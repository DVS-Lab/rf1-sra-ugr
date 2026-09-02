# UGR FEAT templates

Only model 3 is active. Templates retain the established TR (1.615 seconds),
5-mm smoothing, FILM prewhitening, filtering choices, HRF settings, thresholds,
and already-normalized-input registration treatment from the source workflows.
The GUI FEAT progress watcher is disabled in every active template so batch
execution never requires X11.

## L1 activation: 11 EVs

EV order is part of the scientific contract:

1. `nonsocial_high_constant`
2. `nonsocial_high_pmod`
3. `nonsocial_low_constant`
4. `nonsocial_low_pmod`
5. `social_high_constant`
6. `social_high_pmod`
7. `social_low_constant`
8. `social_low_pmod`
9. `rt_constant`
10. `rt_pmod`
11. `miss`

Condition constants use amplitude 1. Offer pmods use canonical BIDS `offer`,
demeaned independently within each sociality × endowment condition and run.
The RT constant is an impulse at `choice_feedback` onset; the RT pmod uses
response time demeaned across all valid trials in that run. FEAT
orthogonalization is disabled because centering is performed explicitly.

Broad condition epochs begin at the canonical true `partner_cue` onset. Valid
epochs end at the end of `choice_feedback`, preserving the historical
decision-offset boundary. Miss epochs end at the end of `missed_decision`; the
following BIDS `missed_feedback` phase is intentionally outside this GLM EV.
The miss EV has shape 3 when a file exists and shape 10 when no misses exist.

The 17 activation contrasts, unchanged from the established template, are:

1. `nonsocial_high_constant`
2. `nonsocial_high_pmod`
3. `nonsocial_low_constant`
4. `nonsocial_low_pmod`
5. `social_high_constant`
6. `social_high_pmod`
7. `social_low_constant`
8. `social_low_pmod`
9. `endowment high > low (constant)`
10. `social > nonsocial (constant)`
11. `offer (un)fairness (pmod)`
12. `social > nonsocial  (pmod)`
13. `nonsocial (pmod)`
14. `social (pmod)`
15. `high > low (pmod)`
16. `nonsocial high > nonsocial low (pmod)`
17. `social high > social low (pmod)`

## L1 template provenance comparison

The authoritative activation template is adapted from `rf1-betrayal`; its one
trailing space was normalized. The selected betrayal source is byte-identical
to the current `rf1-norms/templates/hpc_templates` activation template. The
older root `rf1-norms` activation template differs as follows:

- quoted `NVOLUMES`, dwell time, TE, total-voxel count, and obsolete FNIRT GUI
  field: implementation/display differences;
- missing `custom11 = MISSED_TRIAL`: a scientific/implementation defect that
  makes it unsuitable as the authoritative 11-EV template.

EV order, contrasts, convolution for EVs 1–10, smoothing, prewhitening,
filtering, and orthogonalization otherwise agree.

## Seed PPI

`L1_task-ugr_model-3_type-ppi.fsf` is taken from the newer session-aware
`rf1-betrayal` UGR seed-PPI workflow, as specified for this rebuild. It retains
the 11 task/nuisance EVs, adds the physiological seed series, and constructs 11
interaction EVs for 23 original EVs and 18 contrasts. Contrast 18 is `phys`.
Seeds are selected by `masks/seed-<name>.nii.gz`; activation must run first.

The current norms HPC PPI template is not byte-identical. Most differences are
GUI/environment fields or numeric formatting. The meaningful source
difference was `convolve11`: norms HPC used 3 while betrayal used 0. The
authoritative template uses 3 because a populated missed-trial file represents
a task epoch and must receive the same double-gamma convolution as the other
task regressors. When no miss file exists, `L1stats.sh` changes EV 11 to empty
shape 10, so this setting does not create a regressor. The contrast vectors and
PPI interaction construction otherwise follow betrayal. Two betrayal EV titles
omit a `ppi_` display prefix, but the corresponding interaction definitions and
contrast positions are unchanged.

## Network PPI

`L1_task-ugr_model-3_type-nppi.fsf` is a reproducible expansion of the
authoritative model-3 seed-PPI template. The model-3 task EVs, convolution,
interaction construction, contrasts, filtering, and other FEAT settings come
from that current template; the historical model-2 nPPI template supplies the
ten-network architecture and provenance reference only.

The 32 original EVs are:

1. EVs 1–11: the model-3 task/nuisance EVs above;
2. EV 12: the target network time course (`mainnet`);
3. EVs 13–21: the other nine network time courses as nuisance EVs;
4. EVs 22–32: interactions between each EV 1–11 and `mainnet`.

Contrasts 1–17 preserve the seed-PPI interaction contrasts exactly after the
nine nuisance-network columns are inserted. Contrast 18 estimates `mainnet`.
The miss EV remains double-gamma convolved when populated and is rendered as
empty shape 10 when no misses occur. Its interaction remains in the model for
parity with the established model-3 seed-PPI template.

`L1stats.sh` estimates all ten network time courses together in one spatial
regression, rather than fitting ten separate single-network regressions. `dmn`
selects historical map index 3 and `ecn` selects index 7; all remaining maps
enter as nuisance time courses. Those label/index assignments are inherited
from the historical UGR runner and still require confirmation against the
original network-map distribution documentation.

The template is generated by `code/build_model3_nppi_template.py`. Validation
requires the committed template to be byte-identical to a fresh expansion of
the current seed-PPI source, checks the complete 32 × 33 orthogonalization
matrix, every interaction definition, both contrast matrices, and the
populated/empty miss behavior.

## L2

The activation and PPI L2 templates are byte-identical between `rf1-norms` and
`rf1-betrayal`. Each performs fixed effects across UGR runs 1 and 2 within one
subject/session. L2 does not combine sessions and refuses a missing run.

## Historical model 2

Model 2 was an earlier categorical UGR implementation. It used a different
event/model representation, including cue-level sociality × endowment
regressors. Model 3 superseded it and all current/future analyses here use model
3. Model 2 remains recoverable from Git history and historical repositories but
is intentionally absent from the active workflow.

## Historical model 3b

Model 3b appears in prior manuscript repositories as a separate historical
variant. No evidence from the audited sources requires it for the canonical
model-3 L1/L2 workflow, so it is documented but not shipped as an active choice.
