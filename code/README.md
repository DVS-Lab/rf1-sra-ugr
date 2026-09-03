# Active UGR code

The production path is intentionally small:

```text
build_L1_manifest.py
        ↓
run_gen3colfiles.sh → gen_model3_evs.py
        ↓
run_L1stats.sh → L1stats.sh ← build_model3_nppi_template.py
        ↓
build_L2_manifest.py
        ↓
run_L2stats.sh → L2stats.sh
```

All active analysis code is model 3, session-aware, and BIDS/derivatives-only.

## `audit_workflow.py`

- **Status:** Production read-only completeness audit.
- **Purpose:** Discover every visible UGR subject/session/run and report upstream inputs, EVs, activation, seed PPI, and eligible L2 completion in one pass.
- **Inputs:** Canonical BIDS events, fMRIPrep BOLD, production confounds, local FSL derivatives, session selection, and seed or exact PPI family.
- **Outputs:** A concise summary plus detailed and wrapper-compatible todo TSVs under `logs/audits/`.
- **Typical command:** `python3 code/audit_workflow.py --sessions all --ppi-type nppi-dmn --output-dir logs/audits/current`.
- **Called by / calls:** Called directly or through `run_logged.sh`; does not invoke FEAT or modify derivatives.
- **Scientific role:** None; it enforces the existing model-3 workflow contracts and identifies missing work.
- **Important assumptions:** L2 requires runs 1 and 2; activation has 17 copes and seed/network PPI has 18. `--seed` remains the seed-PPI shorthand; `--ppi-type` selects an exact seed or network family. Every summary prints the resolved input and FSL derivatives roots and warns when input-ready units exist but no EV outputs are found, which commonly indicates a stale cross-project environment variable.

## `project_config.sh`

- **Status:** Production shared configuration.
- **Purpose:** Centralize checkout-relative paths, environment overrides, analysis-type names, EV prefixes, and exact L1/L2 output names.
- **Inputs:** Environment variables documented in the root README.
- **Outputs:** Shell variables and helper functions.
- **Typical command:** Source from another worker; do not execute directly.
- **Called by / calls:** Sourced by shell workers and EV wrapper.
- **Scientific role:** Prevents L1 and L2 path contracts from drifting.
- **Important assumptions:** Model 3 and 5-mm smoothing are encoded in output names.

## `build_L1_manifest.py`

- **Status:** Production readiness audit.
- **Purpose:** Discover canonical UGR runs and require events, MNI fMRIPrep BOLD, and TEDANA-enhanced confounds.
- **Inputs:** BIDS and derivative roots; optional subject list and sessions.
- **Outputs:** Ready and missing TSV reports.
- **Typical command:** `python3 code/build_L1_manifest.py --sessions 01 --output logs/runlists/L1-ready.tsv --missing-output logs/runlists/L1-missing.tsv`.
- **Called by / calls:** Called directly; no private source-data dependency.
- **Scientific role:** Makes the analyzed subject × session × run set explicit.
- **Important assumptions:** Runs are discovered from BIDS; session 02 is never implicit.

## `gen_model3_evs.py`

- **Status:** Authoritative production model-3 transformation.
- **Purpose:** Collapse canonical phase rows by `trial_id`, validate trial metadata and timing, and write FSL three-column EVs.
- **Inputs:** One canonical `*_task-ugr_run-*_events.tsv`.
- **Outputs:** Ten required EVs plus `missed_trial` only when misses exist.
- **Typical command:** `python3 code/gen_model3_evs.py --events FILE --output-dir DIR --run 1`.
- **Called by / calls:** Called by `run_gen3colfiles.sh`; Python standard library only.
- **Scientific role:** Implements the 2×2 constants, condition-demeaned offer pmods, run-demeaned RT regressors, and miss nuisance.
- **Important assumptions:** Broad epochs begin at true `partner_cue`; valid epochs end with `choice_feedback`; miss epochs end with `missed_decision`. Differing existing EVs require `--overwrite`; replacement removes stale miss files.

