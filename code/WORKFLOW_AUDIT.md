# UGR workflow provenance audit

This audit preceded the authoritative model-3 rebuild. It records scientific
sources and cleanup decisions; Git history retains every removed file.

## Replaced `rf1-sra-ugr` checkout

The old checkout contained 26,281 tracked files: 24,739 under `derivatives/`
(including 22,611 generated EV-related files), 1,314 under `code/`, 128 masks,
and 96 templates. It was a working/results directory rather than a reusable
downstream analysis repository.

| Material | Classification | Decision |
| --- | --- | --- |
| `L1stats.sh`, `L2stats.sh`, old UGR FEAT templates | HISTORICAL MODEL / MODEL-3 SUPPORT | Inspected for naming and lab conventions; replaced by source-prioritized model-3 workflow. |
| `convertUGR_BIDS.m`, `final_converter.m`, conversion helpers | BEHAVIORAL/QC / HISTORICAL MODEL | Removed. They read private raw logs or perform raw→BIDS conversion now owned by Linux2. |
| `behavioral_analysis.m` | BEHAVIORAL/QC | Removed from active checkout. It reads private task logs and computes participant earnings/choices. Modernization is deferred until a BIDS-only specification is requested. |
| `UGR_analysis.m` | BEHAVIORAL/QC / RESULT ANALYSIS | Removed from active checkout. It analyzes previously generated subject behavioral tables plus manuscript covariates; it is not the canonical fMRI path. |
| `calc_events.m` | HISTORICAL MODEL | Removed. It compares multiple older EV/model representations and is superseded by explicit model-3 tests. |
| `UGDG_analysis.m`, `behavioral_analysis_UGDG.m` | UNRELATED TO UGR | Removed; these include Dictator Game/proposer analyses outside the responder-task workflow. |
| `MakeCategoricalEVs.m` | HISTORICAL MODEL / RESULT SUPPORT | Removed. It bins old EVs for plotting and is not part of continuous model 3. |
| models 1, 2, 4; nPPI scripts/templates | HISTORICAL MODEL | Removed from active workflow. Model 2 is documented in `templates/README.md`; nPPI has no demonstrated current model-3 requirement. |
| L3 scripts/templates, covariates, subject lists | RESULT/FIGURE ASSET / HISTORICAL MODEL | Removed from active checkout. Group standardization is explicitly deferred. |
| `code/output/`, figures, spreadsheets, ROI extractions | RESULT/FIGURE ASSET | Removed; manuscript/results provenance remains in Git history and source repositories. |
| `derivatives/` generated EVs, imaging tables, FEAT products | RESULT/FIGURE ASSET | Removed and ignored. Rebuild from canonical inputs. |
| broad mask collection and network masks | RESULT/FIGURE ASSET / HISTORICAL MODEL | Removed; only three active seed-PPI masks were selected from source repositories. |
| swap files, `.goutputstream-*`, checkpoints, lock files, `.asv` autosaves | TEMPORARY/JUNK | Removed and ignored. |
| `nilearn`, `cooper-test.txt` | UNCERTAIN / TEMPORARY | Empty or unexplained working artifacts; removed. |

## `rf1-norms`

| Material | Classification | Use here |
| --- | --- | --- |
| `code/a4_model-3.py` | MODEL-3 SCIENTIFIC SOURCE | Principal provenance for condition assignment, within-condition offer demeaning, run-wide RT demeaning, miss classification, and historical timing. Reimplemented from canonical BIDS rather than copied because the source reads private raw CSVs. |
| `templates/hpc_templates/L1_task-ugr_model-3_type-act.fsf` | MODEL-3 SCIENTIFIC SOURCE | Byte-identical to betrayal activation template and used to establish parity. |
| root activation template | MODEL-3 SUPPORT | Rejected as authoritative because it omits the miss custom-file assignment. |
| L2 activation/PPI templates | MODEL-3 SCIENTIFIC SOURCE | Verified byte-identical to betrayal copies. |
| `masks/seed-pTPJ.nii.gz` | MODEL-3 SUPPORT | Retained active seed; detailed anatomical derivation still needs confirmation. |
| model 3b, L3, extraction, behavioral and result material | HISTORICAL MODEL / RESULT ASSET | Not migrated. |

## `rf1-betrayal`

| Material | Classification | Use here |
| --- | --- | --- |
| `code/L1stats-ugr.sh` | MODEL-3 SUPPORT | Principal session-aware seed-PPI worker reference; Trust and cross-task logic were not migrated. |
| `templates/L1_task-ugr_model-3_type-act.fsf` | MODEL-3 SCIENTIFIC SOURCE | Selected authoritative activation template; matches current norms HPC copy. |
| `templates/L1_task-ugr_model-3_type-ppi.fsf` | MODEL-3 SCIENTIFIC SOURCE | Selected authoritative PPI template per source priority. |
| L2 activation/PPI templates | MODEL-3 SCIENTIFIC SOURCE | Selected once after byte-identity verification. |
| `seed-dACC.nii.gz`, `seed-AIns-clusterthresh.nii.gz` | MODEL-3 SUPPORT | Retained as `seed-dACC.nii.gz` and `seed-AIns.nii.gz`; deeper creation provenance needs confirmation. |
| Trust conversion/templates, dACC cross-task regressors, dual-task selection, betrayal L3 | UNRELATED TO UGR / RESULT ASSET | Not migrated. |

## Focused template-difference classification

Activation differences between the older norms root template and betrayal/current
norms HPC template:

- quoted `NVOLUMES`, dwell time, TE, total voxels, and FNIRT GUI field:
  **PATH/ENVIRONMENT ONLY**, **DISPLAY/FEAT GUI ONLY**, or **IMPLEMENTATION ONLY**;
- missing `custom11 = MISSED_TRIAL` in the older norms root file:
  **SCIENTIFIC MODEL DIFFERENCE / implementation defect**. The matching
  betrayal/current norms HPC template preserves the intended 11th EV.

PPI differences between norms HPC and betrayal:

- Featwatcher, dwell/TE, total voxels, randomise GUI field, numeric formatting:
  **DISPLAY/FEAT GUI ONLY** or **IMPLEMENTATION ONLY**;
- `convolve11` equals 3 in norms HPC and 0 in betrayal:
  **SCIENTIFIC MODEL DIFFERENCE**. The task explicitly prioritizes betrayal's
  newer seed-PPI implementation, so the betrayal value is retained and the
  discrepancy is documented in `templates/README.md` rather than silently
  blended.

L2 activation and PPI source templates are byte-identical.

## Timing continuity

Historical model 3 used `cue_Onset` and `decision_offset`. The authoritative
implementation uses canonical BIDS `partner_cue` onset and reconstructs the
same terminal boundary as the end of `choice_feedback` for responses or the end
of `missed_decision` for misses. Synthetic parity tests lock trial membership,
condition assignment, offer/RT centering, and miss classification while
demonstrating the expected approximately 0.5-second earlier onset and longer
duration with an unchanged offset.
