"""Bounded ZIP input adapter; preserve the existing sample's bytes and paths."""
from contextlib import contextmanager
import hashlib
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

MAX_ENTRIES = 4096
MAX_BYTES = 64 * 1024 * 1024
MAX_REVIEWED_BYTES = 512 * 1024 * 1024


def reviewed_size(value):
    if type(value) is not int or not 0 < value <= MAX_REVIEWED_BYTES:
        raise ValueError('Reviewed expanded size must be a positive integer at most 512 MiB')
    return value


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def member_path(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '..' in path.parts or '\\' in name
            or ':' in name or str(path) != name):
        raise ValueError(f'Unsafe ZIP member: {name}')
    if name not in ('manifest.json', 'source_files.json'):
        if len(path.parts) < 2 or path.parts[0] not in ('configs', 'headers', 'provenance'):
            raise ValueError(f'Unexpected sample path: {name}')
        if path.suffix.lower() in ('.safetensors', '.bin', '.pt', '.pth', '.gguf', '.py'):
            raise ValueError(f'Payload/code is not a metadata sample: {name}')
    return path


@contextmanager
def open_sample(path, *, expected_sha256=None, expected_unpacked_bytes=None):
    """Yield a directory; ZIPs are verified/extracted and always cleaned up."""
    path = Path(path)
    limit = MAX_BYTES
    if expected_unpacked_bytes is not None:
        reviewed_size(expected_unpacked_bytes)
        if expected_unpacked_bytes > MAX_BYTES:
            if expected_sha256 is None:
                raise ValueError('Larger samples require an external archive hash and expanded size')
            limit = expected_unpacked_bytes
    if path.is_dir():
        if expected_sha256 is not None:
            raise ValueError('An archive hash cannot verify a directory')
        yield path
        return
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Sample ZIP exceeds size limit')
    if expected_sha256 is not None and sha256(path) != expected_sha256:
        raise ValueError('Sample ZIP hash mismatch')
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        expanded = sum(m.file_size for m in members)
        if len(members) > MAX_ENTRIES or expanded > limit:
            raise ValueError('Sample ZIP exceeds extraction limits')
        if expected_unpacked_bytes is not None and expanded != expected_unpacked_bytes:
            raise ValueError('Sample ZIP expanded size mismatch')
        names = set()
        for member in members:
            member_path(member.filename)
            if member.filename in names:
                raise ValueError('Duplicate ZIP member')
            names.add(member.filename)
            mode = member.external_attr >> 16
            if (member.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or member.flag_bits & 1):
                raise ValueError('Only ordinary, unencrypted ZIP files are accepted')
            if member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError('Unsupported ZIP compression')
        if not {'manifest.json', 'source_files.json'} <= names:
            raise ValueError('Sample ZIP is missing its manifest/inventory')
        with tempfile.TemporaryDirectory(prefix='llm-loadcheck-') as directory:
            root = Path(directory)
            for member in members:
                destination = root.joinpath(*member_path(member.filename).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open('wb') as target:
                    size = 0
                    while chunk := source.read(65536):
                        size += len(chunk)
                        if size > member.file_size:
                            raise ValueError('ZIP entry exceeds declared size')
                        target.write(chunk)
            # Ignore no extra files: every packaged file must have an acquisition record.
            import json
            manifest = json.loads((root/'manifest.json').read_bytes())
            expected = {'manifest.json', 'source_files.json'} | {
                f['local_path'] for f in manifest['files'] if f['status'] == 'COLLECTED'}
            if names != expected:
                raise ValueError('ZIP members do not match sample manifest')
            yield root
