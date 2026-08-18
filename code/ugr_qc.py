#!/usr/bin/env python3
"""Summarize canonical UGR trial counts without imposing hidden exclusions."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

from gen_model3_evs import Model3Error, collapse_trials, read_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    upstream = Path(os.environ.get("RF1_SRA_UPSTREAM_ROOT", "/ZPOOL/data/projects/rf1-sra-linux2"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--bids-root", type=Path, default=Path(os.environ.get("BIDS_ROOT", upstream / "bids")))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--min-valid",
        type=int,
        help="Optional explicit manuscript-specific valid-trial threshold (historically 36/48)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_rows: list[dict[str, object]] = []
    failures = 0
    with args.manifest.open(newline="", encoding="utf-8") as handle:
        for unit in csv.DictReader(handle, delimiter="\t"):
            subject = unit["subject"].removeprefix("sub-")
            session = unit["session"].removeprefix("ses-")
            run = unit["run"]
            stem = f"sub-{subject}_ses-{session}_task-ugr_run-{run}"
            events = args.bids_root / f"sub-{subject}" / f"ses-{session}" / "func" / f"{stem}_events.tsv"
            try:
                trials = collapse_trials(read_events(events))
            except Model3Error as exc:
                print(f"ERROR: {stem}: {exc}", file=sys.stderr)
                failures += 1
                continue
            valid = [trial for trial in trials if not trial.missed]
            row: dict[str, object] = {
                "subject": subject,
                "session": session,
                "run": run,
                "n_trials": len(trials),
                "n_valid": len(valid),
                "n_missed": len(trials) - len(valid),
                "valid_proportion": f"{len(valid) / len(trials):.6f}",
            }
            for sociality, endowment, label in (
                ("nonsocial", 32, "nonsocial_high"),
                ("nonsocial", 16, "nonsocial_low"),
                ("social", 32, "social_high"),
                ("social", 16, "social_low"),
            ):
                row[f"n_{label}"] = sum(
                    trial.sociality == sociality and trial.endowment == endowment for trial in valid
                )
            if args.min_valid is not None:
                row["passes_min_valid"] = int(len(valid) >= args.min_valid)
            output_rows.append(row)
    if not output_rows:
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"QC rows written: {len(output_rows)}")
    print(f"QC report: {args.output.resolve()}")
    if args.min_valid is not None:
        passed = sum(int(row["passes_min_valid"]) for row in output_rows)
        print(f"Runs meeting explicit min-valid {args.min_valid}: {passed}/{len(output_rows)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
