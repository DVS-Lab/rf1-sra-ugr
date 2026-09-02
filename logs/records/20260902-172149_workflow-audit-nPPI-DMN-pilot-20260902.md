# Run Record: workflow-audit-nPPI-DMN-pilot-20260902

- Timestamp: 20260902-172149
- Branch: main
- Commit: 01e7959
- Host: CLA19787.tu.temple.edu
- User: tug87422
- Working directory: `/ZPOOL/data/projects/rf1-sra-ugr`
- Raw log: `/ZPOOL/data/projects/rf1-sra-ugr/logs/runs/20260902-172149_workflow-audit-nPPI-DMN-pilot-20260902.log`
- Command exit: 0
- Check exit: none
- Summary: COMMAND COMPLETED: no check command provided.

## Command

```bash
python3 code/audit_workflow.py --sessions all --ppi-type nppi-dmn --output-dir logs/audits/20260902-nppi-dmn-pilot
```

## Full Log

```text
RUN START: 20260902-172149
PROJECT_ROOT: /ZPOOL/data/projects/rf1-sra-ugr
GIT: main 01e7959
HOST: CLA19787.tu.temple.edu
USER: tug87422
PWD: /ZPOOL/data/projects/rf1-sra-ugr
COMMAND: python3 code/audit_workflow.py --sessions all --ppi-type nppi-dmn --output-dir logs/audits/20260902-nppi-dmn-pilot

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
L1 nppi-dmn complete: 1
L1 nppi-dmn todo: 710
L1 nppi-dmn blocked by EVs/activation: 1
Input-ready subject-sessions with runs 1 and 2: 342
L2 activation complete/eligible: 341/341
L2 activation todo: 0
L2 activation blocked by L1: 1
L2 nppi-dmn complete/eligible: 0/0
L2 nppi-dmn todo: 0
L2 nppi-dmn blocked by L1: 342
Detailed reports: /ZPOOL/data/projects/rf1-sra-ugr/logs/audits/20260902-nppi-dmn-pilot

COMMAND EXIT: 0
```
