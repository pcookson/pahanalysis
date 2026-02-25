from __future__ import annotations

from typing import Any


NominalCoverage = dict[str, float | str | None]


_NOMINAL_INSTRUMENT_COVERAGE: dict[str, NominalCoverage] = {
    "MIRI": {
        "waveNominalMinUm": 4.9,
        "waveNominalMaxUm": 28.9,
        "instrumentCoverageLabel": "MIRI — mid IR (4.9–28.9 µm)",
    },
    "NIRSPEC": {
        "waveNominalMinUm": 0.6,
        "waveNominalMaxUm": 5.3,
        "instrumentCoverageLabel": "NIRSpec — near IR (0.6–5.3 µm)",
    },
    "NIRCAM": {
        "waveNominalMinUm": 0.6,
        "waveNominalMaxUm": 5.0,
        "instrumentCoverageLabel": "NIRCam — near IR (0.6–5.0 µm)",
    },
    "NIRISS": {
        "waveNominalMinUm": 0.8,
        "waveNominalMaxUm": 5.0,
        "instrumentCoverageLabel": "NIRISS — near IR (0.8–5.0 µm)",
    },
}

_NULL_COVERAGE: NominalCoverage = {
    "waveNominalMinUm": None,
    "waveNominalMaxUm": None,
    "instrumentCoverageLabel": None,
}


def get_nominal_instrument_coverage(instrument_name: Any) -> NominalCoverage:
    """Return nominal wavelength coverage by instrument (not FITS-derived).

    Developer note: these values are approximate instrument-level ranges for UI hints
    only. They are not computed from products/FITS headers and may differ from any
    specific observation or exposure mode.
    """
    normalized = _normalize_instrument_token(instrument_name)
    if not normalized:
        return dict(_NULL_COVERAGE)

    if "FGS" in normalized:
        return dict(_NULL_COVERAGE)

    for canonical_name, coverage in _NOMINAL_INSTRUMENT_COVERAGE.items():
        if canonical_name in normalized:
            return dict(coverage)

    return dict(_NULL_COVERAGE)


def _normalize_instrument_token(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    return "".join(ch for ch in text.upper() if ch.isalnum())

