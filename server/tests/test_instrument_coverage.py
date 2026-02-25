import unittest

from app.services.instrument_coverage import get_nominal_instrument_coverage


class InstrumentCoverageTests(unittest.TestCase):
    def test_known_instrument_returns_expected_nominal_range_and_label(self) -> None:
        coverage = get_nominal_instrument_coverage("MIRI")

        self.assertEqual(coverage["waveNominalMinUm"], 4.9)
        self.assertEqual(coverage["waveNominalMaxUm"], 28.9)
        self.assertEqual(
            coverage["instrumentCoverageLabel"],
            "MIRI — mid IR (4.9–28.9 µm)",
        )

    def test_unknown_instrument_returns_null_fields(self) -> None:
        coverage = get_nominal_instrument_coverage("FOO_CAM")

        self.assertIsNone(coverage["waveNominalMinUm"])
        self.assertIsNone(coverage["waveNominalMaxUm"])
        self.assertIsNone(coverage["instrumentCoverageLabel"])

    def test_fgs_returns_null_fields(self) -> None:
        coverage = get_nominal_instrument_coverage("FGS")

        self.assertIsNone(coverage["waveNominalMinUm"])
        self.assertIsNone(coverage["waveNominalMaxUm"])
        self.assertIsNone(coverage["instrumentCoverageLabel"])

    def test_case_insensitive_and_common_spelling_variants_work(self) -> None:
        for value in ("NIRSpec", "NIRSPEC", "nir_spec", "NIRSpec/IFU"):
            with self.subTest(value=value):
                coverage = get_nominal_instrument_coverage(value)
                self.assertEqual(coverage["waveNominalMinUm"], 0.6)
                self.assertEqual(coverage["waveNominalMaxUm"], 5.3)
                self.assertEqual(
                    coverage["instrumentCoverageLabel"],
                    "NIRSpec — near IR (0.6–5.3 µm)",
                )


if __name__ == "__main__":
    unittest.main()
