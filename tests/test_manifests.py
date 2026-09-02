from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()
