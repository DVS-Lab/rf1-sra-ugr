#!/usr/bin/env bash

# Batch UGR model-3 L1 analyses with deterministic shell job control.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

usage() {
    cat <<'EOF'
Usage: run_L1stats.sh [options]

Options:
  --manifest FILE   TSV columns: subject, session, run
  --subject ID      Run one participant/run instead of a manifest
  --session ID      Session for --subject (default: 01)
  --run ID          Run for --subject (default: 1)
  --ppi VALUE       0/act or seed name (default: 0)
  --jobs N          Maximum concurrent FEAT jobs (default: 20)
  --dry-run         Validate inputs and print each plan
  --render-only     Render .fsf files without running FEAT
  --overwrite       Replace existing generated FEAT outputs
  --log-dir DIR     Write one log per L1 unit
EOF
}

manifest=""
subject=""
session="01"
run="1"
ppi="0"
jobs=20
mode="run"
overwrite=0
log_dir=""
while (( $# )); do
    case "$1" in
        --manifest) manifest="$2"; shift 2 ;;
        --subject) subject="$2"; shift 2 ;;
        --session) session="$2"; shift 2 ;;
        --run) run="$2"; shift 2 ;;
        --ppi) ppi="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --dry-run) mode="dry-run"; shift ;;
        --render-only) mode="render-only"; shift ;;
        --overwrite) overwrite=1; shift ;;
        --log-dir) log_dir="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: --jobs must be positive." >&2; exit 2; }
[[ -n "$manifest" || -n "$subject" ]] || { echo "ERROR: provide --manifest or --subject." >&2; exit 2; }
[[ -z "$manifest" || -z "$subject" ]] || { echo "ERROR: --manifest and --subject are mutually exclusive." >&2; exit 2; }

units=()
if [[ -n "$manifest" ]]; then
    [[ -f "$manifest" ]] || { echo "ERROR: manifest not found: $manifest" >&2; exit 1; }
    while IFS=$'\t' read -r unit_sub unit_session unit_run extra || [[ -n "${unit_sub:-}" ]]; do
        unit_sub="${unit_sub%$'\r'}"; unit_session="${unit_session%$'\r'}"; unit_run="${unit_run%$'\r'}"
        [[ "$unit_sub" == subject ]] && continue
        [[ -z "$unit_sub" ]] && continue
        [[ -z "${extra:-}" ]] || { echo "ERROR: malformed manifest row for sub-${unit_sub}." >&2; exit 1; }
        units+=("${unit_sub#sub-}|${unit_session#ses-}|${unit_run}")
    done < "$manifest"
else
    units+=("${subject#sub-}|${session#ses-}|${run}")
fi
(( ${#units[@]} > 0 )) || { echo "ERROR: no L1 work units selected." >&2; exit 1; }
duplicates="$(printf '%s\n' "${units[@]}" | sort | uniq -d)"
[[ -z "$duplicates" ]] || { echo "ERROR: duplicate L1 units:" >&2; echo "$duplicates" >&2; exit 1; }

printf 'L1 batch plan: %d unit(s), %d job(s), model 3, PPI=%s\n' "${#units[@]}" "$jobs" "$ppi"
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
        echo "ERROR: failed L1 unit: $label${logfile:+ (log: $logfile)}" >&2
        failures=$((failures + 1))
    else
        echo "DONE: $label"
    fi
    pids=("${pids[@]:1}")
    labels=("${labels[@]:1}")
    logfiles=("${logfiles[@]:1}")
}

for unit in "${units[@]}"; do
    IFS='|' read -r unit_sub unit_session unit_run <<< "$unit"
    label="sub-${unit_sub} ses-${unit_session} run-${unit_run}"
    cmd=(bash "${SCRIPT_DIR}/L1stats.sh" "$unit_sub" "$unit_run" "$ppi" --session "$unit_session")
    [[ "$mode" == dry-run ]] && cmd+=(--dry-run)
    [[ "$mode" == render-only ]] && cmd+=(--render-only)
    (( overwrite )) && cmd+=(--overwrite)
    if [[ "$mode" == dry-run ]]; then
        "${cmd[@]}" || failures=$((failures + 1))
        continue
    fi
    logfile=""
    if [[ -n "$log_dir" ]]; then
        logfile="${log_dir}/sub-${unit_sub}_ses-${unit_session}_task-ugr_run-${unit_run}.log"
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
