from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from astroquery.mast import Observations


@dataclass
class ProductServiceError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def list_products_for_obs(obsid: str) -> list[dict[str, Any]]:
    try:
        products = Observations.get_product_list(obsid)
    except Exception as exc:
        raise ProductServiceError(
            f"Failed to list products for obsid {obsid}: {exc}"
        ) from exc

    if products is None:
        return []

    normalized: list[dict[str, Any]] = []
    for row in products:
        normalized_row = _normalize_product_row(obsid, row)
        if _should_include_product(normalized_row):
            normalized.append(normalized_row)
    return normalized


def _normalize_product_row(obsid: str, row: Any) -> dict[str, Any]:
    filename = _as_string_or_none(_get_value(row, "productFilename"))
    mast_product_id = _as_string_or_none(
        _get_value(row, "productID", "product_id", "dataURI", "dataURI")
    )
    derived_product_id = mast_product_id or _derive_product_id(obsid, filename)

    kind, is_plottable_candidate = _classify_product(filename)

    return {
        "product_id": derived_product_id,
        "productFilename": filename,
        "size": _as_int_or_none(_get_value(row, "size")),
        "productType": _as_string_or_none(_get_value(row, "productType")),
        "calib_level": _as_int_or_none(_get_value(row, "calib_level")),
        "description": _as_string_or_none(_get_value(row, "description")),
        "kind": kind,
        "is_plottable_candidate": is_plottable_candidate,
    }


def _should_include_product(product: dict[str, Any]) -> bool:
    filename = product["productFilename"]
    if not isinstance(filename, str):
        return False

    lower_filename = filename.lower()

    # Exclude previews/metadata entirely.
    if lower_filename.endswith((".jpg", ".jpeg", ".png", ".json", ".csv")):
        return False

    # Only FITS products are relevant to downstream analysis.
    if not lower_filename.endswith(".fits"):
        return False

    calib_level = product["calib_level"]
    return calib_level == 3


def _classify_product(filename: str | None) -> tuple[str, bool]:
    if not filename:
        return ("other", False)

    lower_filename = filename.lower()
    if lower_filename.endswith("_s3d.fits"):
        return ("cube3d", True)
    if lower_filename.endswith("_x1d.fits"):
        return ("spectrum1d", True)
    return ("other", False)


def _derive_product_id(obsid: str, filename: str | None) -> str:
    if filename:
        return f"{obsid}:{filename}"
    return f"{obsid}:unknown"


def _get_value(row: Any, *candidates: str) -> Any:
    for name in candidates:
        try:
            value = row[name]
        except Exception:
            continue
        return _clean_value(value)
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


def _as_string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text == "":
        return None
    return text


def _as_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
