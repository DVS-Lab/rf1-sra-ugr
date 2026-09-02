#!/usr/bin/env python3
"""Build the UGR model-3 network-PPI FEAT template reproducibly.

The validated model-3 seed-PPI template is the scientific source for task
EVs, interactions, contrasts, and all FEAT settings.  This builder expands
its one physiological EV into one target-network EV plus nine nuisance
network EVs.  Keeping this transformation executable avoids hand-editing a
large and index-sensitive FSF file.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SOURCE_EVS = 23
TARGET_EVS = 32
NETWORK_EXPANSION = TARGET_EVS - SOURCE_EVS
SOURCE_INTERACTION_FIRST = 13
TARGET_INTERACTION_FIRST = SOURCE_INTERACTION_FIRST + NETWORK_EXPANSION
NETWORK_NUISANCE_FIRST = 13
NETWORK_NUISANCE_LAST = 21
N_CONTRASTS = 18


def _shift_ev(index: int) -> int:
    return index if index < SOURCE_INTERACTION_FIRST else index + NETWORK_EXPANSION


def _shift_ev_references(text: str) -> str:
    """Shift every human-readable ``EV N`` reference in one comment line."""

    return re.sub(r"\bEV (\d+)\b", lambda m: f"EV {_shift_ev(int(m.group(1)))}", text)


def _transform_assignment(line: str) -> str:
    scalar = re.match(
        r"^(set fmri\((?:evtitle|shape|convolve|convolve_phase|tempfilt_yn|deriv_yn|custom))(\d+)(\).*)$",
        line,
    )
    if scalar:
        return f"{scalar.group(1)}{_shift_ev(int(scalar.group(2)))}{scalar.group(3)}"

    matrix = re.match(r"^(set fmri\((?:ortho|interactions|interactionsd))(\d+)\.(\d+)(\).*)$", line)
    if matrix:
        row = _shift_ev(int(matrix.group(2)))
        column = _shift_ev(int(matrix.group(3)))
        return f"{matrix.group(1)}{row}.{column}{matrix.group(4)}"

    contrast = re.match(r"^(set fmri\(con_(?:orig|real)\d+\.)(\d+)(\).*)$", line)
    if contrast:
        return f"{contrast.group(1)}{_shift_ev(int(contrast.group(2)))}{contrast.group(3)}"

    return line


def _network_ev_block(index: int, nuisance_number: int) -> list[str]:
    title = f"nuisance_network_{nuisance_number}"
    placeholder = f"OTHERNET{nuisance_number}"
    lines = [
        f"# EV {index} title",
        f'set fmri(evtitle{index}) "{title}"',
        "",
        f"# Basic waveform shape (EV {index})",
        "# 0 : Square",
        "# 1 : Sinusoid",
        "# 2 : Custom (1 entry per volume)",
        "# 3 : Custom (3 column format)",
        "# 4 : Interaction",
        "# 10 : Empty (all zeros)",
        f"set fmri(shape{index}) 2",
        "",
        f"# Convolution (EV {index})",
        "# 0 : None",
        "# 1 : Gaussian",
        "# 2 : Gamma",
        "# 3 : Double-Gamma HRF",
        "# 4 : Gamma basis functions",
        "# 5 : Sine basis functions",
        "# 6 : FIR basis functions",
        "# 8 : Alternate Double-Gamma",
        f"set fmri(convolve{index}) 0",
        "",
        f"# Convolve phase (EV {index})",
        f"set fmri(convolve_phase{index}) 0",
        "",
        f"# Apply temporal filtering (EV {index})",
        f"set fmri(tempfilt_yn{index}) 0",
        "",
        f"# Add temporal derivative (EV {index})",
        f"set fmri(deriv_yn{index}) 0",
        "",
        f"# Custom EV file (EV {index})",
        f'set fmri(custom{index}) "{placeholder}"',
        "",
    ]
    for other in range(TARGET_EVS + 1):
        lines.extend(
            [
                f"# Orthogonalise EV {index} wrt EV {other}",
                f"set fmri(ortho{index}.{other}) 0",
                "",
            ]
        )
    return lines


def _missing_orthogonalisation_entries() -> list[str]:
    lines = ["# Added network-PPI orthogonalisation entries"]
    existing_rows = list(range(1, 13)) + list(range(TARGET_INTERACTION_FIRST, TARGET_EVS + 1))
    for row in existing_rows:
        for column in range(NETWORK_NUISANCE_FIRST, NETWORK_NUISANCE_LAST + 1):
            lines.append(f"set fmri(ortho{row}.{column}) 0")
    lines.append("")
    return lines


def _missing_interaction_entries() -> list[str]:
    lines = ["# Added zero interaction weights for nuisance-network EVs"]
    for row in range(TARGET_INTERACTION_FIRST, TARGET_EVS + 1):
        for column in range(NETWORK_NUISANCE_FIRST, NETWORK_NUISANCE_LAST + 1):
            lines.append(f"set fmri(interactions{row}.{column}) 0")
            lines.append(f"set fmri(interactionsd{row}.{column}) 0")
    lines.append("")
    return lines


def _missing_contrast_entries() -> list[str]:
    lines = ["# Added zero weights for nuisance-network EVs"]
    for kind in ("orig", "real"):
        for contrast in range(1, N_CONTRASTS + 1):
            for column in range(NETWORK_NUISANCE_FIRST, NETWORK_NUISANCE_LAST + 1):
                lines.append(f"set fmri(con_{kind}{contrast}.{column}) 0")
    lines.append("")
    return lines


def build_template(source: str) -> str:
    lines = source.splitlines()
    output: list[str] = []
    inserted_networks = False
    inserted_contrasts = False

    for line in lines:
        if line == "set fmri(evs_orig) 23":
            line = "set fmri(evs_orig) 32"
        elif line == "set fmri(evs_real) 23":
            line = "set fmri(evs_real) 32"

        if line == "# EV 13 title":
            for index, nuisance_number in zip(
                range(NETWORK_NUISANCE_FIRST, NETWORK_NUISANCE_LAST + 1), range(1, 10)
            ):
                output.extend(_network_ev_block(index, nuisance_number))
            inserted_networks = True

        if line.startswith("# Contrast masking") and not inserted_contrasts:
            output.extend(_missing_orthogonalisation_entries())
            output.extend(_missing_interaction_entries())
            output.extend(_missing_contrast_entries())
            inserted_contrasts = True

        line = _shift_ev_references(line) if line.startswith("#") else _transform_assignment(line)

        if line == 'set fmri(evtitle12) "phys"':
            line = 'set fmri(evtitle12) "mainnet"'
        elif line == 'set fmri(custom12) "PHYS"':
            line = 'set fmri(custom12) "MAINNET"'
        elif line == 'set fmri(conname_orig.18) "phys"':
            line = 'set fmri(conname_orig.18) "mainnet"'
        elif line == 'set fmri(conname_real.18) "phys"':
            line = 'set fmri(conname_real.18) "mainnet"'

        output.append(line)

    if not inserted_networks:
        raise ValueError("source template has no EV 13 insertion point")
    if not inserted_contrasts:
        raise ValueError("source template has no contrast-masking insertion point")

    interaction_titles = (
        "ppi_nonsocial_high_constant",
        "ppi_nonsocial_high_pmod",
        "ppi_nonsocial_low_constant",
        "ppi_nonsocial_low_pmod",
        "ppi_social_high_constant",
        "ppi_social_high_pmod",
        "ppi_social_low_constant",
        "ppi_social_low_pmod",
        "ppi_rt_constant",
        "ppi_rt_pmod",
        "ppi_miss",
    )
    text = "\n".join(output) + "\n"
    for index, title in enumerate(interaction_titles, start=TARGET_INTERACTION_FIRST):
        text = re.sub(
            rf'^set fmri\(evtitle{index}\) ".*"$',
            f'set fmri(evtitle{index}) "{title}"',
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="fail if OUTPUT differs; do not write")
    args = parser.parse_args()

    generated = build_template(args.source.read_text(encoding="utf-8"))
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != generated:
            raise SystemExit(f"ERROR: generated network-PPI template differs: {args.output}")
        print(f"PASS: generated network-PPI template is current: {args.output}")
        return 0

    args.output.write_text(generated, encoding="utf-8")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
