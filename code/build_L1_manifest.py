#!/usr/bin/env python3
"""Inventory expected UGR inputs, not QC or final analysis eligibility."""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path


def read_sublist(path: Path) -> list[str]:
    subjects: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.split("#", 1)[0].strip()
        if value:
            subjects.append(value.removeprefix("sub-"))
    return sorted(dict.fromkeys(subjects))


def discover_subjects(bids_root: Path) -> list[str]:
    with (bids_root / "participants.tsv").open(newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        subjects = [row["participant_id"].removeprefix("sub-") for row in rows]
    if not subjects or len(set(subjects)) != len(subjects) or any(not re.fullmatch(r"\d{5}", s) for s in subjects):
        raise ValueError("invalid or duplicate MRI roster IDs")
    return sorted(subjects)


def paths_for(
    subject: str,
    session: str,
    run: str,
    bids_root: Path,
    fmriprep_root: Path,
    confounds_root: Path,
) -> tuple[Path, Path, Path]:
    stem = f"sub-{subject}_ses-{session}_task-ugr_run-{run}"
    events = bids_root / f"sub-{subject}" / f"ses-{session}" / "func" / f"{stem}_events.tsv"
    bold = (
        fmriprep_root
        / f"sub-{subject}"
        / f"ses-{session}"
        / "func"
        / f"{stem}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz"
    )
    confounds = confounds_root / f"sub-{subject}" / f"{stem}_desc-TedanaPlusConfounds.tsv"
    return events, bold, confounds


def build_manifest(
    subjects: list[str],
    sessions: list[str],
    bids_root: Path,
    fmriprep_root: Path,
    confounds_root: Path,
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str, str]]]:
    ready: list[tuple[str, str, str]] = []
    missing: list[tuple[str, str, str, str]] = []
    for subject in subjects:
        for session in sessions:
            # Enumerate expectations even when no events or session directory exists.
            for run in ("1", "2"):
                events, bold, confounds = paths_for(
                    subject, session, run, bids_root, fmriprep_root, confounds_root
                )
                absent = [
                    label
                    for label, path in (("events", events), ("BOLD", bold), ("confounds", confounds))
                    if not path.is_file() or path.stat().st_size == 0
                ]
                if absent:
                    missing.append((subject, session, run, ",".join(absent)))
                else:
                    ready.append((subject, session, run))
    return ready, missing


def write_tsv(path: Path, header: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    upstream = Path(os.environ.get("RF1_SRA_UPSTREAM_ROOT", "/ZPOOL/data/projects/rf1-sra-linux2"))
    parser.add_argument("--bids-root", type=Path, default=Path(os.environ.get("BIDS_ROOT", upstream / "bids")))
    parser.add_argument(
        "--fmriprep-root",
        type=Path,
        default=Path(os.environ.get("FMRIPREP_ROOT", upstream / "derivatives" / "fmriprep")),
    )
    parser.add_argument(
        "--confounds-root",
        type=Path,
        default=Path(
            os.environ.get("CONFOUNDS_ROOT", upstream / "derivatives" / "fsl" / "confounds_tedana")
        ),
    )
    parser.add_argument("--sublist", type=Path)
    parser.add_argument("--source-exclusions-root", type=Path, default=Path(os.environ.get(
        "SOURCEDATA_EXCLUSIONS_ROOT", "/ZPOOL/data/sourcedata/sourcedata/rf1-sra-exclusions")))
    parser.add_argument("--sessions", default="01")
    parser.add_argument("--output", type=Path, default=root / "logs" / "runlists" / "L1-ready.tsv")
    parser.add_argument(
        "--missing-output", type=Path, default=root / "logs" / "runlists" / "L1-missing.tsv"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sessions = [value.removeprefix("ses-").strip() for value in args.sessions.split(",") if value.strip()]
    if not sessions or len(set(sessions)) != len(sessions) or any(not re.fullmatch(r"\d{2}", s) for s in sessions):
        raise ValueError("sessions must be unique two-digit labels")
    if not args.source_exclusions_root.is_dir():
        raise ValueError("source-exclusions root unavailable")
    roster = discover_subjects(args.bids_root)
    subjects = read_sublist(args.sublist) if args.sublist else roster
    if not set(subjects) <= set(roster):
        raise ValueError("requested IDs outside approved MRI roster")
    excluded = {p.name.removeprefix("Smith-SRA-") for p in args.source_exclusions_root.iterdir()
                if p.is_dir() and re.fullmatch(r"Smith-SRA-\d{5}", p.name)}
    skipped = len(set(subjects) & excluded)
    subjects = [s for s in subjects if s not in excluded]
    ready, missing = build_manifest(
        subjects, sessions, args.bids_root, args.fmriprep_root, args.confounds_root
    )
    write_tsv(args.output, ("subject", "session", "run"), ready)
    write_tsv(args.missing_output, ("subject", "session", "run", "reason"), missing)
    paired = len({(sub, ses) for sub, ses, run in ready if {r for s, se, r in ready if s == sub and se == ses} >= {"1", "2"}})
    print(f"Subjects considered: {len(subjects)}")
    print(f"Source-excluded subjects skipped: {skipped}")
    print(f"Ready UGR L1 runs: {len(ready)}")
    print(f"Subject-sessions with ready runs 1 and 2: {paired}")
    print(f"Missing-input rows: {len(missing)}")
    print(f"Ready manifest: {args.output.resolve()}")
    print(f"Missing-input report: {args.missing_output.resolve()}")
    print("Technical inventory only: apply reviewed holds via the Linux2 task handoff before execution; QC is not an exclusion decision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
