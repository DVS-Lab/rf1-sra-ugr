# UGR masks

All active masks are on the production modal MNI152NLin6Asym grid: shape
57 × 70 × 54, voxel size 2.70 × 2.70 × 2.97 mm, RAS orientation.

| Filename | Region | Role | Source | Used by | Provenance |
| --- | --- | --- | --- | --- | --- |
| `seed-pTPJ.nii.gz` | posterior temporoparietal junction | PPI seed | `rf1-norms/masks/seed-pTPJ.nii.gz` | `--ppi pTPJ` | Needs confirmation beyond source-repository identity. |
| `seed-dACC.nii.gz` | dorsal anterior cingulate cortex | PPI seed | `rf1-betrayal/masks/seed-dACC.nii.gz` | `--ppi dACC` | Needs confirmation beyond source-repository identity. |
| `seed-AIns.nii.gz` | anterior insula | PPI seed | renamed copy of `rf1-betrayal/masks/seed-AIns-clusterthresh.nii.gz` | `--ppi AIns` | Needs confirmation beyond source-repository identity. |

## Network-PPI maps

`nan_rPNAS_2mm_net0000.nii.gz` through
`nan_rPNAS_2mm_net0009.nii.gz` are the ten continuous, unthresholded maps used
for simultaneous network time-series estimation. Their sources are the
continuous maps committed at UGR revision `7ce32fd`; those files were
68 × 81 × 62 on the same MNI coordinate system. They were resampled with
trilinear interpolation (`nibabel` 5.3.2 `resample_from_to`, order 1) to the
affine and grid of the tracked canonical `seed-dACC.nii.gz` reference.

The historical root copies present immediately before the repository rebuild
were not restored: although they had the correct 57 × 70 × 54 geometry, they
were binary. That conflicts with the continuous-map network-PPI method.

Historical code assigns map 3 to DMN and map 7 to ECN. The implementation
retains those assignments for a controlled pilot, but the anatomical labels
remain provisional until checked against the original rPNAS network-map
distribution. File integrity and continuous-valued geometry are enforced by
the test suite; `network-maps.sha256` records the active resampled files.

The original repositories contain many additional result-derived masks,
manuscript figures, and historical seeds. They are not active inputs here and
remain available in those repositories and this repository's history.

Before introducing another seed, add `seed-<name>.nii.gz`, verify that its grid
matches the canonical fMRIPrep BOLD, and document its scientific provenance in
this table. Do not infer provenance from filenames alone.
