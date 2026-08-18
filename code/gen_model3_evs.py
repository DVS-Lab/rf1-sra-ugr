#!/usr/bin/env python3
"""Generate authoritative UGR model-3 FSL EVs from canonical BIDS events."""

from __future__ import annotations

import argparse
import csv
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Iterable


REQUIRED_COLUMNS = {
    "onset",
    "duration",
    "trial_type",
    "response_time",
    "trial_id",
    "phase",
    "sociality",
    "endowment",
    "offer",
    "decision",
    "response",
    "left_option",
    "right_option",
}
TRIAL_METADATA = (
    "sociality",
    "endowment",
    "offer",
    "decision",
    "response",
    "left_option",
    "right_option",
)
CONDITIONS = (
    ("nonsocial", 32, "nonsocial_high"),
    ("nonsocial", 16, "nonsocial_low"),
    ("social", 32, "social_high"),
    ("social", 16, "social_low"),
)
TIME_TOLERANCE = 1e-5


class Model3Error(ValueError):
    """Raised when canonical events cannot safely define model 3."""


@dataclass(frozen=True)
class Trial:
    trial_id: str
    sociality: str
    endowment: int
    offer: float | None
    missed: bool
    broad_onset: float
    broad_duration: float
    response_onset: float | None
    response_time: float | None


def _text(value: object) -> str:
    return str(value).strip()


def _missing(value: object) -> bool:
    return _text(value).lower() in {"", "n/a", "na", "nan"}


def _number(value: object, label: str) -> float:
    if _missing(value):
        raise Model3Error(f"missing numeric {label}")
    try:
        result = float(_text(value))
    except ValueError as exc:
        raise Model3Error(f"non-numeric {label}: {value!r}") from exc
    if not math.isfinite(result):
        raise Model3Error(f"non-finite {label}: {value!r}")
    return result


def _integer(value: object, label: str) -> int:
    result = _number(value, label)
    if not result.is_integer():
        raise Model3Error(f"non-integer {label}: {value!r}")
    return int(result)


def _metadata_value(field: str, value: object) -> object:
    if field in {"endowment", "response", "left_option", "right_option"}:
        return None if _missing(value) else _integer(value, field)
    if field == "offer":
        return None if _missing(value) else _number(value, field)
    return _text(value).lower()


