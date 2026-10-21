from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from build_L1_manifest import build_manifest, paths_for
from build_L2_manifest import l1_path, normalize_type


class ManifestTests(unittest.TestCase):
    def test_l1_discovers_visible_runs_and_reports_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bids = base / "bids"
            fmriprep = base / "fmriprep"
            confounds = base / "confounds"
            for run in ("1", "2"):
                events, bold, confound = paths_for("10001", "01", run, bids, fmriprep, confounds)
                events.parent.mkdir(parents=True, exist_ok=True)
                events.write_text("onset\n", encoding="utf-8")
                if run == "1":
                    bold.parent.mkdir(parents=True, exist_ok=True)
                    bold.write_bytes(b"bold")
                    confound.parent.mkdir(parents=True, exist_ok=True)
                    confound.write_text("motion\n", encoding="utf-8")
            ready, missing = build_manifest(["10001"], ["01"], bids, fmriprep, confounds)
            self.assertEqual(ready, [("10001", "01", "1")])
            self.assertEqual(missing, [("10001", "01", "2", "BOLD,confounds")])

    def test_l2_path_matches_central_contract(self) -> None:
        root = Path("/analysis/derivatives/fsl")
        self.assertEqual(
            l1_path(root, "10001", "02", "2", "ppi_seed-pTPJ"),
            root
            / "sub-10001"
            / "ses-02"
            / "L1_task-ugr_ses-02_model-3_type-ppi_seed-pTPJ_run-2_sm-5.feat",
        )
        self.assertEqual(normalize_type("nppi-dmn"), "nppi-dmn")

    def test_expected_runs_exist_in_inventory_without_events_or_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ready, missing = build_manifest(["10001"], ["01", "02"], base / "bids", base / "fmriprep", base / "confounds")
            self.assertEqual(ready, [])
            self.assertEqual([(r[1], r[2]) for r in missing], [("01", "1"), ("01", "2"), ("02", "1"), ("02", "2")])
            self.assertTrue(all(r[3] == "events,BOLD,confounds" for r in missing))

    def test_roster_and_exclusions_gate_even_with_residual_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bids, preproc, confounds, excluded = [base / s for s in ("bids", "preproc", "confounds", "excluded")]
            bids.mkdir()
            excluded.mkdir()
            (excluded / "Smith-SRA-10002").mkdir()
            (bids / "participants.tsv").write_text("participant_id\nsub-10001\nsub-10002\n")
            for subject in ("10001", "10002", "10003"):
                for path in paths_for(subject, "01", "1", bids, preproc, confounds):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("present\n")
            command = [sys.executable, str(ROOT / "code/build_L1_manifest.py"),
                       "--bids-root", str(bids), "--fmriprep-root", str(preproc),
                       "--confounds-root", str(confounds), "--source-exclusions-root", str(excluded),
                       "--output", str(base / "ready.tsv"), "--missing-output", str(base / "missing.tsv")]
            proc = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual((base / "ready.tsv").read_text(), "subject\tsession\trun\n10001\t01\t1\n")
            self.assertIn("10001\t01\t2\tevents,BOLD,confounds", (base / "missing.tsv").read_text())
            before = (base / "ready.tsv").read_bytes()
            command[command.index("--source-exclusions-root") + 1] = str(base / "unavailable")
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((base / "ready.tsv").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
