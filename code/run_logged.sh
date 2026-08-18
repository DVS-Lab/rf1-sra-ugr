#!/usr/bin/env bash

# Capture a local raw log and a compact, Git-trackable workflow record.

set -euo pipefail

usage() {
    cat >&2 <<'USAGE'
Usage: bash code/run_logged.sh [--label LABEL] [--include-full-log] -- COMMAND [ARGS...] [--check CHECK_COMMAND [ARGS...]]

Runs COMMAND, writes one timestamped raw log under ignored logs/runs/, and
writes one compact Git-trackable record under logs/records/.

The optional --check command runs only after COMMAND exits 0.
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=code/project_config.sh
source "${SCRIPT_DIR}/project_config.sh"

label=""
include_full_log=0
while (( $# )); do
    case "$1" in
        --label) label="$2"; shift 2 ;;
        --include-full-log) include_full_log=1; shift ;;
        --) shift; break ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown wrapper argument: $1" >&2; usage; exit 2 ;;
    esac
done

(( $# > 0 )) || { usage; exit 2; }

cmd=()
check_cmd=()
while (( $# )); do
    if [[ "$1" == "--check" ]]; then
        shift
        check_cmd=("$@")
        break
    fi
    cmd+=("$1")
    shift
done
(( ${#cmd[@]} > 0 )) || { usage; exit 2; }

if [[ -z "$label" ]]; then
    label="$(basename "${cmd[0]}")"
    label="${label%.*}"
fi
label="$(printf '%s' "$label" | tr -c 'A-Za-z0-9_.-' '_')"

timestamp="$(date +%Y%m%d-%H%M%S)"
raw_dir="${PROJECT_ROOT}/logs/runs"
record_dir="${PROJECT_ROOT}/logs/records"
raw_log="${raw_dir}/${timestamp}_${label}.log"
record="${record_dir}/${timestamp}_${label}.md"
status_file="${raw_log}.status"
mkdir -p "$raw_dir" "$record_dir"

git_commit="$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
branch="$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo unknown)"
host="$(hostname 2>/dev/null || echo unknown)"
user="$(whoami 2>/dev/null || echo unknown)"
cwd="$(pwd)"
command_string="$(printf '%q ' "${cmd[@]}")"
command_string="${command_string% }"
check_string=""
if (( ${#check_cmd[@]} )); then
    check_string="$(printf '%q ' "${check_cmd[@]}")"
    check_string="${check_string% }"
fi

echo "Writing raw log: $raw_log"
echo "Writing run record: $record"

set +e
(
    command_status=0
    check_status=none
    final_status=0

    printf 'RUN START: %s\nPROJECT_ROOT: %s\nGIT: %s %s\nHOST: %s\nUSER: %s\nPWD: %s\nCOMMAND: %s\n\n' \
        "$timestamp" "$PROJECT_ROOT" "$branch" "$git_commit" "$host" "$user" "$cwd" "$command_string"

    "${cmd[@]}"
    command_status=$?
    printf '\nCOMMAND EXIT: %s\n' "$command_status"

    if (( ${#check_cmd[@]} )) && (( command_status == 0 )); then
        printf '\nCHECK COMMAND: %s\n\n' "$check_string"
        "${check_cmd[@]}"
        check_status=$?
        printf '\nCHECK EXIT: %s\n' "$check_status"
    elif (( ${#check_cmd[@]} )); then
        check_status=skipped
        printf '\nCHECK SKIPPED: command failed, so post-run outputs were not validated.\n'
    fi

    final_status="$command_status"
    if [[ "$check_status" =~ ^[0-9]+$ ]] && (( check_status != 0 )); then
        final_status="$check_status"
    fi
    printf 'COMMAND_STATUS=%s\nCHECK_STATUS=%s\n' "$command_status" "$check_status" > "$status_file"
    exit "$final_status"
) 2>&1 | tee "$raw_log"
run_status=${PIPESTATUS[0]}
set -e

COMMAND_STATUS=unknown
CHECK_STATUS=none
if [[ -f "$status_file" ]]; then
    # shellcheck disable=SC1090
    source "$status_file"
    rm -f "$status_file"
fi

summary="$(grep -E 'CHECK (PASSED|FAILED):' "$raw_log" | tail -n 1 || true)"
[[ -n "$summary" ]] || summary="$(grep -E 'CHECK SKIPPED:' "$raw_log" | tail -n 1 || true)"
batch_plan="$(grep -E '^(EV|L1|L2|L3) batch plan:' "$raw_log" | tail -n 1 || true)"
if [[ -z "$summary" ]]; then
    if [[ "$CHECK_STATUS" == skipped ]]; then
        summary="CHECK SKIPPED: command failed, so post-run outputs were not validated."
    elif [[ "$COMMAND_STATUS" != 0 ]]; then
        summary="COMMAND FAILED: exit ${COMMAND_STATUS}."
    elif [[ "$CHECK_STATUS" == none ]]; then
        if [[ -n "$batch_plan" ]]; then
            summary="${batch_plan}; command completed."
        else
            summary="COMMAND COMPLETED: no check command provided."
        fi
    elif [[ "$CHECK_STATUS" == 0 ]]; then
        summary="CHECK COMPLETED: exit 0; no CHECK PASSED/FAILED line found."
    else
        summary="CHECK FAILED: exit ${CHECK_STATUS}; no CHECK PASSED/FAILED line found."
    fi
fi

include_tail=0
[[ "$COMMAND_STATUS" != 0 ]] && include_tail=1
if [[ "$CHECK_STATUS" != none && "$CHECK_STATUS" != skipped && "$CHECK_STATUS" != 0 ]]; then
    include_tail=1
fi

{
    echo "# Run Record: ${label}"
    echo
    echo "- Timestamp: ${timestamp}"
    echo "- Branch: ${branch}"
    echo "- Commit: ${git_commit}"
    echo "- Host: ${host}"
    echo "- User: ${user}"
    echo "- Working directory: \`${cwd}\`"
    echo "- Raw log: \`${raw_log}\`"
    echo "- Command exit: ${COMMAND_STATUS}"
    echo "- Check exit: ${CHECK_STATUS}"
    echo "- Summary: ${summary}"
    echo
    echo "## Command"
    echo
    echo '```bash'
    echo "$command_string"
    echo '```'
    if (( ${#check_cmd[@]} )); then
        echo
        echo "## Check"
        echo
        echo '```bash'
        echo "$check_string"
        echo '```'
    fi
    if (( include_full_log )); then
        echo
        echo "## Full Log"
        echo
        echo '```text'
        cat "$raw_log"
        echo '```'
    elif (( include_tail )); then
        echo
        echo "## Log Tail"
        echo
        echo '```text'
        tail -n "${RUN_RECORD_TAIL_LINES:-120}" "$raw_log"
        echo '```'
    fi
} > "$record"

echo "Run record saved: $record"
exit "$run_status"
