# RF1-SRA Ultimatum Game analysis

This repository is the authoritative downstream RF1-SRA Ultimatum Game (UGR)
analysis workflow. The task measures responses to fair and unfair divisions of
money under social and nonsocial contexts. The active scientific model is UGR
**model 3** only.

`rf1-sra-linux2` owns canonical BIDS conversion, fMRIPrep, TEDANA, and production
confounds. This repository begins with those visible outputs and never reads raw
PsychoPy logs or private source-data folders.

```text
rf1-sra-linux2
  canonical UGR events.tsv
  fMRIPrep MNI BOLD
  TEDANA-enhanced confounds
          ↓
rf1-sra-ugr
  canonical events → model-3 EVs
          ↓
  L1 activation / seed PPI / network PPI
          ↓
  L2 fixed effects across runs 1 + 2
```

Group-level/L3 analyses will be standardized separately after the canonical
model-3 L1/L2 workflow is validated. Neurodesk notebooks are also deferred.

## Scientific model

Model 3 contains four sociality × endowment conditions: nonsocial/high,
nonsocial/low, social/high, and social/low. Each condition has a constant and a
within-condition, within-run demeaned offer parametric modulator. A run-wide RT
constant and demeaned RT modulator complete the ten required EV files; missed
trials enter an eleventh nuisance EV when present.

Earlier implementations used a PsychoPy `cue_Onset` field that occurred
approximately 0.5 seconds after the true partner-cue onset. The authoritative
implementation uses the reconstructed canonical `partner_cue` onset in BIDS.
For a responded trial, the broad epoch ends at the end of `choice_feedback`—the
same decision-offset boundary used historically. For a miss, it ends at the end
of `missed_decision`, excluding the subsequent `missed_feedback` screen. This is
an intentional onset correction, not a redefinition of the trial endpoint.

See [templates/README.md](templates/README.md) for the full EV and contrast
specification.

## Internal quick start

On Linux2:

```bash
cd /ZPOOL/data/projects/rf1-sra-ugr
git pull --ff-only origin main

export RF1_SRA_UPSTREAM_ROOT=/ZPOOL/data/projects/rf1-sra-linux2
export FSL_DERIVATIVES_ROOT="${PWD}/derivatives/fsl"

if command -v make >/dev/null 2>&1; then
  make test
else
  bash code/validate_workflow.sh
fi

mkdir -p logs/runlists logs/EV-current logs/L1-current

# Rebuild a read-only audit across every visible UGR session. Detailed TSVs
# are ignored locally; --include-full-log preserves the summary in Git.
bash code/run_logged.sh --label workflow-audit --include-full-log -- \
  python3 code/audit_workflow.py \
    --sessions all \
    --seed dACC \
    --output-dir logs/audits/current

python3 code/build_L1_manifest.py \
  --sessions 01 \
  --output logs/runlists/L1-ready.tsv \
  --missing-output logs/runlists/L1-missing.tsv

bash code/run_gen3colfiles.sh \
  --manifest logs/runlists/L1-ready.tsv \
  --jobs 16 --dry-run

bash code/run_gen3colfiles.sh \
  --manifest logs/runlists/L1-ready.tsv \
  --jobs 16 --log-dir logs/EV-current

bash code/run_L1stats.sh \
  --manifest logs/runlists/L1-ready.tsv \
  --ppi 0 --jobs 20 --dry-run
```

Create a small pilot from complete manifest rows before launching FEAT:

```bash
{ head -n 1 logs/runlists/L1-ready.tsv; sed -n '2,5p' logs/runlists/L1-ready.tsv; } \
  > logs/runlists/L1-pilot.tsv

bash code/run_L1stats.sh \
  --manifest logs/runlists/L1-pilot.tsv \
  --ppi 0 --jobs 4 --log-dir logs/L1-pilot
```

After reviewing the pilot, run activation for the approved manifest. Seed and
network PPI must follow activation because they require each activation FEAT
mask:

```bash
bash code/run_L1stats.sh \
  --manifest logs/runlists/L1-ready.tsv \
  --ppi 0 --jobs 20 --log-dir logs/L1-current

bash code/run_L1stats.sh \
  --manifest logs/runlists/L1-ready.tsv \
  --ppi pTPJ --jobs 20 --log-dir logs/L1-PPI-pTPJ-current

# Network-PPI pilot: historical network 3 = DMN, with all ten network maps
# estimated together and the other nine retained as nuisance time courses.
bash code/run_L1stats.sh \
  --manifest logs/runlists/L1-pilot.tsv \
  --ppi dmn --jobs 2 --render-only --log-dir logs/L1-nPPI-DMN-render
```

The active network maps default to `masks/nan_rPNAS_2mm_net0000.nii.gz`
through `net0009.nii.gz`. Override their directory with
`NPPI_NETWORK_MAPS_ROOT` only when deliberately validating an alternative
map set. See [masks/README.md](masks/README.md) for the current provenance
boundary and provisional DMN/ECN index assignments.

After a network-PPI run, select it in the workflow audit with
`--ppi-type nppi-dmn` or `--ppi-type nppi-ecn`.

Build and dry-run L2 after both UGR runs are complete:

```bash
python3 code/build_L2_manifest.py \
  --sessions 01 --type act \
  --output logs/runlists/L2-act-ready.tsv \
  --missing-output logs/runlists/L2-act-missing.tsv

bash code/run_L2stats.sh \
  --manifest logs/runlists/L2-act-ready.tsv \
  --type act --jobs 20 --dry-run
```

`L2stats.sh` defaults `FSLSUB_PARALLEL=1`. This prevents the local `fsl_sub`
shell backend from creating machine-wide worker pools inside every FEAT job,
so `run_L2stats.sh --jobs` remains the primary L2 concurrency control. An
explicitly exported `FSLSUB_PARALLEL` value overrides the default.

Use `code/run_logged.sh` around important production commands when a compact,
Git-trackable run record is desired. Generated imaging data and raw logs remain
untracked.

## External reproducibility

An outside researcher needs this repository, canonical BIDS UGR events,
fMRIPrep derivatives, analysis confounds, Python 3, and FSL. Override paths with
`RF1_SRA_UPSTREAM_ROOT`, `BIDS_ROOT`, `FMRIPREP_ROOT`, `CONFOUNDS_ROOT`,
`FSL_DERIVATIVES_ROOT`, and optionally `NPPI_NETWORK_MAPS_ROOT`. No active code
imports or sources `rf1-sra-linux2`.

The manifest discovers runs from BIDS rather than assuming that all participants
have both. Session 01 is the default historical scope; request session 02
explicitly with `--sessions 01,02`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `code/` | Model-3 EV generation, readiness manifests, L1/L2 workers, wrappers, validation, and workflow provenance. |
| `templates/` | Active model-3 activation, seed-PPI, and generated network-PPI FEAT templates. |
| `masks/` | Tracked seed masks and continuous network maps used by PPI analyses. |
| `derivatives/` | Documentation and ignored local analysis products. |
| `tests/` | Synthetic canonical-event, timing, validation, rendering, and L1→L2 contract tests. |

Run the local validation suite with:

```bash
if command -v make >/dev/null 2>&1; then
  make test
else
  bash code/validate_workflow.sh
fi
```
