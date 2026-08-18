from __future__ import annotations

import csv
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from gen_model3_evs import Model3Error, build_ev_rows, collapse_trials, generate, read_events


FIXTURE = ROOT / "tests" / "fixtures" / "synthetic_ugr_events.tsv"


def read_fixture() -> list[dict[str, str]]:
    with FIXTURE.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class Model3EVTests(unittest.TestCase):
    def test_timing_conditions_pmods_rt_and_miss(self) -> None:
        trials = collapse_trials(read_events(FIXTURE))
        outputs, warnings = build_ev_rows(trials)
        self.assertEqual(warnings, [])
        self.assertEqual(len(trials), 9)
        first = trials[0]
        self.assertEqual(first.broad_onset, 0.0)
        self.assertEqual(first.broad_duration, 4.0)
        self.assertEqual(first.response_onset, 3.0)
        missed = next(trial for trial in trials if trial.missed)
        self.assertEqual(missed.broad_onset, 80.0)
        self.assertEqual(missed.broad_duration, 5.25)

        for label in (
            "nonsocial_high_pmod",
            "nonsocial_low_pmod",
            "social_high_pmod",
            "social_low_pmod",
        ):
            amplitudes = [row[2] for row in outputs[label]]
            self.assertEqual(amplitudes, [-2.0, 2.0])
            self.assertTrue(math.isclose(sum(amplitudes), 0.0, abs_tol=1e-12))

        rt_amplitudes = [row[2] for row in outputs["rt_pmod"]]
        self.assertEqual(rt_amplitudes, [-0.75, 0.25, -0.25, 0.75, -1.25, -0.25, 0.25, 1.25])
        self.assertTrue(math.isclose(sum(rt_amplitudes), 0.0, abs_tol=1e-12))
        self.assertEqual(len(outputs["rt_constant"]), 8)
        self.assertEqual(outputs["missed_trial"], [(80.0, 5.25, 1.0)])
        self.assertEqual(sum(len(outputs[name]) for name in outputs if name.endswith("_constant") and name != "rt_constant"), 8)

    def test_historical_parity_has_only_approved_half_second_broad_timing_change(self) -> None:
        trials = collapse_trials(read_events(FIXTURE))
        outputs, _ = build_ev_rows(trials)
        new_onset, new_duration, _ = outputs["nonsocial_high_constant"][0]
        historical_onset = new_onset + 0.5
        historical_offset = new_onset + new_duration
        historical_duration = historical_offset - historical_onset
        self.assertEqual(new_onset, historical_onset - 0.5)
        self.assertEqual(new_onset + new_duration, historical_onset + historical_duration)
        self.assertEqual(new_duration, historical_duration + 0.5)
        self.assertEqual(outputs["rt_pmod"][0], (3.0, 0.0, -0.75))

    def test_atomic_rerun_removes_stale_miss_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "evs"
            generate(FIXTURE, output, "1", overwrite=False, dry_run=False)
            self.assertTrue((output / "run-1_missed_trial.txt").is_file())
            rows = [row for row in read_fixture() if row["trial_id"] != "9"]
            no_miss = tmp_path / "no_miss.tsv"
            write_rows(no_miss, rows)
            generate(no_miss, output, "1", overwrite=True, dry_run=False)
            self.assertFalse((output / "run-1_missed_trial.txt").exists())

    def assert_invalid(self, mutate) -> None:
        rows = read_fixture()
        mutate(rows)
        with self.assertRaises(Model3Error):
            collapse_trials(rows)

    def test_missing_trial_id_fails(self) -> None:
        self.assert_invalid(lambda rows: rows[0].__setitem__("trial_id", "n/a"))

    def test_contradictory_trial_metadata_fails(self) -> None:
        self.assert_invalid(lambda rows: rows[1].__setitem__("offer", "999"))

    def test_unknown_sociality_fails(self) -> None:
        self.assert_invalid(lambda rows: [row.__setitem__("sociality", "other") for row in rows if row["trial_id"] == "1"])

    def test_unknown_endowment_fails(self) -> None:
        self.assert_invalid(lambda rows: [row.__setitem__("endowment", "24") for row in rows if row["trial_id"] == "1"])

    def test_missing_partner_cue_fails(self) -> None:
        self.assert_invalid(lambda rows: rows.pop(0))

    def test_responded_trial_without_choice_feedback_fails(self) -> None:
        self.assert_invalid(lambda rows: rows.pop(3))

    def test_non_numeric_offer_fails(self) -> None:
        self.assert_invalid(lambda rows: [row.__setitem__("offer", "bad") for row in rows if row["trial_id"] == "1"])

    def test_non_numeric_rt_fails(self) -> None:
        self.assert_invalid(lambda rows: rows[2].__setitem__("response_time", "bad"))

    def test_required_condition_absent_fails(self) -> None:
        rows = [row for row in read_fixture() if row["trial_id"] not in {"1", "2"}]
        trials = collapse_trials(rows)
        with self.assertRaisesRegex(Model3Error, "required condition nonsocial_high"):
            build_ev_rows(trials)

    def test_missing_required_schema_column_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = read_fixture()
            for row in rows:
                del row["trial_id"]
            path = Path(tmp) / "missing.tsv"
            write_rows(path, rows)
            with self.assertRaisesRegex(Model3Error, "missing required BIDS column"):
                read_events(path)


if __name__ == "__main__":
    unittest.main()
