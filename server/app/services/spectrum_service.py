from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits

from app.config import settings
from app.services.download_service import JWST_PRODUCT_PREFIX

WAVELENGTH_COLUMN_CANDIDATES = ["WAVELENGTH", "wavelength"]
FLUX_COLUMN_CANDIDATES = ["FLUX", "flux", "SURF_BRIGHT", "surf_bright"]
ERROR_COLUMN_CANDIDATES = ["ERROR", "ERR", "flux_error", "FLUX_ERROR", "error"]
SUPPORTED_SUFFIXES = ("_x1d.fits", "_c1d.fits")


@dataclass
class SpectrumServiceError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class InvalidSpectrumProductError(SpectrumServiceError):
    pass


@dataclass
class SpectrumNotCachedError(SpectrumServiceError):
    pass


@dataclass
class SpectrumNoTableFoundError(SpectrumServiceError):
    available_hdus: list[dict[str, Any]]


def read_cached_spectrum(product_id: str) -> dict[str, Any]:
    """Read a cached JWST x1d/c1d FITS file and return plot-ready arrays.

    Data hygiene:
    - Rows with non-finite wavelength or flux are filtered out.
    - Non-finite error values are returned as null (when an error column exists).
    """
    filename = _validate_supported_spectrum_product_id(product_id)
    cached_path = Path(settings.jwst_cache_dir) / filename
    if not cached_path.exists():
        raise SpectrumNotCachedError("File not cached")

    try:
        return _parse_spectrum_fits(product_id=product_id, filename=filename, path=cached_path)
    except SpectrumServiceError:
        raise
    except Exception as exc:
        raise SpectrumServiceError(f"Failed to parse spectrum FITS: {exc}") from exc


def _validate_supported_spectrum_product_id(product_id: str) -> str:
    if not product_id.startswith(JWST_PRODUCT_PREFIX):
        raise InvalidSpectrumProductError("Only x1d/c1d FITS supported")

    filename = product_id.rsplit("/", 1)[-1].strip()
    if not filename:
        raise InvalidSpectrumProductError("Only x1d/c1d FITS supported")

    lower_filename = filename.lower()
    if not lower_filename.endswith(SUPPORTED_SUFFIXES):
        raise InvalidSpectrumProductError("Only x1d/c1d FITS supported")

    return filename


def _parse_spectrum_fits(*, product_id: str, filename: str, path: Path) -> dict[str, Any]:
    with fits.open(path, memmap=False) as hdul:
        segments: list[dict[str, Any]] = []
        available_hdus = _describe_hdus(hdul)

        for index, hdu in enumerate(hdul):
            if hdu.data is None or not hasattr(hdu.data, "names"):
                continue

            column_names = list(hdu.data.names or [])
            if not column_names:
                continue

            wavelength_col = _match_column_name(column_names, WAVELENGTH_COLUMN_CANDIDATES)
            flux_col = _match_column_name(column_names, FLUX_COLUMN_CANDIDATES)
            if wavelength_col is None or flux_col is None:
                continue

            error_col = _match_column_name(column_names, ERROR_COLUMN_CANDIDATES)
            wavelength_values = _flatten_values(hdu.data[wavelength_col])
            flux_values = _flatten_values(hdu.data[flux_col])
            error_values = _flatten_values(hdu.data[error_col]) if error_col else None

            wavelength, flux, error = _build_aligned_arrays(
                wavelength_values=wavelength_values,
                flux_values=flux_values,
                error_values=error_values,
            )

            segments.append(
                {
                    "label": _segment_label(index=index, hdu_name=getattr(hdu, "name", None)),
                    "hdu": {
                        "index": index,
                        "name": hdu.name if getattr(hdu, "name", None) is not None else None,
                    },
                    "units": {
                        "wavelength": _column_unit(hdu, wavelength_col),
                        "flux": _column_unit(hdu, flux_col),
                        "error": _column_unit(hdu, error_col) if error_col else None,
                    },
                    "data": {
                        "wavelength": wavelength,
                        "flux": flux,
                        "error": error,
                    },
                }
            )

        if not segments:
            raise SpectrumNoTableFoundError(
                "No wavelength/flux table found",
                available_hdus=available_hdus,
            )

        return {
            "product_id": product_id,
            "filename": filename,
            "segments": segments,
        }


def _describe_hdus(hdul: fits.HDUList) -> list[dict[str, Any]]:
    described: list[dict[str, Any]] = []
    for index, hdu in enumerate(hdul):
        columns = None
        if hdu.data is not None and hasattr(hdu.data, "names"):
            columns = list(hdu.data.names or [])
        described.append(
            {
                "index": index,
                "name": getattr(hdu, "name", None),
                "type": type(hdu).__name__,
                "columns": columns,
            }
        )
    return described


def _segment_label(*, index: int, hdu_name: str | None) -> str:
    if hdu_name:
        return str(hdu_name)
    return f"HDU {index}"


def _match_column_name(column_names: list[str], candidates: list[str]) -> str | None:
    lookup = {name.lower(): name for name in column_names}
    for candidate in candidates:
        matched = lookup.get(candidate.lower())
        if matched:
            return matched
    return None


def _flatten_values(values: Any) -> list[Any]:
    arr = np.ma.asarray(values)
    flat = np.ma.ravel(arr)
    return flat.tolist()


def _build_aligned_arrays(
    *,
    wavelength_values: list[Any],
    flux_values: list[Any],
    error_values: list[Any] | None,
) -> tuple[list[float], list[float], list[float | None] | None]:
    count = min(len(wavelength_values), len(flux_values))
    if error_values is not None:
        count = min(count, len(error_values))

    wavelengths: list[float] = []
    fluxes: list[float] = []
    errors: list[float | None] | None = [] if error_values is not None else None

    for i in range(count):
        w = _to_float_or_none(wavelength_values[i])
        f = _to_float_or_none(flux_values[i])
        if w is None or f is None:
            continue

        wavelengths.append(w)
        fluxes.append(f)

        if errors is not None and error_values is not None:
            errors.append(_to_float_or_none(error_values[i]))

    return wavelengths, fluxes, errors


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None

    if np.ma.is_masked(value):
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if not np.isfinite(numeric):
        return None
    return numeric


def _column_unit(hdu: fits.hdu.base.ExtensionHDU, column_name: str | None) -> str | None:
    if column_name is None or not hasattr(hdu, "columns"):
        return None
    try:
        column = hdu.columns[column_name]
    except Exception:
        return None
    unit = getattr(column, "unit", None)
    return str(unit) if unit else None