## `run_gen3colfiles.sh`

- **Status:** Production batch wrapper.
- **Purpose:** Generate EVs for a manifest or one subject/session/run with deterministic concurrency.
- **Inputs:** L1-ready manifest or explicit unit.
- **Outputs:** Session-aware model-3 EV directories and optional per-unit logs.
- **Typical command:** `bash code/run_gen3colfiles.sh --manifest logs/runlists/L1-ready.tsv --jobs 16 --log-dir logs/EV-current`.
- **Called by / calls:** Calls `gen_model3_evs.py`.
- **Scientific role:** Applies the same validated model transformation to every selected run.
- **Important assumptions:** `--dry-run` performs full input/model validation without writing. It may therefore report canonical-events problems; it is not only a command preview.

## `ugr_qc.py`

- **Status:** Production descriptive QC helper.
- **Purpose:** Report total, valid, missed, valid-proportion, and four-condition counts from canonical events.
- **Inputs:** L1 manifest and BIDS root.
- **Outputs:** One TSV row per subject/session/run.
- **Typical command:** `python3 code/ugr_qc.py --manifest logs/runlists/L1-ready.tsv --output logs/ugr-qc.tsv --min-valid 36`.
- **Called by / calls:** Called directly; reuses the same trial validation as EV generation.
- **Scientific role:** Makes behavioral completeness review visible without silently changing the imaging cohort.
- **Important assumptions:** `--min-valid 36` is an optional manuscript-specific threshold, not a BIDS validity rule.

## `L1stats.sh`

- **Status:** Production single-unit FEAT worker.
- **Purpose:** Validate one subject/session/run, render activation, seed-PPI, or network-PPI model 3, and optionally run FEAT.
- **Inputs:** Canonical BOLD, confounds, model-3 EVs, FEAT template, and optional seed or ten continuous network maps.
- **Outputs:** Rendered FSF, L1 FEAT, and requested seed/network time series.
- **Typical command:** `bash code/L1stats.sh 10317 1 0 --session 01 --dry-run`.
- **Called by / calls:** Called by `run_L1stats.sh`; calls FSL tools.
- **Scientific role:** Runs the established activation/seed-PPI models or the model-3 nPPI expansion with simultaneous ten-map spatial regression.
- **Important assumptions:** Activation must exist before PPI. Historical map 3 = DMN and map 7 = ECN are provisional provenance assignments. Already-normalized input uses identity registration links after FEAT.

## `build_model3_nppi_template.py`

- **Status:** Maintainer-side deterministic template builder.
- **Purpose:** Expand the current 23-EV seed-PPI FSF into the 32-EV network-PPI FSF without manual index editing.
- **Inputs:** The authoritative model-3 seed-PPI template.
- **Outputs:** The committed network-PPI template, or a byte-identity check with `--check`.
- **Typical command:** `python3 code/build_model3_nppi_template.py --source templates/L1_task-ugr_model-3_type-ppi.fsf --output templates/L1_task-ugr_model-3_type-nppi.fsf --check`.
- **Called by / calls:** Called by `validate_workflow.sh` in check mode.
- **Scientific role:** Preserves the model-3 task EVs, all 11 interactions, and 18 contrasts while inserting nine nuisance-network columns around the target network.
- **Important assumptions:** The seed-PPI template remains the source of truth; intentional changes to it require regenerating and revalidating nPPI.

## `run_L1stats.sh`

- **Status:** Production batch wrapper.
- **Purpose:** Run activation, seed-PPI, or network-PPI manifest units with bounded deterministic shell job control and per-unit logs.
- **Inputs:** L1-ready manifest or explicit unit; PPI selector.
- **Outputs:** The outputs of `L1stats.sh`.
- **Typical command:** `bash code/run_L1stats.sh --manifest logs/runlists/L1-ready.tsv --ppi 0 --jobs 20 --log-dir logs/L1-current`.
- **Called by / calls:** Calls `L1stats.sh`.
- **Scientific role:** Keeps activation and seed analyses explicit and separately launchable.
- **Important assumptions:** Existing complete outputs are skipped; replacement requires `--overwrite`.

