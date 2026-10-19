# ModelScope diagnostic samples

These 14 snapshots preserve traceable metadata and headers with unresolved component
scope or conflicting source records. They are useful for investigating loading;
their presence here does not mean the models cannot load.

The [diagnostic catalogue](../../../manifests/diagnostic-samples.json) records each
archive's full revision, SHA-256 and expanded size. Original collected files are
preserved byte for byte. Added annotations live in each ZIP's `manifest.json`:
`known_issues` records reasons and pinned evidence; `offline_review` records strict
status, error count, a hash of the full error list and up to 10 examples.

## Samples

Header counts mean collected headers / headers listed in the pinned source
inventory. They do not establish that every configured component is present.

| Repository / archive | Headers | Reason for separate inclusion | Loading checks still needed |
| --- | --- | --- | --- |
| `MiniMax/MiniMax-M3` · [ZIP](MiniMax/MiniMax-M3/5c6288b3f152.zip) | 59/59 | Config declares 7 MTP modules and nextn; expected components have not been matched. Index total_size also differs. | Confirm component naming and check main-model and MTP scope separately. |
| `Eco-Tech/MiniMax-M3-w8a8` · [ZIP](Eco-Tech/MiniMax-M3-w8a8/247895234a37.zip) | 102/102 | Config declares MTP; expected components have not been matched in headers or quantization metadata. | Confirm MTP naming and loading entry point. |
| `Eco-Tech/MiniMax-M3-w8a8-0626` · [ZIP](Eco-Tech/MiniMax-M3-w8a8-0626/6b534846dcf3.zip) | 103/103 | Four configurations are preserved; declared MTP has not been matched to headers or quantization metadata. | Determine which configuration the loader selects. |
| `MiniMax/MiniMax-M2.7` · [ZIP](MiniMax/MiniMax-M2.7/f274aaba71d9.zip) | 125/125 | Pinned historical config declares 3 MTP modules; headers show main-model layers 0..61. Index total_size also differs. | Check the component convention at this exact revision. |
| `Eco-Tech/MiniMax-M2.7-w8a8-QuaRot` · [ZIP](Eco-Tech/MiniMax-M2.7-w8a8-QuaRot/57b83ec32933.zip) | 55/55 | The 3 declared MTP modules have not been matched in headers. | Confirm component naming and main-model scope. |
| `Eco-Tech/Minimax2.7-BF16-xLLM` · [ZIP](Eco-Tech/Minimax2.7-BF16-xLLM/0ce9bd2f344c.zip) | 125/125 | Headers use BF16/F32, but runtime config declares FP8 and 3 MTP modules; headers show main-model layers 0..61. | Trace actual configuration selection and target dtype. |
| `MiniMax/MiniMax-M2.5` · [ZIP](MiniMax/MiniMax-M2.5/88337210811f.zip) | 125/125 | The 3 declared MTP modules have not been matched. Index total_size also differs. | Check component scope; the pinned LICENSE-MODEL is included. |
| `Eco-Tech/MiniMax-M2.5-w8a8-QuaRot` · [ZIP](Eco-Tech/MiniMax-M2.5-w8a8-QuaRot/d9a92bd9942e.zip) | 57/57 | The 3 declared MTP modules have not been matched; config repeats the model_type key. | Check JSON parsing behavior and component scope. |
| `Eco-Tech/GLM-4.7-W8A8` · [ZIP](Eco-Tech/GLM-4.7-W8A8/1cdfce52fbec.zip) | 85/85 | Config declares one nextn/MTP layer; expected layer 92 has not been found. | Check prediction-layer naming and main-model skip rules. |
| `Eco-Tech/GLM-5.1-W8A8-xLLM` · [ZIP](Eco-Tech/GLM-5.1-W8A8-xLLM/b9e4888b4d61.zip) | 179/179 | The weight index references shards absent from the pinned source inventory. | Determine which missing shards and tensors are needed by the loader. |
| `Eco-Tech/KIMI-k2-Thinking-W8A8-QuaRot` · [ZIP](Eco-Tech/KIMI-k2-Thinking-W8A8-QuaRot/cd5db517b5b9.zip) | 242/242 | An index under old/ references absent shards. | Determine whether the loader reads this old directory. |
| `Eco-Tech/Qwen3-VL-32B-Instruct-w8a8sc-310-vllm` · [ZIP](Eco-Tech/Qwen3-VL-32B-Instruct-w8a8sc-310-vllm/0397b2d48666.zip) | 6/6 | TP-directory indexes reference absent shards; all existing rank headers are collected. | Check each rank and supported compression format. |
| `Eco-Tech/Qwen3-VL-8B-Instruct-w8a8sc-310-vllm` · [ZIP](Eco-Tech/Qwen3-VL-8B-Instruct-w8a8sc-310-vllm/7f11bb2c8f54.zip) | 3/3 | TP-directory indexes reference absent shards; all existing rank headers are collected. | Check each rank and supported compression format. |
| `Eco-Tech/DeepSeek-V4.1-Flash-w8a8` · [ZIP](Eco-Tech/DeepSeek-V4.1-Flash-w8a8/155aced390c4.zip) | 275/275 | The auxiliary export record disagrees with published files. README describes BF16/v2 Engram, while headers/quantization metadata use INT8 + F32 scales/v1. README and LICENSE give different license labels. | The actual weight index matches headers. These document conflicts alone do not prove a mapping failure; check configuration selection and Engram support. |

## Validation and scope

Local offline validation of these fixed snapshots produced **6 PASS, 8 FAIL**.
The eight failures are three index total_size discrepancies, one duplicate JSON
key and four indexes referencing missing source shards. Annotations do not
suppress failures. A structural PASS neither resolves MTP coverage nor proves
framework loading works. Loading is recorded as `NOT_RUN` in this offline check.

This data release does not include the local validator updates used for those
checks. The currently published checker does not support selecting the diagnostic
catalogue with `--catalog` or reading the new EAGLE draft's Python configuration.
The recorded results require those local updates to reproduce; reader support
will be reviewed separately. Original metadata and headers remain available in
standard ZIP files, and their hashes are pinned in the catalogues.

- Preserve config, quantization descriptions, indexes and headers unchanged.
  Do not fabricate components or change dtypes to pass checks.
- Separate main-model, MTP/draft and TP-directory scope. Missing expected names
  alone do not prove a component is absent. Acquisition gaps must not be relabeled
  as source defects.
- Existing regular samples whose only structural issue is total_size remain in
  the regular catalogue with their annotations. An archive-format limitation
  alone does not require diagnostic classification.
- Diagnostic classification does not settle licensing conflicts. Source notices
  and conflicting license labels are preserved and documented in manifests.

The independent [MiniMax EAGLE draft](../../modelscope/Eco-Tech/MiniMax-M2.7-eagle-model-short/631785deb87c.zip)
is in the [regular catalogue](../../../manifests/samples.json), which contains
202 samples. Its reviewed `config.py` is preserved as inert data with exact path,
size and hash checks in the local validator; it was not imported or executed.

For DeepSeek-V4.1-Flash-w8a8, the actual weight index and headers agree. Its
auxiliary export record is a separate document; the inspected SGLang loading path
does not read it or README. The document conflicts remain recorded, and loading
has not been certified.
