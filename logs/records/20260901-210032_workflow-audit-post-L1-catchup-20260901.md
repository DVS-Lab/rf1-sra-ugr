# Run Record: workflow-audit-post-L1-catchup-20260901

- Timestamp: 20260901-210032
- Branch: main
- Commit: 0aed241
- Host: CLA19787.tu.temple.edu
- User: tug87422
- Working directory: `/ZPOOL/data/projects/rf1-sra-ugr`
- Raw log: `/ZPOOL/data/projects/rf1-sra-ugr/logs/runs/20260901-210032_workflow-audit-post-L1-catchup-20260901.log`
- Command exit: 0
- Check exit: none
- Summary: COMMAND COMPLETED: no check command provided.

## Command

```bash
python3 code/audit_workflow.py --sessions all --seed dACC --output-dir logs/audits/20260901-post-L1-catchup
```

## Full Log

```text
RUN START: 20260901-210032
PROJECT_ROOT: /ZPOOL/data/projects/rf1-sra-ugr
GIT: main 0aed241
HOST: CLA19787.tu.temple.edu
USER: tug87422
PWD: /ZPOOL/data/projects/rf1-sra-ugr
COMMAND: python3 code/audit_workflow.py --sessions all --seed dACC --output-dir logs/audits/20260901-post-L1-catchup

UGR WORKFLOW AUDIT
Sessions audited: 01,02
Visible UGR units: 713
Input-ready units: 712
Input-missing units: 1
EV-complete units: 711
EV todo: 1
L1 activation complete: 711
L1 activation todo: 0
L1 activation blocked by EVs: 1
L1 ppi_seed-dACC complete: 711
L1 ppi_seed-dACC todo: 0
L1 ppi_seed-dACC blocked by EVs/activation: 1
Input-ready subject-sessions with runs 1 and 2: 342
L2 activation complete/eligible: 339/341
L2 activation todo: 2
L2 activation blocked by L1: 1
L2 ppi_seed-dACC complete/eligible: 339/341
L2 ppi_seed-dACC todo: 2
L2 ppi_seed-dACC blocked by L1: 1
Detailed reports: /ZPOOL/data/projects/rf1-sra-ugr/logs/audits/20260901-post-L1-catchup

COMMAND EXIT: 0
```
