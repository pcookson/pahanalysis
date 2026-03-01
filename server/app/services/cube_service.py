from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits

from app.config import settings
from app.services.download_service import JWST_PRODUCT_PREFIX

CUBE_SUFFIX = "_s3d.fits"


@dataclass
class CubeServiceError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class InvalidCubeProductError(CubeServiceError):
    pass


@dataclass
class CubeNotCachedError(CubeServiceError):
    pass


def get_cube_spatial_map(
    product_id: str,
    wave_min: float | None = None,
    wave_max: float | None = None,
) -> dict[str, Any]:
    """Collapse a 3D IFU cube to a 2D spatial map via nanmedian over a wavelength range."""
    filename = _validate_cube_product_id(product_id)
    cached_path = Path(settings.jwst_cache_dir) / filename
    if not cached_path.exists():
        raise CubeNotCachedError("Cube file not cached")
    try:
        return _read_spatial_map(product_id, filename, cached_path, wave_min, wave_max)
    except CubeServiceError:
        raise
    except Exception as exc:
        raise CubeServiceError(f"Failed to read cube FITS: {exc}") from exc


def extract_cube_spectrum(
    product_id: str,
    center_x: float,
    center_y: float,
    radius: float,
) -> dict[str, Any]:
    """Sum spaxels within a circular aperture to produce a 1D spectrum.

    Returns the same segments format as spectrum_service.read_cached_spectrum,
    making it drop-in compatible with the existing plot and PAH scoring machinery.
    """
    filename = _validate_cube_product_id(product_id)
    cached_path = Path(settings.jwst_cache_dir) / filename
    if not cached_path.exists():
        raise CubeNotCachedError("Cube file not cached")
    try:
        return _extract_aperture_spectrum(
            product_id, filename, cached_path, center_x, center_y, radius
        )
    except CubeServiceError:
        raise
    except Exception as exc:
        raise CubeServiceError(f"Failed to extract cube spectrum: {exc}") from exc


def _validate_cube_product_id(product_id: str) -> str:
    if not product_id.startswith(JWST_PRODUCT_PREFIX):
        raise InvalidCubeProductError("Only _s3d cube FITS products are supported")
    filename = product_id.rsplit("/", 1)[-1].strip()
    if not filename or not filename.lower().endswith(CUBE_SUFFIX):
        raise InvalidCubeProductError("Only _s3d cube FITS products are supported")
    return filename


def _find_sci_hdu(hdul: fits.HDUList) -> fits.ImageHDU:
    """Return the first 3D image HDU, checking common JWST extension names first."""
    for name in ("SCI", "FLUX", "DATA"):
        try:
            hdu = hdul[name]
        except (KeyError, IndexError):
            continue
        if hdu.data is not None and getattr(hdu.data, "ndim", 0) == 3:
            return hdu  # type: ignore[return-value]

    # Fallback: first extension with a 3D array
    for hdu in hdul:
        if hdu.data is not None and getattr(hdu.data, "ndim", 0) == 3:
            return hdu  # type: ignore[return-value]

    raise CubeServiceError("No 3D data array found in cube FITS file")


def _find_err_hdu(hdul: fits.HDUList, sci_shape: tuple[int, ...]) -> fits.ImageHDU | None:
    """Return the error extension if shape-compatible, else None."""
    for name in ("ERR", "ERROR", "SIGMA"):
        try:
            hdu = hdul[name]
        except (KeyError, IndexError):
            continue
        if hdu.data is not None and hdu.data.shape == sci_shape:
            return hdu  # type: ignore[return-value]
    return None


def _reconstruct_wavelength(header: fits.Header, nwave: int) -> tuple[np.ndarray, str]:
    """Build wavelength array from WCS header keywords.

    Returns (wavelength_um, unit_label). Falls back to pixel indices if WCS is
    absent or produces non-positive values.
    """
    cdelt3 = float(header.get("CD3_3") or header.get("CDELT3", 1.0))
    crpix3 = float(header.get("CRPIX3", 1.0))
    crval3 = float(header.get("CRVAL3", 0.0))
    cunit3 = str(header.get("CUNIT3", "um")).strip().lower()

    pixel_indices = np.arange(nwave, dtype=float)
    wavelength = crval3 + (pixel_indices - (crpix3 - 1.0)) * cdelt3

    if cunit3 in ("m", "meter", "meters"):
        wavelength = wavelength * 1e6
    elif cunit3 in ("nm", "nanometer", "nanometers"):
        wavelength = wavelength * 1e-3
    elif cunit3 in ("angstrom", "angstroms", "aa"):
        wavelength = wavelength * 1e-4

    if not np.all(np.isfinite(wavelength)) or float(wavelength.max()) <= 0:
        return np.arange(nwave, dtype=float), "pixels"

    return wavelength, "um"


