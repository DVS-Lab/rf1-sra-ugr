#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Use the project's existing path and naming definitions.
source "${SCRIPT_DIR}/project_config.sh"

subjects_file="${SCRIPT_DIR}/L3-act-subjects.txt"
paths_file="${SCRIPT_DIR}/L3-act-input-paths.txt"

# Upstream run-level imaging QC.
qc_file="${UPSTREAM_ROOT}/qc/run_qc.tsv"

[[ -f "$qc_file" ]] || {
    echo "QC file not found: $qc_file" >&2
    exit 1
}

# Return success if this UGR run passes imaging QC.
run_passes_qc() {
    local sub="$1"
    local run="$2"

    awk -F '\t' -v subject="$sub" -v run="$run" '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                col[$i] = i
            }
            next
        }

        $(col["subject"]) == subject &&
        $(col["session"]) == "01" &&
        $(col["task"]) == "ugr" &&
        $(col["run"]) == run {
            found = 1

            if ($(col["qc_status"]) == "pass" &&
                $(col["imaging_qc_outlier"]) == "FALSE") {
                good = 1
            }

            exit
        }

        END {
            exit !(found && good)
        }
    ' "$qc_file"
}

# Start fresh.
: > "$subjects_file"
: > "$paths_file"

# Look through all subjects that have FSL derivatives.
for subject_dir in "${FSL_DERIVATIVES_ROOT}"/sub-*; do

    [[ -d "$subject_dir" ]] || continue

    sub="${subject_dir##*/}"
    sub="${sub#sub-}"

    # Current L1 activation outputs for runs 1 and 2.
    l1_run1="$(l1_output_base "$sub" 01 1 act 5).feat"
    l1_run2="$(l1_output_base "$sub" 01 2 act 5).feat"

    # A run is usable only if it passes imaging QC and its L1 is complete.
    run1_good=false
    run2_good=false

    if run_passes_qc "$sub" 1 &&
       [[ -f "${l1_run1}/cluster_mask_zstat1.nii.gz" ]]; then
        run1_good=true
    fi

    if run_passes_qc "$sub" 2 &&
       [[ -f "${l1_run2}/cluster_mask_zstat1.nii.gz" ]]; then
        run2_good=true
    fi

    # Current L2 activation output.
    l2_dir="$(l2_output_base "$sub" 01 act 5).gfeat"

    # If both runs are good and L2 is complete, use L2.
    if $run1_good && $run2_good &&
       [[ -f "${l2_dir}/cope17.feat/cluster_mask_zstat1.nii.gz" ]]; then

        printf '%s\n' "$sub" >> "$subjects_file"
        printf '%s\n' \
            "${l2_dir}/copeCOPENUM.feat/stats/cope1.nii.gz" \
            >> "$paths_file"

        continue
    fi

    # If exactly one run is good, use that run's L1 output.
    if $run1_good && ! $run2_good; then

        printf '%s\n' "$sub" >> "$subjects_file"
        printf '%s\n' \
            "${l1_run1}/stats/copeCOPENUM.nii.gz" \
            >> "$paths_file"

    elif $run2_good && ! $run1_good; then

        printf '%s\n' "$sub" >> "$subjects_file"
        printf '%s\n' \
            "${l1_run2}/stats/copeCOPENUM.nii.gz" \
            >> "$paths_file"

    fi

done