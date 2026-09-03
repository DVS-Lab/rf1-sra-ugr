# Run Record: workflow-audit-post-L1-nPPI-dmn-20260903

- Timestamp: 20260903-074908
- Branch: main
- Commit: 8506ac1
- Host: CLA19787.tu.temple.edu
- User: tug87422
- Working directory: `/ZPOOL/data/projects/rf1-sra-ugr`
- Raw log: `/ZPOOL/data/projects/rf1-sra-ugr/logs/runs/20260903-074908_workflow-audit-post-L1-nPPI-dmn-20260903.log`
- Command exit: 0
- Check exit: none
- Summary: COMMAND COMPLETED: no check command provided.

## Command

```bash
python3 code/audit_workflow.py --sessions all --ppi-type nppi-dmn --output-dir logs/audits/20260903-post-L1-nppi-dmn
```

## Full Log

```text
RUN START: 20260903-074908
PROJECT_ROOT: /ZPOOL/data/projects/rf1-sra-ugr
GIT: main 8506ac1
HOST: CLA19787.tu.temple.edu
USER: tug87422
PWD: /ZPOOL/data/projects/rf1-sra-ugr
COMMAND: python3 code/audit_workflow.py --sessions all --ppi-type nppi-dmn --output-dir logs/audits/20260903-post-L1-nppi-dmn

UGR WORKFLOW AUDIT
Sessions audited: 01,02
Visible UGR units: 713
Input-ready units: 712
Input-missing units: 1
EV-complete units: 0
EV todo: 712
L1 activation complete: 0
L1 activation todo: 0
L1 activation blocked by EVs: 712
L1 nppi-dmn complete: 0
L1 nppi-dmn todo: 0
L1 nppi-dmn blocked by EVs/activation: 712
Input-ready subject-sessions with runs 1 and 2: 342
L2 activation complete/eligible: 0/0
L2 activation todo: 0
L2 activation blocked by L1: 342
L2 nppi-dmn complete/eligible: 0/0
L2 nppi-dmn todo: 0
L2 nppi-dmn blocked by L1: 342
Detailed reports: /ZPOOL/data/projects/rf1-sra-ugr/logs/audits/20260903-post-L1-nppi-dmn

COMMAND EXIT: 0
```
