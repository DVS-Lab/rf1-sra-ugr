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

completion_timeout="${L2_COMPLETION_TIMEOUT_SECONDS:-7200}"
completion_poll="${L2_COMPLETION_POLL_SECONDS:-10}"
[[ "$completion_timeout" =~ ^[0-9]+$ ]] || {
    echo "ERROR: L2_COMPLETION_TIMEOUT_SECONDS must be a nonnegative integer." >&2
    exit 2
}
[[ "$completion_poll" =~ ^[1-9][0-9]*$ ]] || {
    echo "ERROR: L2_COMPLETION_POLL_SECONDS must be a positive integer." >&2
    exit 2
}

l2_output_complete() {
    local base="$1" cope cope_dir
    [[ -s "$base/design.mat" && -s "$base/design.con" ]] || return 1
    for cope in $(seq "$ncopes"); do
        cope_dir="$base/cope${cope}.feat"
        [[ -s "$cope_dir/design.mat" ]] || return 1
        [[ -s "$cope_dir/design.con" ]] || return 1
        [[ -s "$cope_dir/mask.nii.gz" ]] || return 1
        [[ -s "$cope_dir/stats/cope1.nii.gz" ]] || return 1
        [[ -s "$cope_dir/stats/zstat1.nii.gz" ]] || return 1
        [[ -s "$cope_dir/cluster_mask_zstat1.nii.gz" ]] || return 1
    done
}

report_missing_l2_outputs() {
    local base="$1" cope cope_dir relative
    for relative in design.mat design.con; do
        [[ -s "$base/$relative" ]] || printf '  %s\n' "$relative" >&2
    done
    for cope in $(seq "$ncopes"); do
        cope_dir="$base/cope${cope}.feat"
        for relative in \
            design.mat design.con mask.nii.gz \
            stats/cope1.nii.gz stats/zstat1.nii.gz cluster_mask_zstat1.nii.gz
        do
            [[ -s "$cope_dir/$relative" ]] || printf '  cope%s.feat/%s\n' "$cope" "$relative" >&2
        done
    done
}

wait_for_l2_completion() {
    local base="$1" waited=0
    if l2_output_complete "$base"; then
        echo "L2 output complete: $base"
        return 0
    fi

    echo "Waiting for internally submitted FEAT jobs (timeout ${completion_timeout}s): $base"
    while (( waited < completion_timeout )); do
        sleep "$completion_poll"
        waited=$((waited + completion_poll))
        if l2_output_complete "$base"; then
            echo "L2 output complete after ${waited}s: $base"
            return 0
        fi
    done

    echo "ERROR: timed out waiting for complete L2 output after ${waited}s: $base" >&2
    echo "Missing or empty required files:" >&2
    report_missing_l2_outputs "$base"
    return 1
}

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
        if l2_output_complete "$gfeat_dir"; then
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
wait_for_l2_completion "$gfeat_dir"
for cope in $(seq "$ncopes"); do
    cope_dir="$gfeat_dir/cope${cope}.feat"
    rm -f -- "$cope_dir/stats/res4d.nii.gz" "$cope_dir/stats/corrections.nii.gz" \
        "$cope_dir/stats/threshac1.nii.gz" "$cope_dir/filtered_func_data.nii.gz" \
        "$cope_dir/var_filtered_func_data.nii.gz"
done
