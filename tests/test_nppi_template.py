from __future__ import annotations

import gzip
import hashlib
import math
import re
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from build_model3_nppi_template import build_template


ACT = ROOT / "templates" / "L1_task-ugr_model-3_type-act.fsf"
PPI = ROOT / "templates" / "L1_task-ugr_model-3_type-ppi.fsf"
NPPI = ROOT / "templates" / "L1_task-ugr_model-3_type-nppi.fsf"


def assignments(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^set fmri\(([^)]+)\) (.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if key in found:
            raise AssertionError(f"duplicate FSF assignment: {key}")
        found[key] = value.strip('"')
    return found


def nifti_summary(path: Path) -> tuple[tuple[int, ...], tuple[float, ...], tuple[float, ...], int, int]:
    raw = gzip.open(path, "rb").read()
    endian = "<" if struct.unpack("<I", raw[:4])[0] == 348 else ">"
    dimensions = struct.unpack(endian + "8h", raw[40:56])
    shape = tuple(dimensions[1 : dimensions[0] + 1])
    datatype = struct.unpack(endian + "h", raw[70:72])[0]
    zoom_values = struct.unpack(endian + "8f", raw[76:108])
    zooms = tuple(zoom_values[1 : dimensions[0] + 1])
    sform = struct.unpack(endian + "12f", raw[280:328])
    offset = int(struct.unpack(endian + "f", raw[108:112])[0])
    formats = {2: "B", 4: "h", 8: "i", 16: "f", 64: "d", 256: "b", 512: "H", 768: "I"}
    if datatype not in formats:
        raise AssertionError(f"unsupported NIfTI datatype {datatype} in {path}")
    count = math.prod(shape)
    values = struct.unpack_from(endian + str(count) + formats[datatype], raw, offset)
    if not all(math.isfinite(value) for value in values):
        raise AssertionError(f"non-finite voxel in {path}")
    return shape, zooms, sform, len(set(values)), sum(value != 0 for value in values)


class NetworkPpiTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.act = assignments(ACT)
        cls.ppi = assignments(PPI)
        cls.nppi = assignments(NPPI)

    def test_committed_template_is_exact_reproducible_expansion(self) -> None:
        expected = build_template(PPI.read_text(encoding="utf-8"))
        self.assertEqual(NPPI.read_text(encoding="utf-8"), expected)

    def test_ev_structure_and_missed_trial_convolution(self) -> None:
        self.assertEqual(self.nppi["evs_orig"], "32")
        self.assertEqual(self.nppi["evs_real"], "32")
        self.assertEqual(self.nppi["ncon_orig"], "18")
        self.assertEqual(self.nppi["ncon_real"], "18")
        for index in range(1, 12):
            self.assertEqual(self.nppi[f"evtitle{index}"], self.act[f"evtitle{index}"])
            self.assertEqual(self.nppi[f"convolve{index}"], self.act[f"convolve{index}"])
        self.assertEqual(self.nppi["evtitle11"], "miss")
        self.assertEqual(self.nppi["convolve11"], "3")
        self.assertEqual(self.nppi["custom11"], "MISSED_TRIAL")
        self.assertEqual(self.nppi["evtitle12"], "mainnet")
        self.assertEqual(self.nppi["shape12"], "2")
        self.assertEqual(self.nppi["convolve12"], "0")
        self.assertEqual(self.nppi["custom12"], "MAINNET")
        for index in range(13, 22):
            nuisance = index - 12
            self.assertEqual(self.nppi[f"evtitle{index}"], f"nuisance_network_{nuisance}")
            self.assertEqual(self.nppi[f"shape{index}"], "2")
            self.assertEqual(self.nppi[f"convolve{index}"], "0")
            self.assertEqual(self.nppi[f"custom{index}"], f"OTHERNET{nuisance}")

    def test_brain_derived_time_series_are_never_hrf_convolved(self) -> None:
        # EVs 1-11 are event/task regressors.  EV 11 is the missed-trial
        # epoch, not a physiological series, so it retains the double-gamma
        # HRF when populated.
        for template in (self.ppi, self.nppi):
            for index in range(1, 12):
                self.assertEqual(template[f"convolve{index}"], "3")

        # The seed-PPI physiological EV is sampled from BOLD and therefore
        # enters exactly as extracted, with no HRF convolution or derivative.
        self.assertEqual(self.ppi["evtitle12"], "phys")
        self.assertEqual(self.ppi["shape12"], "2")
        self.assertEqual(self.ppi["convolve12"], "0")
        self.assertEqual(self.ppi["tempfilt_yn12"], "0")
        self.assertEqual(self.ppi["deriv_yn12"], "0")
        for index in range(13, 24):
            self.assertEqual(self.ppi[f"shape{index}"], "4")
            self.assertEqual(self.ppi[f"convolve{index}"], "0")

        # Network-PPI uses ten brain-derived time courses: one target and
        # nine nuisance networks.  Every one enters unconvolved.
        for index in range(12, 22):
            self.assertEqual(self.nppi[f"shape{index}"], "2")
            self.assertEqual(self.nppi[f"convolve{index}"], "0")
            self.assertEqual(self.nppi[f"tempfilt_yn{index}"], "0")
            self.assertEqual(self.nppi[f"deriv_yn{index}"], "0")
        for index in range(22, 33):
            self.assertEqual(self.nppi[f"shape{index}"], "4")
            self.assertEqual(self.nppi[f"convolve{index}"], "0")

    def test_interactions_are_task_by_mainnet_with_complete_matrices(self) -> None:
        for psychological_ev, interaction_ev in enumerate(range(22, 33), start=1):
            self.assertEqual(self.nppi[f"shape{interaction_ev}"], "4")
            self.assertEqual(self.nppi[f"convolve{interaction_ev}"], "0")
            self.assertEqual(
                {column for column in range(1, interaction_ev) if self.nppi[f"interactions{interaction_ev}.{column}"] == "1"},
                {psychological_ev, 12},
            )
            self.assertEqual(self.nppi[f"interactionsd{interaction_ev}.12"], "2")
            for column in range(13, 22):
                self.assertEqual(self.nppi[f"interactions{interaction_ev}.{column}"], "0")
                self.assertEqual(self.nppi[f"interactionsd{interaction_ev}.{column}"], "0")

    def test_interaction_zeroing_matches_regressor_semantics(self) -> None:
        # FEAT interaction zeroing codes: 0 = Min, 1 = Centre, 2 = Mean.
        # Ordinary task regressors use Min; signed parametric modulators use
        # Centre; the brain-derived physiological/network signal uses Mean.
        expected_psychological_zeroing = (0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0)
        for template, interaction_first in ((self.ppi, 13), (self.nppi, 22)):
            for psychological_ev, expected_zeroing in enumerate(
                expected_psychological_zeroing, start=1
            ):
                interaction_ev = interaction_first + psychological_ev - 1
                selected = {
                    column
                    for column in range(1, interaction_ev)
                    if template[f"interactions{interaction_ev}.{column}"] == "1"
                }
                self.assertEqual(selected, {psychological_ev, 12})
                self.assertEqual(
                    template[f"interactionsd{interaction_ev}.{psychological_ev}"],
                    str(expected_zeroing),
                )
                self.assertEqual(template[f"interactionsd{interaction_ev}.12"], "2")

    def test_orthogonalisation_matrix_is_complete_and_zero(self) -> None:
        keys = {
            f"ortho{row}.{column}"
            for row in range(1, 33)
            for column in range(0, 33)
        }
        actual = {key for key in self.nppi if key.startswith("ortho")}
        self.assertEqual(actual, keys)
        self.assertTrue(all(self.nppi[key] == "0" for key in keys))

    def test_contrasts_are_seed_ppi_vectors_with_network_nuisance_columns_inserted(self) -> None:
        for kind in ("orig", "real"):
            for contrast in range(1, 19):
                source = [self.ppi[f"con_{kind}{contrast}.{column}"] for column in range(1, 24)]
                expected = source[:12] + ["0"] * 9 + source[12:]
                actual = [self.nppi[f"con_{kind}{contrast}.{column}"] for column in range(1, 33)]
                self.assertEqual(actual, expected)
        self.assertEqual(self.nppi["conname_orig.18"], "mainnet")
        self.assertEqual(self.nppi["conname_real.18"], "mainnet")
        self.assertEqual(self.nppi["featwatcher_yn"], "0")

    def test_network_maps_are_continuous_and_match_the_canonical_grid(self) -> None:
        seed_shape, seed_zooms, seed_sform, _, _ = nifti_summary(ROOT / "masks" / "seed-dACC.nii.gz")
        checksum_rows = [line.split() for line in (ROOT / "masks" / "network-maps.sha256").read_text().splitlines()]
        expected_digests = {filename: digest for digest, filename in checksum_rows}
        self.assertEqual(len(expected_digests), 10)
        digests = set()
        for index in range(10):
            path = ROOT / "masks" / f"nan_rPNAS_2mm_net000{index}.nii.gz"
            shape, zooms, sform, unique, nonzero = nifti_summary(path)
            self.assertEqual(shape, seed_shape)
            self.assertEqual(zooms, seed_zooms)
            self.assertEqual(sform, seed_sform)
            self.assertGreater(unique, 100)
            self.assertGreater(nonzero, 0)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, expected_digests[path.name])
            digests.add(digest)
        self.assertEqual(len(digests), 10)


if __name__ == "__main__":
    unittest.main()
