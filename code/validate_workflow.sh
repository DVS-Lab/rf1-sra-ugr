#!/usr/bin/env bash

# Static and synthetic validation for the authoritative UGR model-3 workflow.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
shell_scripts=(
    project_config.sh run_gen3colfiles.sh run_logged.sh
    L1stats.sh run_L1stats.sh L2stats.sh run_L2stats.sh
    validate_workflow.sh
)
python_scripts=(
    audit_workflow.py build_L1_manifest.py build_L2_manifest.py build_model3_nppi_template.py
    gen_model3_evs.py ugr_qc.py
)

for script in "${shell_scripts[@]}"; do
    bash -n "${SCRIPT_DIR}/${script}"
done
echo "PASS: bash syntax"

if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -x "${shell_scripts[@]/#/${SCRIPT_DIR}/}"
    echo "PASS: ShellCheck"
else
    echo "SKIP: ShellCheck is not installed"
fi

PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/rf1-sra-ugr-pycache" \
    python3 -m py_compile "${python_scripts[@]/#/${SCRIPT_DIR}/}"
echo "PASS: Python syntax"

production=(
    project_config.sh audit_workflow.py build_L1_manifest.py build_L2_manifest.py gen_model3_evs.py ugr_qc.py
    run_gen3colfiles.sh L1stats.sh run_L1stats.sh L2stats.sh run_L2stats.sh
)
if grep -En 'rf1-sra-data|rf1-sra/stimuli|_raw\.csv|fmriprep-24|confounds_tedana-24' \
    "${production[@]/#/${SCRIPT_DIR}/}"; then
    echo "ERROR: active code contains a private, raw, or obsolete production dependency." >&2
    exit 1
fi
echo "PASS: upstream/downstream boundary"

if find "$SCRIPT_DIR" "$PROJECT_ROOT/templates" -type f ! -name 'README.md' \
    \( -iname '*model-2*' -o -iname '*model-3b*' \) | grep -q .; then
    echo "ERROR: historical model 2/3b file is active." >&2
    exit 1
fi
echo "PASS: model 3 is the only active model"

act_template="$PROJECT_ROOT/templates/L1_task-ugr_model-3_type-act.fsf"
ppi_template="$PROJECT_ROOT/templates/L1_task-ugr_model-3_type-ppi.fsf"
nppi_template="$PROJECT_ROOT/templates/L1_task-ugr_model-3_type-nppi.fsf"
[[ "$(grep -c '^set fmri(evtitle[0-9]\+)' "$act_template")" -eq 11 ]]
[[ "$(grep -c '^set fmri(conname_real\.[0-9]\+)' "$act_template")" -eq 17 ]]
[[ "$(grep -c '^set fmri(custom[0-9]\+)' "$act_template")" -eq 11 ]]
[[ "$(grep -c '^set fmri(ortho[0-9]\+\.[0-9]\+) 1' "$act_template" || true)" -eq 0 ]]
echo "PASS: activation template has 11 EVs, 17 contrasts, and no FEAT orthogonalization"

[[ "$(grep -c '^set fmri(convolve11) 3' "$act_template")" -eq 1 ]]
[[ "$(grep -c '^set fmri(convolve11) 3' "$ppi_template")" -eq 1 ]]
[[ "$(grep -c '^set fmri(convolve11) 3' "$nppi_template")" -eq 1 ]]
echo "PASS: missed-trial EV uses task convolution in activation, seed-PPI, and network-PPI templates"

python3 "$SCRIPT_DIR/build_model3_nppi_template.py" \
    --source "$ppi_template" --output "$nppi_template" --check
[[ "$(grep -c '^set fmri(evtitle[0-9]\+)' "$nppi_template")" -eq 32 ]]
[[ "$(grep -c '^set fmri(conname_real\.[0-9]\+)' "$nppi_template")" -eq 18 ]]
[[ "$(grep -c '^set fmri(custom[0-9]\+)' "$nppi_template")" -eq 21 ]]
[[ "$(grep -c '^set fmri(ortho[0-9]\+\.[0-9]\+) 1' "$nppi_template" || true)" -eq 0 ]]
echo "PASS: network-PPI template is reproducible with 32 EVs, 18 contrasts, and no FEAT orthogonalization"

for template in "$PROJECT_ROOT"/templates/*.fsf; do
    if [[ "$(grep -c '^set fmri(featwatcher_yn) 0$' "$template")" -ne 1 ]]; then
        echo "ERROR: FEAT progress watcher is not disabled exactly once: $template" >&2
        exit 1
    fi
done
echo "PASS: FEAT progress watcher is disabled in every active template"

cd "$PROJECT_ROOT"
python3 -m unittest discover -s tests -p 'test_*.py' -v
