from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import astropy.units as u
from astroquery.mast import Observations

from app.services.instrument_coverage import get_nominal_instrument_coverage


@dataclass
class SearchServiceError(Exception):
    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


def search_jwst_by_target(target: str, radius_arcsec: float) -> list[dict[str, Any]]:
    """Search MAST by target name and return normalized JWST observation rows.

    Notes:
    - `t_min` is returned as the raw MJD float provided by MAST (or null).
    """
    try:
        table = Observations.query_object(
            target,
            radius=radius_arcsec * u.arcsec,
        )
    except Exception as exc:
        raise SearchServiceError(
            "Failed to query MAST for target search",
            details={"target": target, "radiusArcsec": radius_arcsec, "error": str(exc)},
        ) from exc

    if table is None:
        return []

    normalized_rows: list[dict[str, Any]] = []
    for row in table:
        if not _is_jwst_row(row):
            continue
        normalized_rows.append(_normalize_row(row))

    return normalized_rows


def _is_jwst_row(row: Any) -> bool:
    for column in ("obs_collection", "project", "obs_collection_name"):
        value = _get_value(row, column)
        if _as_upper_str(value) == "JWST":
            return True
    return False


def _normalize_row(row: Any) -> dict[str, Any]:
    obsid_value = _get_value(row, "obsid", "obs_id")
    target_name_value = _get_value(row, "target_name")
    instrument_name = _as_string_or_none(_get_value(row, "instrument_name"))
    nominal_coverage = get_nominal_instrument_coverage(instrument_name)

    return {
        "obsid": _as_required_string(obsid_value),
        "target_name": _as_required_string(target_name_value),
        "s_ra": _as_float_or_none(_get_value(row, "s_ra", "ra")),
        "s_dec": _as_float_or_none(_get_value(row, "s_dec", "dec")),
        "instrument_name": instrument_name,
        "t_min": _as_float_or_none(_get_value(row, "t_min")),
        "proposal_id": _as_string_or_none(_get_value(row, "proposal_id", "proposalId")),
        "data_rights": _as_string_or_none(_get_value(row, "data_rights", "dataRights")),
        "waveNominalMinUm": nominal_coverage["waveNominalMinUm"],
        "waveNominalMaxUm": nominal_coverage["waveNominalMaxUm"],
        "instrumentCoverageLabel": nominal_coverage["instrumentCoverageLabel"],
    }


def _get_value(row: Any, *candidates: str) -> Any:
    for name in candidates:
        try:
            value = row[name]
        except Exception:
            continue
        cleaned = _clean_value(value)
        return cleaned
    return None


def _clean_value(value: Any) -> Any:
    if value is None:
        return None

    if getattr(value, "mask", False) is True:
        return None

    try:
        value = value.item()
    except Exception:
        pass

    if getattr(value, "mask", False) is True:
        return None

    return value


def _as_upper_str(value: Any) -> str | None:
    text = _as_string_or_none(value)
    if text is None:
        return None
    return text.upper()


def _as_required_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text == "":
        return None
    return text


def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
