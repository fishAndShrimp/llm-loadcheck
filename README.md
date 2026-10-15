# llm-loadcheck

Datasets and tools for checking LLM weight loading, starting with BF16 and
ModelSlim checkpoints in SGLang.

The dataset contains metadata snapshots from ModelScope for selected Eco-Tech
quantized checkpoints and official original checkpoints. Each sample is pinned
to a full source revision and stored as one ZIP. Full tensor payloads are not
included.

The [sample catalogue](manifests/samples.json) lists every repository, revision,
variant, archive path, compressed/expanded size and SHA-256. Quantized samples come
from Eco-Tech; original baselines come from their official publishers. Publisher
selection does not imply that every checkpoint from that account is supported.

## Verify the dataset

Use Python 3.10 or newer. No third-party packages, model framework or accelerator
are required. From the repository root:

```bash
python scripts/check_dataset.py
```

This verifies all catalogue ZIPs and writes `.cache/structure-check.json`.
The strict checker retains upstream inconsistencies as failures. Samples with a
recorded `index_total_size_mismatch` still report structure status `FAIL` and
produce exit code 1; inspect their original errors and manifest annotations.
Packaging such a sample does not turn the discrepancy into a structural `PASS`.

The two scripts have distinct roles:

- `scripts/sample_archive.py` verifies archive hashes and extraction limits, rejects
  unsafe paths and unexpected members, and cleans up temporary extraction directories.
- `scripts/check_dataset.py` checks source identity, file hashes, complete shard-header
  inventory, tensor shapes/dtypes/offsets and index-to-header consistency.

These are offline metadata checks. A structural `PASS` does not establish correct
model loading, quantization behavior, numerical accuracy or device inference.
Header hashes do not verify tensor payloads; upstream full-weight hashes are
recorded without claiming independent verification.

## Known issues and mapping checks

A sample can be useful for mapping checks even when it has an upstream metadata
issue or cannot yet be published. Keep these decisions separate:

| Category | Meaning | Effect on mapping checks |
| --- | --- | --- |
| Total size mismatch | Index `total_size` differs from the bytes calculated from headers. | This discrepancy alone does not block mapping checks when the full header inventory and index-to-header name coverage pass. Preserve the discrepancy. |
| Missing shard | An index references a file absent from the pinned source inventory. | Review the actual loading path, including old indexes and TP subdirectories; do not claim full coverage of missing inputs. |
| Component scope unresolved | Config declares MTP or another component that has not been matched to header entries. | Limit any test to a verified scope; do not claim complete component coverage. |
| Invalid or incomplete headers | A header is malformed or only part of the required inventory was acquired. | Blocks a complete mapping check. |
| Configuration conflict | Config, quantization metadata or export descriptions disagree about the model or precision. | Resolve the configuration used by the loader before interpreting results. |
| Publication concern | License information or original upstream names need an explicit review note. | Does not itself block mapping checks. Record the concern and packaging decision without rewriting source files or inventing a license. |
| Archive format limitation | Required source files are retained locally but are not accepted by the ZIP format. | Separate from mapping correctness; the test still needs the appropriate configuration and loading entry point. Do not execute source code automatically. |
| Source unavailable or unconfirmed | The source cannot be accessed, or its identity/revision is not established. | Blocks a reproducible complete sample. |

A sample may have more than one issue. Record each issue against the exact source,
repository and full revision, with its explanation and evidence. For a size
mismatch, retain both the declared and calculated values. A source defect is not
proof of a collection error or a loader bug.

For packaged samples, the authoritative annotations live in `manifest.json`
inside each ZIP. The external `manifests/samples.json` catalogue pins that ZIP by
SHA-256; it does not maintain a second copy of the annotations.
The README defines the categories; reports retain evidence and present summaries.
Do not duplicate manually maintained labels in directory names, ZIP names or
separate tag files. Preserve original metadata and headers unchanged. Framework
results belong in test reports with the framework commit and tested scope;
"eligible for testing" never means "mapping passed".

The annotated samples use these additive manifest fields:

- `known_issues`: issue code, explanation, `mapping_impact`, and evidence paths
  with SHA-256 hashes. Size discrepancies also record `index_path`,
  `declared_bytes` and `observed_bytes`. Missing license files and differences
  between model-card descriptions and repository names are recorded separately.
- `offline_review`: the original strict structure status and errors, packaging
  status, and loading status `NOT_RUN`. `NO_BLOCKER_FROM_RECORDED_ISSUES` means
  only that these specific issues do not preclude mapping diagnostics; it does
  not certify detector support or correct loading.
- `packaging_policy.preserve_collected_files`: all collected configs, headers,
  model cards and recipes are retained byte for byte. The acquisition file
  records and source inventory are unchanged. Inventory-only payloads stay
  inventory-only; no full weight data is added.

The local packer admits a size discrepancy only when the annotation matches the
original index hash, declared size and independently recalculated header bytes,
and the strict checker has no other errors or unsupported data. Publication
notes cannot waive structural errors. The public strict checker is unchanged;
annotations do not suppress its failures. Existing unannotated ZIPs are unchanged.

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
