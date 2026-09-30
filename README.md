# llm-loadcheck

Datasets and tools for checking LLM weight loading, starting with BF16 and
ModelSlim checkpoints in SGLang.

This first release contains **45 metadata snapshots from ModelScope**: 44 selected
Eco-Tech quantized checkpoints and one official Qwen BF16 checkpoint. Each sample
is pinned to a full source revision and stored as one ZIP. Full tensor payloads
are not included.

The [sample catalogue](manifests/samples.json) lists every repository, revision,
variant, archive path, compressed/expanded size and SHA-256. Quantized samples come
from Eco-Tech; the BF16 baseline comes from the original publisher, Qwen. Publisher
selection does not imply that every checkpoint from that account is supported.

## Verify the dataset

Use Python 3.10 or newer. No third-party packages, model framework or accelerator
are required. From the repository root:

```bash
python scripts/check_dataset.py
```

This verifies all catalogue ZIPs and writes `.cache/structure-check.json`.
The included dataset should report 45 samples with structure status `PASS`.

The two scripts have distinct roles:

- `scripts/sample_archive.py` verifies archive hashes and extraction limits, rejects
  unsafe paths and unexpected members, and cleans up temporary extraction directories.
- `scripts/check_dataset.py` checks source identity, file hashes, complete shard-header
  inventory, tensor shapes/dtypes/offsets and index-to-header consistency.

These are offline metadata checks. A structural `PASS` does not establish correct
model loading, quantization behavior, numerical accuracy or device inference.
Header hashes do not verify tensor payloads; upstream full-weight hashes are
recorded without claiming independent verification.

## Sample format

ZIP paths follow `data/modelscope/<owner>/<model>/<revision-prefix>.zip`.
The full revision in the catalogue and sample manifest is authoritative.
Each archive uses `publication_format=llm-loadcheck-zip-v1` and contains:

```text
manifest.json                  # identity, acquisition records and explicit omissions
source_files.json              # inventory at the pinned source revision
configs/<original-path>        # model config, quantization metadata and weight indexes
headers/<original-path>.json   # complete original safetensors JSON headers
provenance/<original-path>     # available upstream attribution and license files
```

Included upstream files retain their original bytes. Headers preserve all tensor
entries, including prediction tensors stored in those shards. Optional model cards
and quantization recipes may be omitted after review; the manifest retains their
source paths and hashes with explicit omission status. Required configs, headers
and available LICENSE/NOTICE files are preserved.

Extraction accepts at most 4,096 members and 64 MiB compressed data. The default
expanded limit is 64 MiB; larger samples require the external catalogue's exact
expanded byte count and archive hash, with a hard maximum of 512 MiB. The archive
cannot authorize a larger limit itself. No code from a sample is executed.

## License

Original project code is licensed under [Apache-2.0](LICENSE). Upstream metadata
retains its original attribution and terms; this project's license does not
relicense it. Consult each sample's manifest and provenance records.