def read_events(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fields = set(reader.fieldnames or ())
            missing = sorted(REQUIRED_COLUMNS - fields)
            if missing:
                raise Model3Error(f"missing required BIDS column(s): {', '.join(missing)}")
            rows = list(reader)
    except OSError as exc:
        raise Model3Error(f"cannot read events file {path}: {exc}") from exc
    if not rows:
        raise Model3Error("events file contains no rows")
    return rows


def _one(rows: list[dict[str, str]], trial_type: str, trial_id: str) -> dict[str, str]:
    matches = [row for row in rows if _text(row["trial_type"]).lower() == trial_type]
    if len(matches) != 1:
        raise Model3Error(
            f"trial {trial_id}: expected exactly one {trial_type} row, found {len(matches)}"
        )
    return matches[0]


def _bounds(row: dict[str, str], trial_id: str) -> tuple[float, float]:
    onset = _number(row["onset"], f"trial {trial_id} onset")
    duration = _number(row["duration"], f"trial {trial_id} duration")
    if onset < 0 or duration < 0:
        raise Model3Error(f"trial {trial_id}: onset and duration must be nonnegative")
    return onset, onset + duration


def collapse_trials(rows: Iterable[dict[str, str]]) -> list[Trial]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for index, row in enumerate(rows, start=2):
        trial_id = _text(row.get("trial_id", ""))
        if _missing(trial_id):
            raise Model3Error(f"events row {index}: missing trial_id")
        _bounds(row, trial_id)
        grouped.setdefault(trial_id, []).append(row)

    trials: list[Trial] = []
    for trial_id, trial_rows in grouped.items():
        for field in TRIAL_METADATA:
            values = {_metadata_value(field, row[field]) for row in trial_rows}
            if len(values) != 1:
                raise Model3Error(
                    f"trial {trial_id}: contradictory {field} values across phase rows: {values}"
                )

        sociality = _text(trial_rows[0]["sociality"]).lower()
        if sociality not in {"social", "nonsocial"}:
            raise Model3Error(f"trial {trial_id}: unknown sociality {sociality!r}")
        endowment = _integer(trial_rows[0]["endowment"], f"trial {trial_id} endowment")
        if endowment not in {16, 32}:
            raise Model3Error(f"trial {trial_id}: unexpected endowment {endowment}; expected 16 or 32")

        partner = _one(trial_rows, "partner_cue", trial_id)
        if _text(partner["phase"]).lower() != "partner_cue":
            raise Model3Error(f"trial {trial_id}: partner_cue row has inconsistent phase")
        endowment_row = _one(trial_rows, "endowment", trial_id)
        partner_onset, partner_end = _bounds(partner, trial_id)
        endowment_onset, endowment_end = _bounds(endowment_row, trial_id)

        missed_rows = [
            row for row in trial_rows if _text(row["trial_type"]).lower() == "missed_decision"
        ]
        choice_rows = [
            row for row in trial_rows if _text(row["trial_type"]).lower() == "choice_feedback"
        ]
        if bool(missed_rows) == bool(choice_rows):
            raise Model3Error(
                f"trial {trial_id}: must contain either missed_decision or choice_feedback, not both/neither"
            )

        if missed_rows:
            if len(missed_rows) != 1:
                raise Model3Error(f"trial {trial_id}: duplicate missed_decision rows")
            allowed = {"partner_cue", "endowment", "missed_decision", "missed_feedback"}
            unexpected = sorted({_text(row["trial_type"]).lower() for row in trial_rows} - allowed)
            if unexpected:
                raise Model3Error(f"trial {trial_id}: unexpected missed-trial phase(s): {unexpected}")
            missed_onset, missed_end = _bounds(missed_rows[0], trial_id)
            if not (
                partner_onset <= partner_end
                and partner_end <= endowment_onset + TIME_TOLERANCE
                and endowment_onset <= endowment_end
                and endowment_end <= missed_onset + TIME_TOLERANCE
                and missed_onset < missed_end
            ):
                raise Model3Error(f"trial {trial_id}: temporally inconsistent missed-trial phases")
            trials.append(
                Trial(
                    trial_id=trial_id,
                    sociality=sociality,
                    endowment=endowment,
                    offer=None,
                    missed=True,
                    broad_onset=partner_onset,
                    broad_duration=missed_end - partner_onset,
                    response_onset=None,
                    response_time=None,
                )
            )
            continue

        allowed = {"partner_cue", "endowment", "decision", "choice_feedback"}
        unexpected = sorted({_text(row["trial_type"]).lower() for row in trial_rows} - allowed)
        if unexpected:
            raise Model3Error(f"trial {trial_id}: unexpected responded-trial phase(s): {unexpected}")
        decision = _one(trial_rows, "decision", trial_id)
        choice = _one(trial_rows, "choice_feedback", trial_id)
        decision_onset, decision_end = _bounds(decision, trial_id)
        choice_onset, choice_end = _bounds(choice, trial_id)
        if not (
            partner_onset <= partner_end
            and partner_end <= endowment_onset + TIME_TOLERANCE
            and endowment_onset <= endowment_end
            and endowment_end <= decision_onset + TIME_TOLERANCE
            and decision_onset <= choice_onset + TIME_TOLERANCE
            and choice_onset < choice_end
        ):
            raise Model3Error(f"trial {trial_id}: temporally inconsistent responded-trial phases")
        rt_decision = _number(decision["response_time"], f"trial {trial_id} decision response_time")
        rt_choice = _number(choice["response_time"], f"trial {trial_id} choice_feedback response_time")
        if not math.isclose(rt_decision, rt_choice, rel_tol=0, abs_tol=TIME_TOLERANCE):
            raise Model3Error(f"trial {trial_id}: contradictory response_time across response phases")
        if not math.isclose(
            decision_end - decision_onset,
            rt_decision,
            rel_tol=0,
            abs_tol=TIME_TOLERANCE,
        ):
            raise Model3Error(f"trial {trial_id}: decision duration disagrees with response_time")
        offer = _number(trial_rows[0]["offer"], f"trial {trial_id} offer")
        trials.append(
            Trial(
                trial_id=trial_id,
                sociality=sociality,
                endowment=endowment,
                offer=offer,
                missed=False,
                broad_onset=partner_onset,
                broad_duration=choice_end - partner_onset,
                response_onset=choice_onset,
                response_time=rt_choice,
            )
        )

    return sorted(trials, key=lambda trial: trial.broad_onset)


def build_ev_rows(trials: list[Trial]) -> tuple[dict[str, list[tuple[float, float, float]]], list[str]]:
    valid = [trial for trial in trials if not trial.missed]
    if not valid:
        raise Model3Error("run has no valid responded trials")
    outputs: dict[str, list[tuple[float, float, float]]] = {}
    warnings: list[str] = []
    for sociality, endowment, label in CONDITIONS:
        members = [
            trial
            for trial in valid
            if trial.sociality == sociality and trial.endowment == endowment
        ]
        if not members:
            raise Model3Error(f"run is not estimable: required condition {label} has no valid trials")
        offers = [trial.offer for trial in members]
        assert all(value is not None for value in offers)
        offer_values = [float(value) for value in offers if value is not None]
        mean_offer = fmean(offer_values)
        demeaned = [value - mean_offer for value in offer_values]
        if all(math.isclose(value, 0.0, rel_tol=0, abs_tol=1e-12) for value in demeaned):
            warnings.append(f"ZERO-VARIANCE PMOD: {label} offer is constant within this run")
        outputs[f"{label}_constant"] = [
            (trial.broad_onset, trial.broad_duration, 1.0) for trial in members
        ]
        outputs[f"{label}_pmod"] = [
            (trial.broad_onset, trial.broad_duration, amplitude)
            for trial, amplitude in zip(members, demeaned)
        ]

    rt_mean = fmean(float(trial.response_time) for trial in valid if trial.response_time is not None)
    outputs["rt_constant"] = [
        (float(trial.response_onset), 0.0, 1.0)
        for trial in valid
        if trial.response_onset is not None
    ]
    outputs["rt_pmod"] = [
        (float(trial.response_onset), 0.0, float(trial.response_time) - rt_mean)
        for trial in valid
        if trial.response_onset is not None and trial.response_time is not None
    ]
    missed = [trial for trial in trials if trial.missed]
    if missed:
        outputs["missed_trial"] = [
            (trial.broad_onset, trial.broad_duration, 1.0) for trial in missed
        ]
    return outputs, warnings


def _format_rows(rows: list[tuple[float, float, float]]) -> str:
    rows = sorted(rows, key=lambda row: row[0])
    return "".join(f"{onset:.6f}\t{duration:.6f}\t{amplitude:.6f}\n" for onset, duration, amplitude in rows)


def write_outputs(
    outputs: dict[str, list[tuple[float, float, float]]],
    output_dir: Path,
    run: str,
    *,
    overwrite: bool,
    dry_run: bool,
) -> str:
    expected = {f"run-{run}_{name}.txt": _format_rows(rows) for name, rows in outputs.items()}
    existing = sorted(output_dir.glob(f"run-{run}_*.txt")) if output_dir.exists() else []
    existing_names = {path.name for path in existing}
    expected_names = set(expected)
    identical = existing_names == expected_names and all(
        (output_dir / name).read_text(encoding="utf-8") == content
        for name, content in expected.items()
    )
    if identical:
        return "unchanged"
    if existing and not overwrite:
        raise Model3Error(
            f"run-{run} EVs already exist but differ from the canonical events; use --overwrite"
        )
    if dry_run:
        return "would-write"

    output_dir.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".run-{run}-model3-", dir=output_dir))
    try:
        for name, content in expected.items():
            (stage / name).write_text(content, encoding="utf-8")
        for old in existing:
            old.unlink()
        for name in sorted(expected):
            os.replace(stage / name, output_dir / name)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return "written"


def generate(events: Path, output_dir: Path, run: str, *, overwrite: bool, dry_run: bool) -> tuple[list[Trial], list[str], str]:
    trials = collapse_trials(read_events(events))
    outputs, warnings = build_ev_rows(trials)
    result = write_outputs(outputs, output_dir, run, overwrite=overwrite, dry_run=dry_run)
    return trials, warnings, result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        trials, warnings, result = generate(
            args.events,
            args.output_dir,
            str(args.run),
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    except Model3Error as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    valid = sum(not trial.missed for trial in trials)
    missed = sum(trial.missed for trial in trials)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    print(
        f"Model-3 EVs {result}: {args.events} -> {args.output_dir} "
        f"(run {args.run}; {valid} valid, {missed} missed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
