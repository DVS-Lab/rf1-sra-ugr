#!/usr/bin/env bash

# Combine UGR model-3 runs 1 and 2 within one subject/session using fixed effects.

set -euo pipefail

# The local fsl_sub shell backend otherwise gives each FEAT subprocess access
# to every CPU and may build a full-size worker pool for one-line command
# files. Keep run_L2stats.sh --jobs as the primary concurrency control while
# allowing an intentional environment override.
export FSLSUB_PARALLEL="${FSLSUB_PARALLEL:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=project_config.sh
source "${SCRIPT_DIR}/project_config.sh"

usage() {
    cat <<'EOF'
Usage: L2stats.sh SUBJECT TYPE [options]

TYPE is act, ppi_seed-<seed>, or nppi-<dmn|ecn>.

Options:
  --session ID    BIDS session (default: 01)
  --dry-run       Validate and print paths without writing
  --render-only   Render the .fsf without running FEAT
  --overwrite     Replace an existing generated GFEAT output
EOF
}

(( $# >= 2 )) || { usage >&2; exit 2; }
sub="$(normalize_subject "$1")"
type="$2"
shift 2
session="01"
mode="run"
overwrite=0
while (( $# )); do
    case "$1" in
        --session) session="$2"; shift 2 ;;
        --dry-run) mode="dry-run"; shift ;;
        --render-only) mode="render-only"; shift ;;
        --overwrite) overwrite=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
    esac
done
session="$(normalize_session "$session")"

case "$type" in
    act) template_type="act"; ncopes=17 ;;
    ppi_seed-*|nppi-dmn|nppi-ecn) template_type="ppi"; ncopes=18 ;;
    *) echo "ERROR: TYPE must be act, ppi_seed-<seed>, or nppi-<dmn|ecn>." >&2; exit 2 ;;
esac

smoothing=5
input1="$(l1_output_base "$sub" "$session" 1 "$type" "$smoothing").feat"
input2="$(l1_output_base "$sub" "$session" 2 "$type" "$smoothing").feat"
for input in "$input1" "$input2"; do
    [[ -f "$input/cluster_mask_zstat1.nii.gz" ]] || { echo "ERROR: complete L1 input required: $input" >&2; exit 1; }
done

output="$(l2_output_base "$sub" "$session" "$type" "$smoothing")"
template="${PROJECT_ROOT}/templates/L2_task-ugr_model-3_type-${template_type}.fsf"
subject_output="${FSL_DERIVATIVES_ROOT}/sub-${sub}/ses-${session}"
rendered="${subject_output}/L2_sub-${sub}_task-ugr_ses-${session}_model-3_type-${type}.fsf"
[[ -f "$template" ]] || { echo "ERROR: FEAT template not found: $template" >&2; exit 1; }

printf 'L2 plan (fixed effects across UGR runs 1 + 2)\n  run 1: %s\n  run 2: %s\n  output: %s.gfeat\n  FSLSUB_PARALLEL: %s\n' \
    "$input1" "$input2" "$output" "$FSLSUB_PARALLEL"
[[ "$mode" == dry-run ]] && exit 0

gfeat_dir="${output}.gfeat"
if [[ -e "$gfeat_dir" ]]; then
    if (( ! overwrite )); then
        if [[ -f "$gfeat_dir/cope${ncopes}.feat/cluster_mask_zstat1.nii.gz" ]]; then
            echo "Complete output already exists; skipping: $gfeat_dir"
            exit 0
        fi
        echo "ERROR: incomplete output exists: $gfeat_dir (use --overwrite)." >&2
        exit 1
    fi
    case "$gfeat_dir" in
        "${FSL_DERIVATIVES_ROOT}"/*) rm -rf -- "$gfeat_dir" ;;
        *) echo "ERROR: refusing to remove output outside FSL_DERIVATIVES_ROOT: $gfeat_dir" >&2; exit 1 ;;
    esac
fi

mkdir -p "$subject_output"
sed_escape() { printf '%s' "$1" | sed 's/[&@\\]/\\&/g'; }
sed -e "s@OUTPUT@$(sed_escape "$output")@g" \
    -e "s@INPUT1@$(sed_escape "$input1")@g" \
    -e "s@INPUT2@$(sed_escape "$input2")@g" \
    "$template" > "$rendered"
if grep -En 'OUTPUT|INPUT1|INPUT2' "$rendered" >/dev/null 2>&1; then
    echo "ERROR: unresolved placeholder remains in rendered template: $rendered" >&2
    exit 1
fi
echo "Rendered: $rendered"
[[ "$mode" == render-only ]] && exit 0

command -v feat >/dev/null 2>&1 || { echo "ERROR: feat is not available; load FSL first." >&2; exit 1; }
feat "$rendered"
for cope in $(seq "$ncopes"); do
    cope_dir="$gfeat_dir/cope${cope}.feat"
    rm -f -- "$cope_dir/stats/res4d.nii.gz" "$cope_dir/stats/corrections.nii.gz" \
        "$cope_dir/stats/threshac1.nii.gz" "$cope_dir/filtered_func_data.nii.gz" \
        "$cope_dir/var_filtered_func_data.nii.gz"
done
