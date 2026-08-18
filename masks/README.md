# UGR masks

Only masks directly usable by the retained seed-PPI workflow are tracked. All
three are on the production modal MNI152NLin6Asym grid: shape 57 × 70 × 54,
voxel size 2.70 × 2.70 × 2.97 mm, RAS orientation.

| Filename | Region | Role | Source | Used by | Provenance |
| --- | --- | --- | --- | --- | --- |
| `seed-pTPJ.nii.gz` | posterior temporoparietal junction | PPI seed | `rf1-norms/masks/seed-pTPJ.nii.gz` | `--ppi pTPJ` | Needs confirmation beyond source-repository identity. |
| `seed-dACC.nii.gz` | dorsal anterior cingulate cortex | PPI seed | `rf1-betrayal/masks/seed-dACC.nii.gz` | `--ppi dACC` | Needs confirmation beyond source-repository identity. |
| `seed-AIns.nii.gz` | anterior insula | PPI seed | renamed copy of `rf1-betrayal/masks/seed-AIns-clusterthresh.nii.gz` | `--ppi AIns` | Needs confirmation beyond source-repository identity. |

The original repositories contain many result-derived masks, manuscript
figures, network masks, and historical seeds. They are not active inputs here
and remain available in those repositories and this repository's history.

Before introducing another seed, add `seed-<name>.nii.gz`, verify that its grid
matches the canonical fMRIPrep BOLD, and document its scientific provenance in
this table. Do not infer provenance from filenames alone.
