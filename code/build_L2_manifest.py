#!/usr/bin/env python3
"""Build UGR L2 readiness from complete run-1 and run-2 model-3 L1 outputs."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


def normalize_type(value: str) -> str:
    if value == "act" or (value.startswith("ppi_seed-") and len(value) > len("ppi_seed-")):
        return value
    raise argparse.ArgumentTypeError("type must be act or ppi_seed-<seed>")


def l1_path(root: Path, subject: str, session: str, run: str, analysis_type: str) -> Path:
    return (
        root
        / f"sub-{subject}"
        / f"ses-{session}"
        / f"L1_task-ugr_ses-{session}_model-3_type-{analysis_type}_run-{run}_sm-5.feat"
    )


def read_sublist(path: Path) -> list[str]:
    values = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.split("#", 1)[0].strip().removeprefix("sub-")
        if value:
            values.append(value)
    return sorted(dict.fromkeys(values))


def discover_subjects(root: Path) -> list[str]:
    return sorted(path.name.removeprefix("sub-") for path in root.glob("sub-*") if path.is_dir())


def write(path: Path, header: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--fsl-root",
        type=Path,
        default=Path(os.environ.get("FSL_DERIVATIVES_ROOT", root / "derivatives" / "fsl")),
    )
    parser.add_argument("--sublist", type=Path)
    parser.add_argument("--sessions", default="01")
    parser.add_argument("--type", required=True, type=normalize_type)
    parser.add_argument("--output", type=Path, default=root / "logs" / "runlists" / "L2-ready.tsv")
    parser.add_argument(
        "--missing-output", type=Path, default=root / "logs" / "runlists" / "L2-missing.tsv"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sessions = [value.strip().removeprefix("ses-") for value in args.sessions.split(",") if value.strip()]
    subjects = read_sublist(args.sublist) if args.sublist else discover_subjects(args.fsl_root)
    ready: list[tuple[str, str]] = []
    missing: list[tuple[str, str, str]] = []
    for subject in subjects:
        for session in sessions:
            absent = []
            for run in ("1", "2"):
                feat = l1_path(args.fsl_root, subject, session, run, args.type)
                if not (feat / "cluster_mask_zstat1.nii.gz").is_file():
                    absent.append(f"run-{run}")
            if absent:
                missing.append((subject, session, ",".join(absent)))
            else:
                ready.append((subject, session))
    write(args.output, ("subject", "session"), ready)
    write(args.missing_output, ("subject", "session", "missing_l1"), missing)
    print(f"L2 type: {args.type}")
    print(f"Ready subject-sessions: {len(ready)}")
    print(f"Incomplete subject-sessions: {len(missing)}")
    print(f"Ready manifest: {args.output.resolve()}")
    print(f"Missing report: {args.missing_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
