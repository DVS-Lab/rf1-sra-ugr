# Run Record: workflow-audit-post-L2-activation-20260831

- Timestamp: 20260831-190409
- Branch: main
- Commit: 872ed13
- Host: CLA19787.tu.temple.edu
- User: tug87422
- Working directory: `/ZPOOL/data/projects/rf1-sra-ugr`
- Raw log: `/ZPOOL/data/projects/rf1-sra-ugr/logs/runs/20260831-190409_workflow-audit-post-L2-activation-20260831.log`
- Command exit: 0
- Check exit: none
- Summary: COMMAND COMPLETED: no check command provided.

## Command

```bash
python3 code/audit_workflow.py --sessions all --seed dACC --output-dir logs/audits/20260831-post-L2-activation
```

## Full Log

```text
RUN START: 20260831-190409
PROJECT_ROOT: /ZPOOL/data/projects/rf1-sra-ugr
GIT: main 872ed13
HOST: CLA19787.tu.temple.edu
USER: tug87422
PWD: /ZPOOL/data/projects/rf1-sra-ugr
COMMAND: python3 code/audit_workflow.py --sessions all --seed dACC --output-dir logs/audits/20260831-post-L2-activation

UGR WORKFLOW AUDIT
Sessions audited: 01,02
Visible UGR units: 711
Input-ready units: 708
Input-missing units: 3
EV-complete units: 707
EV todo: 1
L1 activation complete: 707
L1 activation todo: 0
L1 activation blocked by EVs: 1
L1 ppi_seed-dACC complete: 2
L1 ppi_seed-dACC todo: 705
L1 ppi_seed-dACC blocked by EVs/activation: 1
Input-ready subject-sessions with runs 1 and 2: 340
L2 activation complete/eligible: 338/339
L2 activation todo: 1
L2 activation blocked by L1: 1
L2 ppi_seed-dACC complete/eligible: 1/1
L2 ppi_seed-dACC todo: 0
L2 ppi_seed-dACC blocked by L1: 339
Detailed reports: /ZPOOL/data/projects/rf1-sra-ugr/logs/audits/20260831-post-L2-activation

COMMAND EXIT: 0
```
