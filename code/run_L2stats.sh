#!/usr/bin/env bash

# Batch UGR model-3 L2 fixed-effects analyses.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

usage() {
    cat <<'EOF'
Usage: run_L2stats.sh [options]

Options:
  --manifest FILE   TSV columns: subject, session
  --subject ID      Run one subject/session instead of a manifest
  --session ID      Session for --subject (default: 01)
  --type TYPE        act, ppi_seed-<seed>, or nppi-<dmn|ecn> (required)
  --jobs N          Maximum concurrent FEAT jobs (default: 20)
  --dry-run         Validate and print each L2 plan
  --render-only     Render .fsf files without running FEAT
  --overwrite       Replace existing generated GFEAT outputs
  --log-dir DIR     Write one log per L2 unit
EOF
}

manifest=""
subject=""
session="01"
type=""
jobs=20
mode="run"
overwrite=0
log_dir=""
while (( $# )); do
    case "$1" in
        --manifest) manifest="$2"; shift 2 ;;
        --subject) subject="$2"; shift 2 ;;
        --session) session="$2"; shift 2 ;;
        --type) type="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --dry-run) mode="dry-run"; shift ;;
        --render-only) mode="render-only"; shift ;;
        --overwrite) overwrite=1; shift ;;
        --log-dir) log_dir="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done
case "$type" in
    act|ppi_seed-?*|nppi-dmn|nppi-ecn) ;;
    *) echo "ERROR: --type must be act, ppi_seed-<seed>, or nppi-<dmn|ecn>." >&2; exit 2 ;;
esac
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: --jobs must be positive." >&2; exit 2; }
[[ -n "$manifest" || -n "$subject" ]] || { echo "ERROR: provide --manifest or --subject." >&2; exit 2; }
[[ -z "$manifest" || -z "$subject" ]] || { echo "ERROR: --manifest and --subject are mutually exclusive." >&2; exit 2; }

units=()
if [[ -n "$manifest" ]]; then
    [[ -f "$manifest" ]] || { echo "ERROR: manifest not found: $manifest" >&2; exit 1; }
    while IFS=$'\t' read -r unit_sub unit_session extra || [[ -n "${unit_sub:-}" ]]; do
        unit_sub="${unit_sub%$'\r'}"; unit_session="${unit_session%$'\r'}"
        [[ "$unit_sub" == subject ]] && continue
        [[ -z "$unit_sub" ]] && continue
        [[ -z "${extra:-}" ]] || { echo "ERROR: malformed L2 manifest row." >&2; exit 1; }
        units+=("${unit_sub#sub-}|${unit_session#ses-}")
    done < "$manifest"
else
    units+=("${subject#sub-}|${session#ses-}")
fi
(( ${#units[@]} > 0 )) || { echo "ERROR: no L2 work units selected." >&2; exit 1; }

printf 'L2 batch plan: %d unit(s), %d job(s), model 3, type=%s\n' "${#units[@]}" "$jobs" "$type"
if [[ -n "$log_dir" && "$mode" != dry-run ]]; then
    mkdir -p "$log_dir"
    printf 'Per-unit logs: %s\n' "$log_dir"
fi

pids=()
labels=()
logfiles=()
failures=0
wait_oldest() {
    local pid="${pids[0]}" label="${labels[0]}" logfile="${logfiles[0]}"
    if ! wait "$pid"; then
        echo "ERROR: failed L2 unit: $label${logfile:+ (log: $logfile)}" >&2
        failures=$((failures + 1))
    else
        echo "DONE: $label"
    fi
    pids=("${pids[@]:1}")
    labels=("${labels[@]:1}")
    logfiles=("${logfiles[@]:1}")
}

for unit in "${units[@]}"; do
    IFS='|' read -r unit_sub unit_session <<< "$unit"
    label="sub-${unit_sub} ses-${unit_session} type-${type}"
    cmd=(bash "${SCRIPT_DIR}/L2stats.sh" "$unit_sub" "$type" --session "$unit_session")
    [[ "$mode" == dry-run ]] && cmd+=(--dry-run)
    [[ "$mode" == render-only ]] && cmd+=(--render-only)
    (( overwrite )) && cmd+=(--overwrite)
    if [[ "$mode" == dry-run ]]; then
        "${cmd[@]}" || failures=$((failures + 1))
        continue
    fi
    logfile=""
    if [[ -n "$log_dir" ]]; then
        logfile="${log_dir}/sub-${unit_sub}_ses-${unit_session}_type-${type}.log"
        echo "START: $label (log: $logfile)"
        "${cmd[@]}" > "$logfile" 2>&1 &
    else
        echo "START: $label"
        "${cmd[@]}" &
    fi
    pids+=("$!")
    labels+=("$label")
    logfiles+=("$logfile")
    (( ${#pids[@]} >= jobs )) && wait_oldest
done
while (( ${#pids[@]} )); do wait_oldest; done
(( failures == 0 )) || exit 1
