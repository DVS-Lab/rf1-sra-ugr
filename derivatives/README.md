# Generated derivatives

Generated analysis products are local data and are not version-controlled.
The expected layout is:

```text
derivatives/fsl/
  EVfiles/
    sub-XXXXX/
      ses-01/
        ugr/model-3/run-*_*.txt
  sub-XXXXX/
    ses-01/
      L1_task-ugr_ses-01_model-3_type-*.feat/
      L2_task-ugr_ses-01_model-3_type-*.gfeat/
      L1_sub-...fsf
      L2_sub-...fsf
      ts_task-ugr_...txt
```

The source templates, code, tests, documentation, and seed masks are tracked;
generated EVs, rendered per-subject FSFs, physiological series, FEAT/GFEAT
trees, and other large derivatives are ignored.
