from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from gen_model3_evs import generate


FIXTURE = ROOT / "tests" / "fixtures" / "synthetic_ugr_events.tsv"


class WorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.bids = self.base / "bids"
        self.fmriprep = self.base / "fmriprep"
        self.confounds = self.base / "confounds"
        self.fsl = self.base / "fsl"
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.network_maps = self.base / "network-maps"
        self.network_maps.mkdir()
        for index in range(10):
            (self.network_maps / f"nan_rPNAS_2mm_net000{index}.nii.gz").write_bytes(b"fake")
        (self.bin / "fslnvols").write_text("#!/usr/bin/env bash\necho 100\n", encoding="utf-8")
        (self.bin / "fslmeants").write_text(
            "#!/usr/bin/env bash\n"
            "out=''\n"
            "while (($#)); do if [[ $1 == -o ]]; then out=$2; shift 2; else shift; fi; done\n"
            "printf '0\\n%.0s' {1..100} > \"$out\"\n",
            encoding="utf-8",
        )
        (self.bin / "fslmerge").write_text(
            "#!/usr/bin/env bash\n"
            "[[ $1 == -t ]] || exit 2\n"
            "printf fake > \"$2\"\n",
            encoding="utf-8",
        )
        (self.bin / "fsl_glm").write_text(
            "#!/usr/bin/env bash\n"
            "out=''\n"
            "while (($#)); do if [[ $1 == -o ]]; then out=$2; shift 2; else shift; fi; done\n"
            "awk 'BEGIN { for (row=1; row<=100; row++) { "
            "for (column=1; column<=10; column++) "
            "printf \"%s%.6f\", (column == 1 ? \"\" : \" \"), row + column / 100; "
            "print \"\" } }' > \"$out\"\n",
            encoding="utf-8",
        )
        for command in ("fslnvols", "fslmeants", "fslmerge", "fsl_glm"):
            (self.bin / command).chmod(0o755)
        self.env = os.environ.copy()
        self.env.pop("FSLSUB_PARALLEL", None)
        self.env.update(
            {
                "BIDS_ROOT": str(self.bids),
                "FMRIPREP_ROOT": str(self.fmriprep),
                "CONFOUNDS_ROOT": str(self.confounds),
                "FSL_DERIVATIVES_ROOT": str(self.fsl),
                "NPPI_NETWORK_MAPS_ROOT": str(self.network_maps),
                "PATH": f"{self.bin}:{self.env.get('PATH', '')}",
            }
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def prepare_run(self, run: str, *, misses: bool) -> Path:
        subject = "99999"
        session = "01"
        stem = f"sub-{subject}_ses-{session}_task-ugr_run-{run}"
        events_dir = self.bids / f"sub-{subject}" / f"ses-{session}" / "func"
        bold_dir = self.fmriprep / f"sub-{subject}" / f"ses-{session}" / "func"
        confound_dir = self.confounds / f"sub-{subject}"
        events_dir.mkdir(parents=True, exist_ok=True)
        bold_dir.mkdir(parents=True, exist_ok=True)
        confound_dir.mkdir(parents=True, exist_ok=True)
        events = events_dir / f"{stem}_events.tsv"
        if misses:
            shutil.copyfile(FIXTURE, events)
        else:
            with FIXTURE.open(newline="", encoding="utf-8") as source:
                rows = [row for row in csv.DictReader(source, delimiter="\t") if row["trial_id"] != "9"]
            with events.open("w", newline="", encoding="utf-8") as target:
                writer = csv.DictWriter(target, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        (bold_dir / f"{stem}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz").write_bytes(b"fake")
        (confound_dir / f"{stem}_desc-TedanaPlusConfounds.tsv").write_text("motion\n0\n", encoding="utf-8")
        ev_dir = self.fsl / "EVfiles" / f"sub-{subject}" / f"ses-{session}" / "ugr" / "model-3"
        generate(events, ev_dir, run, overwrite=False, dry_run=False)
        return events

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_l1_rendering_resolves_all_activation_and_ppi_placeholders(self) -> None:
        self.prepare_run("1", misses=True)
        self.run_script("code/L1stats.sh", "99999", "1", "0", "--session", "01", "--render-only")
        subject_dir = self.fsl / "sub-99999" / "ses-01"
        act_fsf = subject_dir / "L1_sub-99999_task-ugr_ses-01_model-3_type-act_run-1.fsf"
        rendered = act_fsf.read_text(encoding="utf-8")
        self.assertIn("set fmri(shape11) 3", rendered)
        self.assertIn("set fmri(featwatcher_yn) 0", rendered)
        for placeholder in ("OUTPUT", "DATA", "EVDIR", "MISSED_TRIAL", "SHAPE_EV", "CONFOUNDEVS", "NVOLUMES"):
            self.assertNotIn(placeholder, rendered)

        activation = subject_dir / "L1_task-ugr_ses-01_model-3_type-act_run-1_sm-5.feat"
        activation.mkdir(parents=True)
        (activation / "mask.nii.gz").write_bytes(b"fake")
        self.run_script("code/L1stats.sh", "99999", "1", "pTPJ", "--session", "01", "--render-only")
        ppi_fsf = subject_dir / "L1_sub-99999_task-ugr_ses-01_model-3_type-ppi_seed-pTPJ_run-1.fsf"
        ppi = ppi_fsf.read_text(encoding="utf-8")
        self.assertNotIn("PHYS", ppi)
        self.assertIn("ts_task-ugr_ses-01_mask-pTPJ_run-1.txt", ppi)
        self.assertIn("set fmri(convolve11) 3", ppi)
        self.assertIn("set fmri(featwatcher_yn) 0", ppi)

    def test_nppi_rendering_uses_simultaneous_network_regression_and_target_mapping(self) -> None:
        self.prepare_run("1", misses=True)
        subject_dir = self.fsl / "sub-99999" / "ses-01"
        activation = subject_dir / "L1_task-ugr_ses-01_model-3_type-act_run-1_sm-5.feat"
        activation.mkdir(parents=True)
        (activation / "mask.nii.gz").write_bytes(b"fake")

        for network, target, other_indices in (
            ("dmn", 3, (0, 1, 2, 4, 5, 6, 7, 8, 9)),
            ("ecn", 7, (0, 1, 2, 3, 4, 5, 6, 8, 9)),
        ):
            result = self.run_script(
                "code/L1stats.sh", "99999", "1", network, "--session", "01", "--render-only"
            )
            self.assertIn(f"nPPI target: {network} (network {target})", result.stdout)
            rendered_path = (
                subject_dir
                / f"L1_sub-99999_task-ugr_ses-01_model-3_type-nppi-{network}_run-1.fsf"
            )
            rendered = rendered_path.read_text(encoding="utf-8")
            self.assertIn("set fmri(evs_orig) 32", rendered)
            self.assertIn("set fmri(convolve11) 3", rendered)
            self.assertIn("set fmri(shape11) 3", rendered)
            self.assertIn(
                f'set fmri(custom12) "{subject_dir}/ts_task-ugr_ses-01_nppi-{network}_net-{target}_run-1.txt"',
                rendered,
            )
            for ev, index in enumerate(other_indices, start=13):
                self.assertIn(
                    f'set fmri(custom{ev}) "{subject_dir}/ts_task-ugr_ses-01_nppi-{network}_net-{index}_run-1.txt"',
                    rendered,
                )
            for placeholder in ("MAINNET", *(f"OTHERNET{i}" for i in range(1, 10))):
                self.assertNotIn(placeholder, rendered)

            matrix = subject_dir / f"ts_task-ugr_ses-01_nppi-{network}_networks10_run-1.txt"
            rows = [line.split() for line in matrix.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 100)
            self.assertTrue(all(len(row) == 10 for row in rows))
            for index in range(10):
                series = subject_dir / f"ts_task-ugr_ses-01_nppi-{network}_net-{index}_run-1.txt"
                self.assertEqual(len(series.read_text(encoding="utf-8").splitlines()), 100)

    def test_nppi_absent_miss_is_empty_but_retains_task_convolution_setting(self) -> None:
        self.prepare_run("2", misses=False)
        subject_dir = self.fsl / "sub-99999" / "ses-01"
        activation = subject_dir / "L1_task-ugr_ses-01_model-3_type-act_run-2_sm-5.feat"
        activation.mkdir(parents=True)
        (activation / "mask.nii.gz").write_bytes(b"fake")
        self.run_script("code/L1stats.sh", "99999", "2", "dmn", "--session", "01", "--render-only")
        rendered = (
            subject_dir / "L1_sub-99999_task-ugr_ses-01_model-3_type-nppi-dmn_run-2.fsf"
        ).read_text(encoding="utf-8")
        self.assertIn("set fmri(shape11) 10", rendered)
        self.assertIn("set fmri(convolve11) 3", rendered)

    def test_absent_miss_uses_empty_shape_and_no_stale_file(self) -> None:
        self.prepare_run("2", misses=False)
        self.run_script("code/L1stats.sh", "99999", "2", "0", "--session", "01", "--render-only")
        rendered = (
            self.fsl
            / "sub-99999"
            / "ses-01"
            / "L1_sub-99999_task-ugr_ses-01_model-3_type-act_run-2.fsf"
        ).read_text(encoding="utf-8")
        self.assertIn("set fmri(shape11) 10", rendered)
        self.assertFalse(
            (self.fsl / "EVfiles" / "sub-99999" / "ses-01" / "ugr" / "model-3" / "run-2_missed_trial.txt").exists()
        )

    def test_ev_batch_dry_run_validates_without_writing(self) -> None:
        events = self.prepare_run("1", misses=True)
        shutil.rmtree(self.fsl / "EVfiles")
        manifest = self.base / "manifest.tsv"
        manifest.write_text("subject\tsession\trun\n99999\t01\t1\n", encoding="utf-8")

        result = self.run_script(
            "code/run_gen3colfiles.sh",
            "--manifest",
            str(manifest),
            "--jobs",
            "2",
            "--dry-run",
        )

        self.assertIn("Model-3 EVs would-write", result.stdout)
        self.assertFalse(self.fsl.joinpath("EVfiles").exists())
        self.assertTrue(events.is_file())

    def test_l1_names_are_exactly_the_l2_inputs(self) -> None:
        subject_dir = self.fsl / "sub-99999" / "ses-01"
        expected = []
        for run in ("1", "2"):
            feat = subject_dir / f"L1_task-ugr_ses-01_model-3_type-act_run-{run}_sm-5.feat"
            feat.mkdir(parents=True)
            (feat / "cluster_mask_zstat1.nii.gz").write_bytes(b"fake")
            expected.append(feat)
        result = self.run_script("code/L2stats.sh", "99999", "act", "--session", "01", "--render-only")
        self.assertIn("FSLSUB_PARALLEL: 1", result.stdout)
        rendered = (
            subject_dir / "L2_sub-99999_task-ugr_ses-01_model-3_type-act.fsf"
        ).read_text(encoding="utf-8")
        self.assertIn(f'set feat_files(1) "{expected[0]}"', rendered)
        self.assertIn(f'set feat_files(2) "{expected[1]}"', rendered)
        self.assertNotIn("INPUT1", rendered)
        self.assertNotIn("INPUT2", rendered)

    def test_network_ppi_names_are_exactly_the_l2_inputs(self) -> None:
        subject_dir = self.fsl / "sub-99999" / "ses-01"
        expected = []
        for run in ("1", "2"):
            feat = subject_dir / f"L1_task-ugr_ses-01_model-3_type-nppi-dmn_run-{run}_sm-5.feat"
            feat.mkdir(parents=True)
            (feat / "cluster_mask_zstat1.nii.gz").write_bytes(b"fake")
            expected.append(feat)
        result = self.run_script("code/L2stats.sh", "99999", "nppi-dmn", "--session", "01", "--render-only")
        self.assertIn("fixed effects", result.stdout)
        rendered = (
            subject_dir / "L2_sub-99999_task-ugr_ses-01_model-3_type-nppi-dmn.fsf"
        ).read_text(encoding="utf-8")
        self.assertIn(f'set feat_files(1) "{expected[0]}"', rendered)
        self.assertIn(f'set feat_files(2) "{expected[1]}"', rendered)

    def test_l2_rejects_partial_existing_output_even_with_final_cope_marker(self) -> None:
        subject_dir = self.fsl / "sub-99999" / "ses-01"
        for run in ("1", "2"):
            feat = subject_dir / f"L1_task-ugr_ses-01_model-3_type-act_run-{run}_sm-5.feat"
            feat.mkdir(parents=True)
            (feat / "cluster_mask_zstat1.nii.gz").write_bytes(b"fake")

        partial = subject_dir / "L2_task-ugr_ses-01_model-3_type-act_sm-5.gfeat"
        final_cope = partial / "cope17.feat"
        final_cope.mkdir(parents=True)
        (final_cope / "cluster_mask_zstat1.nii.gz").write_bytes(b"fake")

        result = subprocess.run(
            ["bash", "code/L2stats.sh", "99999", "act", "--session", "01", "--render-only"],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("incomplete output exists", result.stderr)

    def test_l2_waits_for_asynchronously_completed_feat_output(self) -> None:
        subject_dir = self.fsl / "sub-99999" / "ses-01"
        for run in ("1", "2"):
            feat = subject_dir / f"L1_task-ugr_ses-01_model-3_type-act_run-{run}_sm-5.feat"
            feat.mkdir(parents=True)
            (feat / "cluster_mask_zstat1.nii.gz").write_bytes(b"fake")

        fake_feat = self.bin / "feat"
        fake_feat.write_text(
            "#!/usr/bin/env bash\n"
            "output=$(awk -F '\"' '/^set fmri\\(outputdir\\)/ { print $2; exit }' \"$1\")\n"
            "(\n"
            "  sleep 1\n"
            "  gfeat=\"${output}.gfeat\"\n"
            "  mkdir -p \"$gfeat\"\n"
            "  printf fake > \"$gfeat/design.mat\"\n"
            "  printf fake > \"$gfeat/design.con\"\n"
            "  for cope in $(seq 17); do\n"
            "    cope_dir=\"$gfeat/cope${cope}.feat\"\n"
            "    mkdir -p \"$cope_dir/stats\"\n"
            "    for relative in design.mat design.con mask.nii.gz stats/cope1.nii.gz "
            "stats/zstat1.nii.gz cluster_mask_zstat1.nii.gz; do\n"
            "      printf fake > \"$cope_dir/$relative\"\n"
            "    done\n"
            "  done\n"
            ") >/dev/null 2>&1 &\n",
            encoding="utf-8",
        )
        fake_feat.chmod(0o755)
        env = self.env.copy()
        env["L2_COMPLETION_TIMEOUT_SECONDS"] = "5"
        env["L2_COMPLETION_POLL_SECONDS"] = "1"

        result = subprocess.run(
            ["bash", "code/L2stats.sh", "99999", "act", "--session", "01"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("Waiting for internally submitted FEAT jobs", result.stdout)
        self.assertIn("L2 output complete after", result.stdout)


if __name__ == "__main__":
    unittest.main()