## `build_L2_manifest.py`

- **Status:** Production L2 readiness audit.
- **Purpose:** Select subject/session units with complete run-1 and run-2 L1 outputs for one analysis type.
- **Inputs:** FSL derivative root, sessions, optional subject list, and `act`, `ppi_seed-<seed>`, or `nppi-<dmn|ecn>`.
- **Outputs:** L2-ready and L2-incomplete TSV reports.
- **Typical command:** `python3 code/build_L2_manifest.py --sessions 01 --type act --output logs/runlists/L2-act-ready.tsv`.
- **Called by / calls:** Called directly.
- **Scientific role:** Prevents accidental one-run fixed-effects models.
- **Important assumptions:** Both expected runs must have the L1 completion marker.

## `L2stats.sh`

- **Status:** Production single-unit L2 worker.
- **Purpose:** Combine UGR runs 1 and 2 within one subject/session using fixed effects.
- **Inputs:** Two complete model-3 L1 FEAT directories and the matching L2 template.
- **Outputs:** Session-aware L2 GFEAT.
- **Typical command:** `bash code/L2stats.sh 10317 act --session 01 --dry-run`.
- **Called by / calls:** Called by `run_L2stats.sh`; calls FEAT.
- **Scientific role:** Estimates within-subject fixed effects across runs, not across sessions.
- **Important assumptions:** Activation has 17 copes; seed and network PPI have 18. The worker defaults `FSLSUB_PARALLEL=1` so the batch wrapper's `--jobs` value remains the primary concurrency limit; export another value only when deliberately changing nested FSL parallelism.

## `run_L2stats.sh`

- **Status:** Production batch wrapper.
- **Purpose:** Run one transparent L2 manifest with bounded concurrency.
- **Inputs:** L2 manifest and one analysis type.
- **Outputs:** The outputs of `L2stats.sh` and optional per-unit logs.
- **Typical command:** `bash code/run_L2stats.sh --manifest logs/runlists/L2-act-ready.tsv --type act --jobs 20 --log-dir logs/L2-act-current`.
- **Called by / calls:** Calls `L2stats.sh`.
- **Scientific role:** Applies the same two-run fixed-effects contract across selected subject-sessions.
- **Important assumptions:** Manifest analysis type and `--type` must describe the same completed L1 family.

## `run_logged.sh`

- **Status:** Production provenance helper adapted from `rf1-sra-socdoors`.
- **Purpose:** Capture an ignored raw log and a compact Markdown run record.
- **Inputs:** Command, optional label, and optional post-run check.
- **Outputs:** `logs/runs/*.log` and `logs/records/*.md`.
- **Typical command:** `bash code/run_logged.sh --label L1-pilot -- bash code/run_L1stats.sh ...`.
- **Called by / calls:** Called directly; executes the supplied command.
- **Scientific role:** Preserves important operational evidence without committing huge logs.
- **Important assumptions:** Raw logs/runlists remain local.

## `validate_workflow.sh`

- **Status:** Production static/synthetic checker.
- **Purpose:** Check shell/Python syntax, forbidden dependencies, sole-model scope, template structure, and unit tests.
- **Inputs:** Active source, templates, and tests.
- **Outputs:** PASS/SKIP messages and nonzero failure status.
- **Typical command:** `make test`.
- **Called by / calls:** Called by `Makefile`; calls `unittest` and ShellCheck when installed.
- **Scientific role:** Locks timing, centering, miss handling, rendering, and L1→L2 naming contracts.
- **Important assumptions:** Routine tests render FSFs but do not run FEAT.

## Historical material

The replaced repository contained raw-to-BIDS MATLAB conversion, model 1/2/4
scripts and templates, nPPI machinery, manuscript-specific L3 models,
covariates, behavioral outputs, figures, and generated derivatives. These are
not part of production. Their classification and source locations are recorded
in [WORKFLOW_AUDIT.md](WORKFLOW_AUDIT.md) and Git history.
