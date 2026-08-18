#!/usr/bin/env python3
"""Build a session/run-aware UGR L1 readiness manifest from visible inputs."""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path


EVENT_RE = re.compile(r"^sub-(?P<subject>[^_]+)_ses-(?P<session>[^_]+)_task-ugr_run-(?P<run>[^_]+)_events\.tsv$")


def read_sublist(path: Path) -> list[str]:
    subjects: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.split("#", 1)[0].strip()
        if value:
            subjects.append(value.removeprefix("sub-"))
    return sorted(dict.fromkeys(subjects))


def discover_subjects(bids_root: Path) -> list[str]:
    return sorted(path.name.removeprefix("sub-") for path in bids_root.glob("sub-*") if path.is_dir())


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
            func_dir = bids_root / f"sub-{subject}" / f"ses-{session}" / "func"
            if not func_dir.is_dir():
                missing.append((subject, session, "", "missing BIDS session func directory"))
                continue
            runs: list[str] = []
            for events in sorted(func_dir.glob(f"sub-{subject}_ses-{session}_task-ugr_run-*_events.tsv")):
                match = EVENT_RE.match(events.name)
                if match:
                    runs.append(match.group("run"))
            if not runs:
                missing.append((subject, session, "", "no canonical UGR events"))
                continue
            for run in sorted(dict.fromkeys(runs), key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value)):
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
    parser.add_argument("--sessions", default="01")
    parser.add_argument("--output", type=Path, default=root / "logs" / "runlists" / "L1-ready.tsv")
    parser.add_argument(
        "--missing-output", type=Path, default=root / "logs" / "runlists" / "L1-missing.tsv"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sessions = [value.removeprefix("ses-").strip() for value in args.sessions.split(",") if value.strip()]
    subjects = read_sublist(args.sublist) if args.sublist else discover_subjects(args.bids_root)
    ready, missing = build_manifest(
        subjects, sessions, args.bids_root, args.fmriprep_root, args.confounds_root
    )
    write_tsv(args.output, ("subject", "session", "run"), ready)
    write_tsv(args.missing_output, ("subject", "session", "run", "reason"), missing)
    paired = len({(sub, ses) for sub, ses, run in ready if {r for s, se, r in ready if s == sub and se == ses} >= {"1", "2"}})
    print(f"Subjects considered: {len(subjects)}")
    print(f"Ready UGR L1 runs: {len(ready)}")
    print(f"Subject-sessions with ready runs 1 and 2: {paired}")
    print(f"Missing-input rows: {len(missing)}")
    print(f"Ready manifest: {args.output.resolve()}")
    print(f"Missing-input report: {args.missing_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
