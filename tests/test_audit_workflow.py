from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from audit_workflow import REQUIRED_EVS, Unit, l1_dir


class WorkflowAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.bids = self.base / "bids"
        self.fmriprep = self.base / "fmriprep"
        self.confounds = self.base / "confounds"
        self.fsl = self.base / "fsl"
        self.output = self.base / "audit"

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def touch(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")

    def prepare_inputs(self, unit: Unit, *, events: bool = True, confounds: bool = True) -> None:
        stem = f"sub-{unit.subject}_ses-{unit.session}_task-ugr_run-{unit.run}"
        if events:
            self.touch(
                self.bids
                / f"sub-{unit.subject}"
                / f"ses-{unit.session}"
                / "func"
                / f"{stem}_events.tsv"
            )
        self.touch(
            self.fmriprep
            / f"sub-{unit.subject}"
            / f"ses-{unit.session}"
            / "func"
            / f"{stem}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz"
        )
        if confounds:
            self.touch(
                self.confounds
                / f"sub-{unit.subject}"
                / f"{stem}_desc-TedanaPlusConfounds.tsv"
            )

    def prepare_evs(self, unit: Unit) -> None:
        prefix = (
            self.fsl
            / "EVfiles"
            / f"sub-{unit.subject}"
            / f"ses-{unit.session}"
            / "ugr"
            / "model-3"
            / f"run-{unit.run}"
        )
        for name in REQUIRED_EVS:
            self.touch(Path(f"{prefix}_{name}.txt"))

    def prepare_l1(self, unit: Unit, analysis_type: str, ncopes: int) -> None:
        feat = l1_dir(self.fsl, unit, analysis_type)
        for relative in ("design.mat", "design.con", "mask.nii.gz", "cluster_mask_zstat1.nii.gz"):
            self.touch(feat / relative)
        for cope in range(1, ncopes + 1):
            self.touch(feat / "stats" / f"cope{cope}.nii.gz")
            self.touch(feat / "stats" / f"zstat{cope}.nii.gz")

    @staticmethod
    def read_tsv(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_audit_discovers_union_and_writes_actionable_manifests(self) -> None:
        run1 = Unit("10001", "01", "1")
        run2 = Unit("10001", "01", "2")
        for unit in (run1, run2):
            self.prepare_inputs(unit)
            self.prepare_evs(unit)
            self.prepare_l1(unit, "act", 17)
        self.prepare_l1(run1, "ppi_seed-dACC", 18)

        # A BOLD-only unit must not disappear merely because canonical events
        # or confounds are missing.
        bold_only = Unit("10002", "02", "1")
        self.prepare_inputs(bold_only, events=False, confounds=False)

        result = subprocess.run(
            [
                sys.executable,
                "code/audit_workflow.py",
                "--bids-root",
                str(self.bids),
                "--fmriprep-root",
                str(self.fmriprep),
                "--confounds-root",
                str(self.confounds),
                "--fsl-root",
                str(self.fsl),
                "--sessions",
                "all",
                "--seed",
                "dACC",
                "--output-dir",
                str(self.output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("Visible UGR units: 3", result.stdout)
        self.assertIn(f"BIDS root: {self.bids.resolve()}", result.stdout)
        self.assertIn(f"fMRIPrep root: {self.fmriprep.resolve()}", result.stdout)
        self.assertIn(f"Confounds root: {self.confounds.resolve()}", result.stdout)
        self.assertIn(f"FSL derivatives root: {self.fsl.resolve()}", result.stdout)
        self.assertIn("Input-ready units: 2", result.stdout)
        self.assertIn("Input-missing units: 1", result.stdout)
        self.assertIn("EV todo: 0", result.stdout)
        self.assertIn("L1 activation todo: 0", result.stdout)
        self.assertIn("L1 activation blocked by EVs: 0", result.stdout)
        self.assertIn("L1 ppi_seed-dACC todo: 1", result.stdout)
        self.assertIn("L1 ppi_seed-dACC blocked by EVs/activation: 0", result.stdout)
        self.assertIn("L2 activation complete/eligible: 0/1", result.stdout)
        self.assertIn("L2 activation todo: 1", result.stdout)
        self.assertIn("L2 activation blocked by L1: 0", result.stdout)
        self.assertIn("L2 ppi_seed-dACC complete/eligible: 0/0", result.stdout)
        self.assertIn("L2 ppi_seed-dACC blocked by L1: 1", result.stdout)

        missing = self.read_tsv(self.output / "L1-input-missing.tsv")
        self.assertEqual(missing[0]["missing"], "events,confounds")
        ppi_todo = self.read_tsv(self.output / "L1-ppi_seed-dACC-todo.tsv")
        self.assertEqual(ppi_todo, [{"subject": "10001", "session": "01", "run": "2"}])
        l2_todo = self.read_tsv(self.output / "L2-act-todo.tsv")
        self.assertEqual(l2_todo, [{"subject": "10001", "session": "01"}])

    def test_audit_accepts_network_ppi_family(self) -> None:
        unit = Unit("10001", "01", "1")
        self.prepare_inputs(unit)
        self.prepare_evs(unit)
        self.prepare_l1(unit, "act", 17)
        output = self.base / "audit-nppi"
        result = subprocess.run(
            [
                sys.executable,
                "code/audit_workflow.py",
                "--bids-root",
                str(self.bids),
                "--fmriprep-root",
                str(self.fmriprep),
                "--confounds-root",
                str(self.confounds),
                "--fsl-root",
                str(self.fsl),
                "--ppi-type",
                "nppi-dmn",
                "--output-dir",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("L1 nppi-dmn todo: 1", result.stdout)
        self.assertEqual(
            self.read_tsv(output / "L1-nppi-dmn-todo.tsv"),
            [{"subject": "10001", "session": "01", "run": "1"}],
        )

    def test_audit_warns_when_ready_inputs_have_no_local_derivatives(self) -> None:
        unit = Unit("10001", "01", "1")
        self.prepare_inputs(unit)
        output = self.base / "audit-empty-derivatives"
        result = subprocess.run(
            [
                sys.executable,
                "code/audit_workflow.py",
                "--bids-root",
                str(self.bids),
                "--fmriprep-root",
                str(self.fmriprep),
                "--confounds-root",
                str(self.confounds),
                "--fsl-root",
                str(self.fsl),
                "--output-dir",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn(f"FSL derivatives root: {self.fsl.resolve()}", result.stdout)
        self.assertIn(
            "WARNING: no EV outputs were found for any input-ready unit; verify the FSL derivatives root.",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
