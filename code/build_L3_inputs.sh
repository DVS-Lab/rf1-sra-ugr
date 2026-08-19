#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Use the project's existing path and naming definitions.
source "${SCRIPT_DIR}/project_config.sh"

subjects_file="${SCRIPT_DIR}/L3-act-subjects.txt"
paths_file="${SCRIPT_DIR}/L3-act-input-paths.txt"

# Start fresh.
: > "$subjects_file"
: > "$paths_file"

# Look through all subjects that have FSL derivatives.
for subject_dir in "${FSL_DERIVATIVES_ROOT}"/sub-*; do

    [[ -d "$subject_dir" ]] || continue

    sub="${subject_dir##*/}"
    sub="${sub#sub-}"

    # Current L2 activation output.
    l2_dir="$(l2_output_base "$sub" 01 act 5).gfeat"

    # If L2 is complete, use it and do not consider L1.
    if [[ -f "${l2_dir}/cope17.feat/cluster_mask_zstat1.nii.gz" ]]; then
        printf '%s\n' "$sub" >> "$subjects_file"
        printf '%s\n' \
            "${l2_dir}/copeCOPENUM.feat/stats/cope1.nii.gz" \
            >> "$paths_file"
        continue
    fi

    # Current L1 activation outputs for runs 1 and 2.
    l1_run1="$(l1_output_base "$sub" 01 1 act 5).feat"
    l1_run2="$(l1_output_base "$sub" 01 2 act 5).feat"

    # If exactly one L1 run is complete, use that run.
    if [[ -f "${l1_run1}/cluster_mask_zstat1.nii.gz" &&
          ! -f "${l1_run2}/cluster_mask_zstat1.nii.gz" ]]; then

        printf '%s\n' "$sub" >> "$subjects_file"
        printf '%s\n' \
            "${l1_run1}/stats/copeCOPENUM.nii.gz" \
            >> "$paths_file"

    elif [[ -f "${l1_run2}/cluster_mask_zstat1.nii.gz" &&
            ! -f "${l1_run1}/cluster_mask_zstat1.nii.gz" ]]; then

        printf '%s\n' "$sub" >> "$subjects_file"
        printf '%s\n' \
            "${l1_run2}/stats/copeCOPENUM.nii.gz" \
            >> "$paths_file"
    fi

done