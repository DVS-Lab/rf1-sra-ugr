#!/usr/bin/env bash

# Shared paths and output naming for the downstream RF1-SRA UGR workflow.
# Source this file; do not execute it directly.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"
UPSTREAM_ROOT="${RF1_SRA_UPSTREAM_ROOT:-/ZPOOL/data/projects/rf1-sra-linux2}"
BIDS_ROOT="${BIDS_ROOT:-${UPSTREAM_ROOT}/bids}"
FMRIPREP_ROOT="${FMRIPREP_ROOT:-${UPSTREAM_ROOT}/derivatives/fmriprep}"
CONFOUNDS_ROOT="${CONFOUNDS_ROOT:-${UPSTREAM_ROOT}/derivatives/fsl/confounds_tedana}"
FSL_DERIVATIVES_ROOT="${FSL_DERIVATIVES_ROOT:-${PROJECT_ROOT}/derivatives/fsl}"
NPPI_NETWORK_MAPS_ROOT="${NPPI_NETWORK_MAPS_ROOT:-${PROJECT_ROOT}/masks}"

normalize_subject() {
    printf '%s\n' "${1#sub-}"
}

normalize_session() {
    printf '%s\n' "${1#ses-}"
}

analysis_type_from_ppi() {
    case "$1" in
        0|act) printf '%s\n' act ;;
        dmn|ecn) printf 'nppi-%s\n' "$1" ;;
        nppi-dmn|nppi-ecn) printf '%s\n' "$1" ;;
        *) printf 'ppi_seed-%s\n' "$1" ;;
    esac
}

model3_ev_prefix() {
    local sub session run
    sub="$(normalize_subject "$1")"
    session="$(normalize_session "$2")"
    run="$3"
    printf '%s/EVfiles/sub-%s/ses-%s/ugr/model-3/run-%s\n' \
        "$FSL_DERIVATIVES_ROOT" "$sub" "$session" "$run"
}

l1_output_base() {
    local sub session run type smoothing
    sub="$(normalize_subject "$1")"
    session="$(normalize_session "$2")"
    run="$3"
    type="$4"
    smoothing="${5:-5}"
    printf '%s/sub-%s/ses-%s/L1_task-ugr_ses-%s_model-3_type-%s_run-%s_sm-%s\n' \
        "$FSL_DERIVATIVES_ROOT" "$sub" "$session" "$session" "$type" "$run" "$smoothing"
}

l2_output_base() {
    local sub session type smoothing
    sub="$(normalize_subject "$1")"
    session="$(normalize_session "$2")"
    type="$3"
    smoothing="${4:-5}"
    printf '%s/sub-%s/ses-%s/L2_task-ugr_ses-%s_model-3_type-%s_sm-%s\n' \
        "$FSL_DERIVATIVES_ROOT" "$sub" "$session" "$session" "$type" "$smoothing"
}