def _pixel_scale_arcsec(header: fits.Header) -> float | None:
    for key in ("CDELT1", "CD1_1"):
        val = header.get(key)
        if val is not None:
            return abs(float(val)) * 3600.0
    return None


def _read_spatial_map(
    product_id: str,
    filename: str,
    path: Path,
    wave_min: float | None,
    wave_max: float | None,
) -> dict[str, Any]:
    with fits.open(path, memmap=False) as hdul:
        sci_hdu = _find_sci_hdu(hdul)
        data = sci_hdu.data.astype(np.float64)  # (nwave, ny, nx)
        nwave, ny, nx = data.shape

        wavelength, wave_unit = _reconstruct_wavelength(sci_hdu.header, nwave)
        flux_unit = str(sci_hdu.header.get("BUNIT", "")) or None
        pixel_scale = _pixel_scale_arcsec(sci_hdu.header)

        wave_filter = np.ones(nwave, dtype=bool)
        if wave_min is not None:
            wave_filter &= wavelength >= wave_min
        if wave_max is not None:
            wave_filter &= wavelength <= wave_max
        if not wave_filter.any():
            wave_filter = np.ones(nwave, dtype=bool)

        spatial_map = np.nanmedian(data[wave_filter, :, :], axis=0)  # (ny, nx)
        wave_used = wavelength[wave_filter]

        map_list = [
            [None if not np.isfinite(v) else float(v) for v in row]
            for row in spatial_map
        ]

        return {
            "product_id": product_id,
            "filename": filename,
            "shape": {"ny": ny, "nx": nx, "nwave": nwave},
            "wavelength_range": {
                "min": float(wavelength.min()),
                "max": float(wavelength.max()),
                "unit": wave_unit,
            },
            "wave_min_used": float(wave_used.min()),
            "wave_max_used": float(wave_used.max()),
            "pixel_scale_arcsec": pixel_scale,
            "flux_unit": flux_unit,
            "map": map_list,
        }


def _extract_aperture_spectrum(
    product_id: str,
    filename: str,
    path: Path,
    center_x: float,
    center_y: float,
    radius: float,
) -> dict[str, Any]:
    with fits.open(path, memmap=False) as hdul:
        sci_hdu = _find_sci_hdu(hdul)
        sci_data = sci_hdu.data.astype(np.float64)  # (nwave, ny, nx)
        nwave, ny, nx = sci_data.shape

        err_hdu = _find_err_hdu(hdul, sci_data.shape)
        err_data = err_hdu.data.astype(np.float64) if err_hdu is not None else None

        wavelength, wave_unit = _reconstruct_wavelength(sci_hdu.header, nwave)
        flux_unit = str(sci_hdu.header.get("BUNIT", "")) or None

        # Circular aperture mask in pixel space
        yy, xx = np.mgrid[0:ny, 0:nx]
        dist = np.sqrt(
            (xx.astype(float) - center_x) ** 2 + (yy.astype(float) - center_y) ** 2
        )
        mask = dist <= radius  # (ny, nx)

        if not mask.any():
            raise CubeServiceError(
                f"Aperture at ({center_x:.1f}, {center_y:.1f}) r={radius:.1f}px "
                "falls entirely outside the cube spatial extent"
            )

        # Vectorised aperture sum over spatial axes
        mask_3d = mask[np.newaxis, :, :]  # (1, ny, nx) broadcasts with (nwave, ny, nx)
        flux = np.nansum(np.where(mask_3d, sci_data, np.nan), axis=(1, 2))  # (nwave,)

        error: np.ndarray | None = None
        if err_data is not None:
            error = np.sqrt(
                np.nansum(np.where(mask_3d, err_data**2, np.nan), axis=(1, 2))
            )

        finite = np.isfinite(wavelength) & np.isfinite(flux)
        wavelength_out = wavelength[finite].tolist()
        flux_out = flux[finite].tolist()
        error_out: list[float | None] | None = None
        if error is not None:
            error_out = [
                None if not np.isfinite(v) else float(v) for v in error[finite]
            ]

        n_spaxels = int(mask.sum())
        label = (
            f"Aperture x={center_x:.1f} y={center_y:.1f} "
            f"r={radius:.1f}px ({n_spaxels} spaxels)"
        )

        return {
            "product_id": product_id,
            "filename": filename,
            "segments": [
                {
                    "label": label,
                    "hdu": {"index": 1, "name": getattr(sci_hdu, "name", "SCI")},
                    "units": {
                        "wavelength": wave_unit,
                        "flux": flux_unit,
                        "error": flux_unit if error_out is not None else None,
                    },
                    "data": {
                        "wavelength": wavelength_out,
                        "flux": flux_out,
                        "error": error_out,
                    },
                    "extraction": {
                        "center_x": center_x,
                        "center_y": center_y,
                        "radius_px": radius,
                        "n_spaxels": n_spaxels,
                    },
                }
            ],
        }
