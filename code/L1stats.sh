#!/usr/bin/env bash

# Render and run one UGR model-3 first-level FEAT analysis.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=project_config.sh
source "${SCRIPT_DIR}/project_config.sh"

usage() {
    cat <<'EOF'
Usage: L1stats.sh SUBJECT RUN PPI [options]

PPI is 0/act for activation or a seed name matching masks/seed-<name>.nii.gz.

Options:
  --session ID       BIDS session (default: 01)
  --bold FILE        Override the canonical fMRIPrep BOLD
  --confounds FILE   Override the canonical TEDANA-enhanced confounds
  --dry-run          Validate inputs and print paths without writing
  --render-only      Render and validate the .fsf without running FEAT
  --overwrite        Replace an existing generated FEAT output
EOF
}

(( $# >= 3 )) || { usage >&2; exit 2; }
sub="$(normalize_subject "$1")"
run="$2"
ppi="$3"
shift 3

session="01"
bold_override=""
confounds_override=""
mode="run"
overwrite=0
while (( $# )); do
    case "$1" in
        --session) session="$2"; shift 2 ;;
        --bold) bold_override="$2"; shift 2 ;;
        --confounds) confounds_override="$2"; shift 2 ;;
        --dry-run) mode="dry-run"; shift ;;
        --render-only) mode="render-only"; shift ;;
        --overwrite) overwrite=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done
session="$(normalize_session "$session")"

smoothing=5
type="$(analysis_type_from_ppi "$ppi")"
subject_output="${FSL_DERIVATIVES_ROOT}/sub-${sub}/ses-${session}"
output="$(l1_output_base "$sub" "$session" "$run" "$type" "$smoothing")"
stem="sub-${sub}_ses-${session}_task-ugr_run-${run}"
data="${bold_override:-${FMRIPREP_ROOT}/sub-${sub}/ses-${session}/func/${stem}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz}"
confounds="${confounds_override:-${CONFOUNDS_ROOT}/sub-${sub}/${stem}_desc-TedanaPlusConfounds.tsv}"
ev_prefix="$(model3_ev_prefix "$sub" "$session" "$run")"
missed_ev="${ev_prefix}_missed_trial.txt"
shape_missed=10
[[ -s "$missed_ev" ]] && shape_missed=3

required_evs=(
    nonsocial_high_constant nonsocial_high_pmod
    nonsocial_low_constant nonsocial_low_pmod
    social_high_constant social_high_pmod
    social_low_constant social_low_pmod
    rt_constant rt_pmod
)
for ev in "${required_evs[@]}"; do
    path="${ev_prefix}_${ev}.txt"
    [[ -s "$path" ]] || { echo "ERROR: required model-3 EV is missing or empty: $path" >&2; exit 1; }
done
[[ -f "$data" ]] || { echo "ERROR: BOLD input not found: $data" >&2; exit 1; }
[[ -s "$confounds" ]] || { echo "ERROR: confounds file not found or empty: $confounds" >&2; exit 1; }

case "$type" in
    act) template="${PROJECT_ROOT}/templates/L1_task-ugr_model-3_type-act.fsf" ;;
    ppi_seed-*) template="${PROJECT_ROOT}/templates/L1_task-ugr_model-3_type-ppi.fsf" ;;
    *) echo "ERROR: unsupported analysis type: $type" >&2; exit 2 ;;
esac
[[ -f "$template" ]] || { echo "ERROR: FEAT template not found: $template" >&2; exit 1; }

rendered="${subject_output}/L1_sub-${sub}_task-ugr_ses-${session}_model-3_type-${type}_run-${run}.fsf"
printf 'L1 plan\n  BOLD: %s\n  confounds: %s\n  EV prefix: %s\n  template: %s\n  output: %s.feat\n' \
    "$data" "$confounds" "$ev_prefix" "$template" "$output"
[[ "$mode" == dry-run ]] && exit 0

