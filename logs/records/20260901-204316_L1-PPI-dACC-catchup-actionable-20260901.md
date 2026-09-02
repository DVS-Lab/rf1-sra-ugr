# Run Record: L1-PPI-dACC-catchup-actionable-20260901

- Timestamp: 20260901-204316
- Branch: main
- Commit: 0aed241
- Host: CLA19787.tu.temple.edu
- User: tug87422
- Working directory: `/ZPOOL/data/projects/rf1-sra-ugr`
- Raw log: `/ZPOOL/data/projects/rf1-sra-ugr/logs/runs/20260901-204316_L1-PPI-dACC-catchup-actionable-20260901.log`
- Command exit: 0
- Check exit: none
- Summary: L1 batch plan: 4 unit(s), 4 job(s), model 3, PPI=dACC; command completed.

## Command

```bash
bash code/run_L1stats.sh --manifest logs/runlists/UGR-catchup-actionable-20260901.tsv --ppi dACC --jobs 4 --log-dir logs/L1-PPI-dACC-catchup-actionable-20260901
```

## Full Log

```text
RUN START: 20260901-204316
PROJECT_ROOT: /ZPOOL/data/projects/rf1-sra-ugr
GIT: main 0aed241
HOST: CLA19787.tu.temple.edu
USER: tug87422
PWD: /ZPOOL/data/projects/rf1-sra-ugr
COMMAND: bash code/run_L1stats.sh --manifest logs/runlists/UGR-catchup-actionable-20260901.tsv --ppi dACC --jobs 4 --log-dir logs/L1-PPI-dACC-catchup-actionable-20260901

L1 batch plan: 4 unit(s), 4 job(s), model 3, PPI=dACC
Per-unit logs: logs/L1-PPI-dACC-catchup-actionable-20260901
START: sub-11116 ses-02 run-1 (log: logs/L1-PPI-dACC-catchup-actionable-20260901/sub-11116_ses-02_task-ugr_run-1.log)
START: sub-11116 ses-02 run-2 (log: logs/L1-PPI-dACC-catchup-actionable-20260901/sub-11116_ses-02_task-ugr_run-2.log)
START: sub-12032 ses-01 run-1 (log: logs/L1-PPI-dACC-catchup-actionable-20260901/sub-12032_ses-01_task-ugr_run-1.log)
START: sub-12032 ses-01 run-2 (log: logs/L1-PPI-dACC-catchup-actionable-20260901/sub-12032_ses-01_task-ugr_run-2.log)
DONE: sub-11116 ses-02 run-1
DONE: sub-11116 ses-02 run-2
DONE: sub-12032 ses-01 run-1
DONE: sub-12032 ses-01 run-2

COMMAND EXIT: 0
```
