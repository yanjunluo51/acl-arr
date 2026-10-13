# Acquisition of the evaluator panels

Run all commands from the repository root with the dependencies in `requirements.txt`. Downloaded inputs are for local reproduction; these instructions confer no redistribution permission (see `DATA_STATEMENT_CURRENT.md`). The repository itself contains no third-party response text and no original evaluator score arrays.

## RewardBench 2 and WMT23

```bash
python3 scripts/fetch_inputs.py --output-dir data
```

The script reads `evidence/source-model-files.json` and `MANIFEST_SHA256.json`. It fetches the RewardBench 2 results snapshot at revision `b19c7033e964187d12e74a43a07f2d727a3d37e5` and the WMT23 metrics mirror at revision `56352a3d563d371622935c84974b3f215abeede3`, reconstructs the numerical panels, verifies their frozen SHA256 values and never overwrites differing existing inputs. It writes no response text.

## WMT24 and MQM

```bash
python3 scripts/fetch_external_inputs.py --archive /path/to/mt-metrics-eval-v2.tgz --output-dir data
```

`review-revision/acquisition/official-hosting.json`, `review-revision/external-admission.json` and `review-revision/external-panel-protocol.json` identify the official archive and the admission rules. The script rebuilds the three WMT24 numerical panels and the aligned MQM labels, verifies the six recorded hashes and refuses differing existing inputs. The archive must have the recorded SHA256 and byte count; the current remote host may not serve identical bytes.

For WMT23 MQM, `review-revision/acceptance-review-implementation/wmt23-official-files.json` binds the 44 official files used. It contains neither labels nor scores. `scripts/wmt23_quality_diagnostic.py` aligns the labels after masks and query paths are fixed; missing labels remain missing.

## WMT22 confirmation panels

`review-revision/editorial-evidence-followthrough/confirmation/SOURCE_MANIFEST.json` identifies the official archive (SHA256 `6708eec9aaa8a9deca5e370bdd0e23db4881aeca129f29d5281575eaa66c7e10`).

```sh
python3 review-revision/editorial-evidence-implementation/rebuild_wmt22.py --archive /path/to/mt-metrics-eval-v2.tgz --output /path/to/new-wmt22-rebuild
```

The command refuses an existing output directory or an archive with a different hash. It reconstructs admission, arrays and document identities and checks every extracted-file hash against the frozen admission manifest. `review-revision/editorial-evidence-followthrough/confirmation/run.py` runs the subsequent analysis.

## Derived records

Saved derived records (integer flip contributions, certificates, query traces and summaries) are in `outputs/`, `supplement/`, `review-revision/` and `external-verification-20261006/`; `RESULT_DATA_DICTIONARY.md` lists their fields. Checks that replay saved records need no third-party inputs. Complete re-execution needs the panels rebuilt above.
