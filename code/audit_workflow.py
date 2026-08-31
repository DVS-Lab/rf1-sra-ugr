#!/usr/bin/env python3
"""Audit visible UGR inputs and downstream model-3 completion.

The audit discovers subject/session/run units from the union of canonical BIDS
events, fMRIPrep BOLD, and production confounds. It writes detailed status
tables plus wrapper-compatible todo manifests without changing derivatives.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


EVENT_RE = re.compile(
    r"^sub-(?P<subject>[^_]+)_ses-(?P<session>[^_]+)_task-ugr_run-(?P<run>[^_]+)_events\.tsv$"
)
BOLD_RE = re.compile(
    r"^sub-(?P<subject>[^_]+)_ses-(?P<session>[^_]+)_task-ugr_run-(?P<run>[^_]+)_part-mag_"
    r"space-MNI152NLin6Asym_desc-preproc_bold\.nii\.gz$"
)
CONFOUNDS_RE = re.compile(
    r"^sub-(?P<subject>[^_]+)_ses-(?P<session>[^_]+)_task-ugr_run-(?P<run>[^_]+)_"
    r"desc-TedanaPlusConfounds\.tsv$"
)

REQUIRED_EVS = (
    "nonsocial_high_constant",
    "nonsocial_high_pmod",
    "nonsocial_low_constant",
    "nonsocial_low_pmod",
    "social_high_constant",
    "social_high_pmod",
    "social_low_constant",
    "social_low_pmod",
    "rt_constant",
    "rt_pmod",
)


@dataclass(frozen=True, order=True)
class Unit:
    subject: str
    session: str
    run: str


def sort_key(unit: Unit) -> tuple[str, str, tuple[bool, object]]:
    run_key: tuple[bool, object]
    if unit.run.isdigit():
        run_key = (False, int(unit.run))
    else:
        run_key = (True, unit.run)
    return unit.subject, unit.session, run_key


def parse_sessions(value: str) -> set[str] | None:
    if value.strip().lower() == "all":
        return None
    sessions = {
        item.strip().removeprefix("ses-") for item in value.split(",") if item.strip()
    }
    if not sessions:
        raise argparse.ArgumentTypeError("sessions must be 'all' or a comma-separated list")
    return sessions


def discover(root: Path, pattern: str, matcher: re.Pattern[str]) -> set[Unit]:
    units: set[Unit] = set()
    if not root.is_dir():
        return units
    for path in root.glob(pattern):
        match = matcher.match(path.name)
        if match:
            units.add(Unit(match["subject"], match["session"], match["run"]))
    return units


def input_paths(
    unit: Unit, bids_root: Path, fmriprep_root: Path, confounds_root: Path
) -> tuple[Path, Path, Path]:
    stem = f"sub-{unit.subject}_ses-{unit.session}_task-ugr_run-{unit.run}"
    events = (
        bids_root
        / f"sub-{unit.subject}"
        / f"ses-{unit.session}"
        / "func"
        / f"{stem}_events.tsv"
    )
    bold = (
        fmriprep_root
        / f"sub-{unit.subject}"
        / f"ses-{unit.session}"
        / "func"
        / f"{stem}_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz"
    )
    confounds = (
        confounds_root
        / f"sub-{unit.subject}"
        / f"{stem}_desc-TedanaPlusConfounds.tsv"
    )
    return events, bold, confounds


def file_present(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def completion_state(base: Path, required: list[Path]) -> str:
    if all(file_present(path) for path in required):
        return "complete"
    if base.exists() or any(path.exists() for path in required):
        return "partial"
    return "missing"


def ev_state(fsl_root: Path, unit: Unit) -> str:
    prefix = (
        fsl_root
        / "EVfiles"
        / f"sub-{unit.subject}"
        / f"ses-{unit.session}"
        / "ugr"
        / "model-3"
        / f"run-{unit.run}"
    )
    required = [Path(f"{prefix}_{name}.txt") for name in REQUIRED_EVS]
    return completion_state(prefix.parent, required)


def l1_dir(fsl_root: Path, unit: Unit, analysis_type: str) -> Path:
    return (
        fsl_root
        / f"sub-{unit.subject}"
        / f"ses-{unit.session}"
        / (
            f"L1_task-ugr_ses-{unit.session}_model-3_type-{analysis_type}_"
            f"run-{unit.run}_sm-5.feat"
        )
    )


def l1_state(fsl_root: Path, unit: Unit, analysis_type: str, ncopes: int) -> str:
    base = l1_dir(fsl_root, unit, analysis_type)
    required = [
        base / "design.mat",
        base / "design.con",
        base / "mask.nii.gz",
        base / "cluster_mask_zstat1.nii.gz",
    ]
    for cope in range(1, ncopes + 1):
        required.extend(
            [base / "stats" / f"cope{cope}.nii.gz", base / "stats" / f"zstat{cope}.nii.gz"]
        )
    return completion_state(base, required)


def l2_dir(fsl_root: Path, subject: str, session: str, analysis_type: str) -> Path:
    return (
        fsl_root
        / f"sub-{subject}"
        / f"ses-{session}"
        / f"L2_task-ugr_ses-{session}_model-3_type-{analysis_type}_sm-5.gfeat"
    )


def l2_state(
    fsl_root: Path, subject: str, session: str, analysis_type: str, ncopes: int
) -> str:
    base = l2_dir(fsl_root, subject, session, analysis_type)
    required = [base / "design.mat", base / "design.con"]
    for cope in range(1, ncopes + 1):
        cope_dir = base / f"cope{cope}.feat"
        required.extend(
            [
                cope_dir / "design.mat",
                cope_dir / "design.con",
                cope_dir / "mask.nii.gz",
                cope_dir / "stats" / "cope1.nii.gz",
                cope_dir / "stats" / "zstat1.nii.gz",
                cope_dir / "cluster_mask_zstat1.nii.gz",
            ]
        )
    return completion_state(base, required)


def write_tsv(path: Path, header: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    upstream = Path(os.environ.get("RF1_SRA_UPSTREAM_ROOT", "/ZPOOL/data/projects/rf1-sra-linux2"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bids-root", type=Path, default=Path(os.environ.get("BIDS_ROOT", upstream / "bids")))
    parser.add_argument(
        "--fmriprep-root",
        type=Path,
        default=Path(os.environ.get("FMRIPREP_ROOT", upstream / "derivatives" / "fmriprep")),
    )
    parser.add_argument(
        "--confounds-root",
        type=Path,
        default=Path(os.environ.get("CONFOUNDS_ROOT", upstream / "derivatives" / "fsl" / "confounds_tedana")),
    )
    parser.add_argument(
        "--fsl-root",
        type=Path,
        default=Path(os.environ.get("FSL_DERIVATIVES_ROOT", root / "derivatives" / "fsl")),
    )
    parser.add_argument("--sessions", default="all")
    parser.add_argument("--seed", default="dACC")
    parser.add_argument("--output-dir", type=Path, default=root / "logs" / "audits" / "current")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sessions = parse_sessions(args.sessions)
    ppi_type = f"ppi_seed-{args.seed}"

    event_units = discover(
        args.bids_root, "sub-*/ses-*/func/*task-ugr_run-*_events.tsv", EVENT_RE
    )
    bold_units = discover(
        args.fmriprep_root,
        "sub-*/ses-*/func/*task-ugr_run-*_part-mag_space-MNI152NLin6Asym_desc-preproc_bold.nii.gz",
        BOLD_RE,
    )
    confound_units = discover(
        args.confounds_root,
        "sub-*/*task-ugr_run-*_desc-TedanaPlusConfounds.tsv",
        CONFOUNDS_RE,
    )
    units = event_units | bold_units | confound_units
    if sessions is not None:
        units = {unit for unit in units if unit.session in sessions}
    ordered_units = sorted(units, key=sort_key)

    input_missing: list[tuple[str, ...]] = []
    unit_status: list[tuple[str, ...]] = []
    input_ready: list[Unit] = []
    ev_todo: list[tuple[str, ...]] = []
    act_todo: list[tuple[str, ...]] = []
    ppi_todo: list[tuple[str, ...]] = []
    states: dict[Unit, tuple[str, str, str]] = {}

    for unit in ordered_units:
        events, bold, confounds = input_paths(
            unit, args.bids_root, args.fmriprep_root, args.confounds_root
        )
        absent = [
            label
            for label, path in (("events", events), ("BOLD", bold), ("confounds", confounds))
            if not file_present(path)
        ]
        if absent:
            input_missing.append((unit.subject, unit.session, unit.run, ",".join(absent)))
            unit_status.append(
                (unit.subject, unit.session, unit.run, "missing:" + ",".join(absent), "blocked", "blocked", "blocked")
            )
            continue

        input_ready.append(unit)
        evs = ev_state(args.fsl_root, unit)
        act = l1_state(args.fsl_root, unit, "act", 17)
        ppi = l1_state(args.fsl_root, unit, ppi_type, 18)
        states[unit] = (evs, act, ppi)
        unit_status.append((unit.subject, unit.session, unit.run, "ready", evs, act, ppi))

        if evs != "complete":
            ev_todo.append((unit.subject, unit.session, unit.run))
        if evs == "complete" and act != "complete":
            act_todo.append((unit.subject, unit.session, unit.run))
        if evs == "complete" and act == "complete" and ppi != "complete":
            ppi_todo.append((unit.subject, unit.session, unit.run))

    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for unit in input_ready:
        grouped[(unit.subject, unit.session)].add(unit.run)

    session_status: list[tuple[str, ...]] = []
    l2_act_todo: list[tuple[str, ...]] = []
    l2_ppi_todo: list[tuple[str, ...]] = []
    paired = 0
    act_l2_eligible = 0
    ppi_l2_eligible = 0
    act_l2_complete = 0
    ppi_l2_complete = 0
    for (subject, session), runs in sorted(grouped.items()):
        if not {"1", "2"}.issubset(runs):
            session_status.append((subject, session, "no", "blocked", "blocked"))
            continue
        paired += 1
        unit1 = Unit(subject, session, "1")
        unit2 = Unit(subject, session, "2")
        act_inputs = all(states[unit][1] == "complete" for unit in (unit1, unit2))
        ppi_inputs = all(states[unit][2] == "complete" for unit in (unit1, unit2))
        act_l2 = l2_state(args.fsl_root, subject, session, "act", 17) if act_inputs else "blocked"
        ppi_l2 = l2_state(args.fsl_root, subject, session, ppi_type, 18) if ppi_inputs else "blocked"
        session_status.append((subject, session, "yes", act_l2, ppi_l2))
        if act_inputs:
            act_l2_eligible += 1
            if act_l2 == "complete":
                act_l2_complete += 1
            else:
                l2_act_todo.append((subject, session))
        if ppi_inputs:
            ppi_l2_eligible += 1
            if ppi_l2 == "complete":
                ppi_l2_complete += 1
            else:
                l2_ppi_todo.append((subject, session))

    out = args.output_dir
    write_tsv(out / "L1-ready.tsv", ("subject", "session", "run"), [(u.subject, u.session, u.run) for u in input_ready])
    write_tsv(out / "L1-input-missing.tsv", ("subject", "session", "run", "missing"), input_missing)
    write_tsv(
        out / "unit-status.tsv",
        ("subject", "session", "run", "inputs", "evs", "l1_act", f"l1_{ppi_type}"),
        unit_status,
    )
    write_tsv(out / "EV-todo.tsv", ("subject", "session", "run"), ev_todo)
    write_tsv(out / "L1-act-todo.tsv", ("subject", "session", "run"), act_todo)
    write_tsv(out / f"L1-{ppi_type}-todo.tsv", ("subject", "session", "run"), ppi_todo)
    write_tsv(
        out / "session-status.tsv",
        ("subject", "session", "runs_1_and_2", "l2_act", f"l2_{ppi_type}"),
        session_status,
    )
    write_tsv(out / "L2-act-todo.tsv", ("subject", "session"), l2_act_todo)
    write_tsv(out / f"L2-{ppi_type}-todo.tsv", ("subject", "session"), l2_ppi_todo)

    ev_complete = sum(states[unit][0] == "complete" for unit in input_ready)
    act_complete = sum(states[unit][1] == "complete" for unit in input_ready)
    ppi_complete = sum(states[unit][2] == "complete" for unit in input_ready)
    act_blocked = sum(states[unit][0] != "complete" for unit in input_ready)
    ppi_blocked = sum(
        states[unit][0] != "complete" or states[unit][1] != "complete"
        for unit in input_ready
    )
    discovered_sessions = sorted({unit.session for unit in ordered_units})
    lines = [
        "UGR WORKFLOW AUDIT",
        f"Sessions audited: {','.join(discovered_sessions) if discovered_sessions else 'none'}",
        f"Visible UGR units: {len(ordered_units)}",
        f"Input-ready units: {len(input_ready)}",
        f"Input-missing units: {len(input_missing)}",
        f"EV-complete units: {ev_complete}",
        f"EV todo: {len(ev_todo)}",
        f"L1 activation complete: {act_complete}",
        f"L1 activation todo: {len(act_todo)}",
        f"L1 activation blocked by EVs: {act_blocked}",
        f"L1 {ppi_type} complete: {ppi_complete}",
        f"L1 {ppi_type} todo: {len(ppi_todo)}",
        f"L1 {ppi_type} blocked by EVs/activation: {ppi_blocked}",
        f"Input-ready subject-sessions with runs 1 and 2: {paired}",
        f"L2 activation complete/eligible: {act_l2_complete}/{act_l2_eligible}",
        f"L2 activation todo: {len(l2_act_todo)}",
        f"L2 activation blocked by L1: {paired - act_l2_eligible}",
        f"L2 {ppi_type} complete/eligible: {ppi_l2_complete}/{ppi_l2_eligible}",
        f"L2 {ppi_type} todo: {len(l2_ppi_todo)}",
        f"L2 {ppi_type} blocked by L1: {paired - ppi_l2_eligible}",
        f"Detailed reports: {out.resolve()}",
    ]
    summary = "\n".join(lines) + "\n"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
