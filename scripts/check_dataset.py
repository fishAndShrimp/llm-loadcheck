"""Offline integrity checks for collected headers; does not run a model loader."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DTYPE_BITS = {
    "BOOL": 8, "U8": 8, "I8": 8, "F8_E4M3": 8, "F8_E5M2": 8,
    "F8_E8M0": 8, "F8_E4M3FNUZ": 8, "F8_E5M2FNUZ": 8,
    "I16": 16, "U16": 16, "F16": 16, "BF16": 16,
    "I32": 32, "U32": 32, "F32": 32, "I64": 64, "U64": 64, "F64": 64,
}


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"Duplicate JSON key: {key}")
        obj[key] = value
    return obj


def load_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_object)


def local_path(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError(f"Unsafe path: {relative}")
    return root.joinpath(*path.parts)


def validate_header(header, *, header_bytes, source_size):
    errors, unsupported = [], []
    tensors = {}
    if not isinstance(header, dict):
        return {}, ["header is not an object"], []
    spans = []
    for name, tensor in header.items():
        if name == "__metadata__":
            if not isinstance(tensor, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in tensor.items()):
                errors.append("__metadata__ must map strings to strings")
            continue
        try:
            shape, dtype, offsets = tensor["shape"], tensor["dtype"], tensor["data_offsets"]
            if not isinstance(shape, list) or any(type(v) is not int or v < 0 for v in shape):
                raise ValueError("invalid shape")
            if not isinstance(offsets, list) or len(offsets) != 2 or any(type(v) is not int for v in offsets):
                raise ValueError("invalid offsets")
            start, end = offsets
            if start < 0 or end < start or end > source_size - 8 - header_bytes:
                raise ValueError("offsets outside data buffer")
            if dtype not in DTYPE_BITS:
                unsupported.append(f"{name}: unsupported dtype {dtype}")
            elif end - start != (math.prod(shape) * DTYPE_BITS[dtype] + 7) // 8:
                raise ValueError("shape/dtype byte count does not match offsets")
            spans.append((start, end, name))
            tensors[name] = tensor
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    cursor = 0
    for start, end, name in sorted(spans):
        if start != cursor:
            errors.append(f"{name}: data gap or overlap at {start}, expected {cursor}")
        cursor = max(cursor, end)
    if cursor != source_size - 8 - header_bytes:
        errors.append("tensor spans do not cover the declared file data buffer")
    return tensors, errors, unsupported


def validate_index(index, index_path, tensors_by_file):
    errors = []
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        return ["index has no nonempty weight_map"]
    parent = PurePosixPath(index_path).parent
    expected = {}
    for name, filename in weight_map.items():
        if not isinstance(filename, str):
            errors.append(f"{name}: invalid shard filename")
            continue
        file = str(parent / filename)
        expected.setdefault(file, set()).add(name)
        if file not in tensors_by_file:
            errors.append(f"{name}: missing collected shard {file}")
        elif name not in tensors_by_file[file]:
            errors.append(f"{name}: absent from indexed shard {file}")
    observed_bytes = 0
    complete = True
    for file, names in expected.items():
        if file not in tensors_by_file:
            complete = False
            continue
        actual = tensors_by_file[file]
        extras = set(actual) - names
        if extras:
            errors.append(f"{file}: {len(extras)} tensors missing from index")
        observed_bytes += sum(t["data_offsets"][1] - t["data_offsets"][0] for t in actual.values())
    declared = index.get("metadata", {}).get("total_size")
    if complete and declared is not None and declared != observed_bytes:
        errors.append(f"index total_size {declared} != tensor bytes {observed_bytes}")
    return errors


def check_sample(manifest_path):
    manifest = load_json(manifest_path)
    root = manifest_path.parent
    catalogue = load_json(ROOT / "manifests/samples.json")
    allowed = {(r["repo_id"], r["revision"]) for r in catalogue["samples"]}
    # Local acquisition tools may also validate reviewed, unpublished samples.
    policy_path = ROOT / "manifests/modelscope-allowlist.json"
    if policy_path.exists():
        policy = load_json(policy_path)
        allowed.update((r["id"], r["revision"]) for r in policy["repositories"])
    if manifest.get("source") != "modelscope" or (manifest["repo_id"], manifest["revision"]) not in allowed:
        raise ValueError("Sample source/repository/revision is outside the approved catalogue or local collection policy")
    errors, unsupported, tensors_by_file = [], [], {}
    if manifest.get("collection_status") != "COLLECTED":
        errors.append("sample collection is not complete")
    config_records, indexes, dtype_counts = [], [], Counter()
    inventory = root / "source_files.json"
    if hashlib.sha256(inventory.read_bytes()).hexdigest() != manifest["source_inventory_sha256"]:
        errors.append("source_files.json hash mismatch")
    expected_headers = {f["path"] for f in load_json(inventory) if f["path"].endswith(".safetensors")}
    collected_headers = {f["source_path"] for f in manifest["files"]
                         if f["kind"] == "header" and f["status"] == "COLLECTED"}
    if expected_headers != collected_headers:
        errors.append("collected headers do not match the full source safetensors inventory")
    for entry in manifest["files"]:
        name = entry["source_path"]
        if entry["status"] == "ERROR":
            errors.append(f"{name}: acquisition error")
        elif entry["status"] == "SKIPPED_SIZE_LIMIT":
            unsupported.append(f"{name}: not collected (size limit)")
        if entry["status"] != "COLLECTED":
            continue
        try:
            path = local_path(root, entry["local_path"])
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["local_sha256"]:
                raise ValueError("local hash mismatch")
            if len(raw) != entry["collected_bytes"]:
                raise ValueError("local size mismatch")
            if entry["kind"] == "header":
                if len(raw) != entry["header_bytes"]:
                    raise ValueError("header length mismatch")
                tensors, failures, unknown = validate_header(load_json(path), header_bytes=len(raw), source_size=entry["source_size"])
                errors.extend(f"{name}: {e}" for e in failures)
                unsupported.extend(f"{name}: {e}" for e in unknown)
                tensors_by_file[name] = tensors
                dtype_counts.update(t["dtype"] for t in tensors.values())
            elif entry["kind"] == "config" and name.endswith(".json"):
                config = load_json(path)
                if name.endswith(".safetensors.index.json"):
                    indexes.append((name, config))
                if PurePosixPath(name).name == "config.json":
                    quant = config.get("quantization_config", {})
                    config_records.append({"path": name, "architectures": config.get("architectures", []),
                                           "model_type": config.get("model_type"),
                                           "declared_quantization": quant})
                elif PurePosixPath(name).name == "quant_model_description.json":
                    config_records.append({"path": name, "format": "modelslim",
                        "weight_schemes": dict(Counter(v for k, v in config.items() if k.endswith(".weight") and isinstance(v, str)))})
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"{name}: {exc}")
    for name, index in indexes:
        errors.extend(f"{name}: {e}" for e in validate_index(index, name, tensors_by_file))
    if not tensors_by_file:
        unsupported.append("no safetensors headers; other weight formats are inventory-only")
    return {
        "repo_id": manifest["repo_id"], "revision": manifest["revision"],
        "structure_status": "FAIL" if errors else ("BLOCKED" if unsupported else "PASS"),
        "sglang_loading_status": "NOT_RUN", "numerical_status": "NOT_RUN", "device_status": "NOT_RUN",
        "safetensors_files": len(tensors_by_file), "tensors": sum(map(len, tensors_by_file.values())),
        "dtype_counts": dict(dtype_counts), "configurations": config_records,
        "errors": errors, "unsupported": unsupported,
    }


def check_input(path, *, expected_sha256=None, expected_unpacked_bytes=None):
    from sample_archive import open_sample
    with open_sample(path, expected_sha256=expected_sha256,
                     expected_unpacked_bytes=expected_unpacked_bytes) as directory:
        return check_sample(directory / "manifest.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="ZIP file or directory; defaults to the published ZIP catalogue")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/structure-check.json")
    args = parser.parse_args()
    results = []
    if args.root is None:
        entries = load_json(ROOT / "manifests/samples.json")["samples"]
        inputs = [(local_path(ROOT, e["archive"]), e) for e in entries]
    elif args.root.is_file():
        inputs = [(args.root, {})]
    else:
        archives = sorted(args.root.rglob("*.zip"))
        inputs = [(p, {}) for p in archives] if archives else [
            (p.parent, {}) for p in sorted(args.root.rglob("manifest.json"))
            if (p.parent / "source_files.json").exists()]
    for path, entry in inputs:
        try:
            result = check_input(path, expected_sha256=entry.get("sha256"),
                                 expected_unpacked_bytes=entry.get("unpacked_bytes"))
            if entry and (result["repo_id"], result["revision"]) != (entry["repo_id"], entry["revision"]):
                raise ValueError("ZIP identity does not match sample catalogue")
            if entry:
                result.update(archive=entry["archive"], archive_sha256=entry["sha256"])
            results.append(result)
        except Exception as exc:
            results.append({"sample": entry.get("archive", str(path)), "structure_status": "FAIL", "error": str(exc)})
    summary = dict(Counter(r["structure_status"] for r in results))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": 1, "scope": "offline_structure_only",
                                      "summary": summary, "samples": results}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"samples": len(results), "summary": summary}, ensure_ascii=False))
    if not results or summary.get("FAIL"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