command -v fslnvols >/dev/null 2>&1 || { echo "ERROR: fslnvols is not available; load FSL first." >&2; exit 1; }
nvolumes="$(fslnvols "$data")"
[[ "$nvolumes" =~ ^[0-9]+$ ]] || { echo "ERROR: invalid BOLD volume count: $nvolumes" >&2; exit 1; }

feat_dir="${output}.feat"
if [[ -e "$feat_dir" ]]; then
    if (( ! overwrite )); then
        if [[ -f "$feat_dir/cluster_mask_zstat1.nii.gz" ]]; then
            echo "Complete output already exists; skipping: $feat_dir"
            exit 0
        fi
        echo "ERROR: incomplete output exists: $feat_dir (use --overwrite)." >&2
        exit 1
    fi
    case "$feat_dir" in
        "${FSL_DERIVATIVES_ROOT}"/*) rm -rf -- "$feat_dir" ;;
        *) echo "ERROR: refusing to remove output outside FSL_DERIVATIVES_ROOT: $feat_dir" >&2; exit 1 ;;
    esac
fi

mkdir -p "$subject_output"
sed_escape() { printf '%s' "$1" | sed 's/[&@\\]/\\&/g'; }
sed_args=(
    -e "s@OUTPUT@$(sed_escape "$output")@g"
    -e "s@DATA@$(sed_escape "$data")@g"
    -e "s@EVDIR@$(sed_escape "$ev_prefix")@g"
    -e "s@MISSED_TRIAL@$(sed_escape "$missed_ev")@g"
    -e "s@SHAPE_EV@${shape_missed}@g"
    -e "s@CONFOUNDEVS@$(sed_escape "$confounds")@g"
    -e "s@NVOLUMES@${nvolumes}@g"
)

if [[ "$type" == ppi_seed-* ]]; then
    seed="${type#ppi_seed-}"
    mask="${PROJECT_ROOT}/masks/seed-${seed}.nii.gz"
    [[ -f "$mask" ]] || { echo "ERROR: seed mask not found: $mask" >&2; exit 1; }
    activation="$(l1_output_base "$sub" "$session" "$run" act "$smoothing").feat"
    [[ -f "$activation/mask.nii.gz" ]] || { echo "ERROR: activation must exist before PPI: $activation" >&2; exit 1; }
    command -v fslmeants >/dev/null 2>&1 || { echo "ERROR: fslmeants is not available; load FSL first." >&2; exit 1; }
    phys="${subject_output}/ts_task-ugr_ses-${session}_mask-${seed}_run-${run}.txt"
    fslmeants -i "$data" -o "$phys" -m "$mask"
    sed_args+=( -e "s@PHYS@$(sed_escape "$phys")@g" )
fi

sed "${sed_args[@]}" "$template" > "$rendered"
if grep -En 'OUTPUT|DATA|EVDIR|MISSED_TRIAL|SHAPE_EV|CONFOUNDEVS|NVOLUMES|PHYS' "$rendered" >/dev/null 2>&1; then
    echo "ERROR: unresolved placeholder remains in rendered template: $rendered" >&2
    exit 1
fi
echo "Rendered: $rendered"
[[ "$mode" == render-only ]] && exit 0

command -v feat >/dev/null 2>&1 || { echo "ERROR: feat is not available; load FSL first." >&2; exit 1; }
feat "$rendered"

mkdir -p "$feat_dir/reg"
ln -sfn "${FSLDIR}/etc/flirtsch/ident.mat" "$feat_dir/reg/example_func2standard.mat"
ln -sfn "${FSLDIR}/etc/flirtsch/ident.mat" "$feat_dir/reg/standard2example_func.mat"
ln -sfn "$feat_dir/mean_func.nii.gz" "$feat_dir/reg/standard.nii.gz"
rm -f -- "$feat_dir/stats/res4d.nii.gz" "$feat_dir/stats/corrections.nii.gz" \
    "$feat_dir/stats/threshac1.nii.gz" "$feat_dir/filtered_func_data.nii.gz"
