from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.db import get_pah_score, upsert_pah_score
from app.services.spectrum_service import read_cached_spectrum

PAH_SCORE_VERSION = "heuristic_v1"

# Heuristic window half-widths (micron): broader windows for the broad 7.7 and 16.4 complexes.
PAH_BANDS_UM: list[tuple[float, float]] = [
    (6.2, 0.15),
    (7.7, 0.30),
    (8.6, 0.15),
    (11.2, 0.20),
    (12.7, 0.20),
    (16.4, 0.30),
]

_numpy_trapezoid = getattr(np, "trapezoid", None)
_numpy_trapz = getattr(np, "trapz", None)


@dataclass
class PahScoreServiceError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def get_or_compute_pah_score(product_id: str, *, force: bool = False) -> dict[str, Any]:
    if not force:
        cached_score = get_pah_score(product_id, PAH_SCORE_VERSION)
        if cached_score is not None:
            return cached_score

    spectrum = read_cached_spectrum(product_id)
    score = _score_spectrum(product_id=product_id, spectrum=spectrum)
    upsert_pah_score(score)
    return score


def _score_spectrum(*, product_id: str, spectrum: dict[str, Any]) -> dict[str, Any]:
    segments = spectrum.get("segments") if isinstance(spectrum, dict) else None
    if not isinstance(segments, list):
        raise PahScoreServiceError("Invalid spectrum payload: missing segments")

    evidence: dict[str, dict[str, Any]] = {}
    bands_considered: list[float] = []
    bands_missing: list[float] = []
    positive_snrs: list[float] = []

    normalized_segments = [_normalize_segment(seg) for seg in segments]

    for center, half_width in PAH_BANDS_UM:
        best = None
        for segment in normalized_segments:
            candidate = _score_band_for_segment(
                center=center,
                half_width=half_width,
                wavelength=segment["wavelength"],
                flux=segment["flux"],
                error=segment["error"],
            )
            if candidate is None:
                continue
            if best is None or candidate["snr"] > best["snr"]:
                best = candidate

        key = _band_key(center)
        if best is None:
            bands_missing.append(center)
            continue

        bands_considered.append(center)
        evidence[key] = {
            "snr": round(float(best["snr"]), 4),
            "excess_flux": round(float(best["excess_flux"]), 8),
        }
        positive_snrs.append(max(float(best["snr"]), 0.0))

    coverage = {
        "bands_considered": bands_considered,
        "bands_missing": bands_missing,
    }

    computed_at = datetime.now(timezone.utc).isoformat()
    if not bands_considered:
        return {
            "product_id": product_id,
            "score_version": PAH_SCORE_VERSION,
            "confidence": 0.0,
            "grade": "LOW",
            "coverage": coverage,
            "evidence": evidence,
            "computed_at": computed_at,
            "notes": "insufficient wavelength coverage",
        }

    snr_max = max(positive_snrs) if positive_snrs else 0.0
    snr_count_ge3 = sum(1 for snr in positive_snrs if snr >= 3.0)
    confidence = _confidence_from_band_stats(
        snr_max=snr_max,
        snr_count_ge3=snr_count_ge3,
        bands_considered_count=len(bands_considered),
    )
    grade = "HIGH" if confidence >= 0.75 else "MED" if confidence >= 0.4 else "LOW"
    notes = (
        f"heuristic bands considered={len(bands_considered)} "
        f"snr_max={snr_max:.2f} snr_count_ge3={snr_count_ge3}"
    )

    return {
        "product_id": product_id,
        "score_version": PAH_SCORE_VERSION,
        "confidence": round(confidence, 4),
        "grade": grade,
        "coverage": coverage,
        "evidence": evidence,
        "computed_at": computed_at,
        "notes": notes,
    }


def _normalize_segment(segment: dict[str, Any]) -> dict[str, np.ndarray]:
    data = segment.get("data") if isinstance(segment, dict) else {}
    wavelength = np.asarray(data.get("wavelength") or [], dtype=float)
    flux = np.asarray(data.get("flux") or [], dtype=float)
    error_raw = data.get("error")
    error = None
    if isinstance(error_raw, list):
        # `None` values become nan and are filtered later during band calculations.
        error = np.asarray(
            [np.nan if value is None else float(value) for value in error_raw],
            dtype=float,
        )
    return {
        "wavelength": wavelength,
        "flux": flux,
        "error": error,
    }


def _score_band_for_segment(
    *,
    center: float,
    half_width: float,
    wavelength: np.ndarray,
    flux: np.ndarray,
    error: np.ndarray | None,
) -> dict[str, float] | None:
    if wavelength.size < 5 or flux.size < 5:
        return None

    feature_min = center - half_width
    feature_max = center + half_width
    left_min = center - 3 * half_width
    left_max = center - 2 * half_width
    right_min = center + 2 * half_width
    right_max = center + 3 * half_width

    if wavelength.min() > left_min or wavelength.max() < right_max:
        return None

    finite_mask = np.isfinite(wavelength) & np.isfinite(flux)
    if finite_mask.sum() < 5:
        return None
    wavelength = wavelength[finite_mask]
    flux = flux[finite_mask]

    if error is not None and error.shape[0] == finite_mask.shape[0]:
        error = error[finite_mask]
    else:
        error = None

    order = np.argsort(wavelength)
    wavelength = wavelength[order]
    flux = flux[order]
    if error is not None:
        error = error[order]

    feature_mask = (wavelength >= feature_min) & (wavelength <= feature_max)
    left_mask = (wavelength >= left_min) & (wavelength <= left_max)
    right_mask = (wavelength >= right_min) & (wavelength <= right_max)

    if feature_mask.sum() < 3 or left_mask.sum() < 2 or right_mask.sum() < 2:
        return None

    wf = wavelength[feature_mask]
    ff = flux[feature_mask]

    left_mean = float(np.mean(flux[left_mask]))
    right_mean = float(np.mean(flux[right_mask]))

    # Linear baseline across the feature window from left/right continuum means.
    baseline = left_mean + (wf - feature_min) * ((right_mean - left_mean) / (feature_max - feature_min))
    residual = ff - baseline
    excess_flux = float(_integrate_trapezoid(residual, wf))

    sigma_area = _estimate_integrated_noise(
        feature_wavelength=wf,
        feature_error=error[feature_mask] if error is not None else None,
        continuum_flux=flux[left_mask | right_mask],
    )
    if sigma_area is None or sigma_area <= 0:
        return None

    return {
        "snr": excess_flux / sigma_area,
        "excess_flux": excess_flux,
    }


def _estimate_integrated_noise(
    *,
    feature_wavelength: np.ndarray,
    feature_error: np.ndarray | None,
    continuum_flux: np.ndarray,
) -> float | None:
    weights = _trapezoid_weights(feature_wavelength)
    if weights.size == 0:
        return None

    if feature_error is not None:
        sigma = np.asarray(feature_error, dtype=float)
        if sigma.shape[0] == weights.shape[0]:
            sigma = np.where(np.isfinite(sigma) & (sigma > 0), sigma, np.nan)
            if np.isfinite(sigma).any():
                sigma_filled = sigma.copy()
                median_sigma = np.nanmedian(sigma_filled)
                if not np.isfinite(median_sigma) or median_sigma <= 0:
                    median_sigma = 0.0
                sigma_filled = np.where(np.isfinite(sigma_filled), sigma_filled, median_sigma)
                variance = float(np.sum((weights * sigma_filled) ** 2))
                if variance > 0:
                    return variance ** 0.5

    continuum = np.asarray(continuum_flux, dtype=float)
    continuum = continuum[np.isfinite(continuum)]
    if continuum.size < 3:
        return None

    mad = np.median(np.abs(continuum - np.median(continuum)))
    sigma_flux = 1.4826 * mad
    if not np.isfinite(sigma_flux) or sigma_flux <= 0:
        std = float(np.std(continuum))
        sigma_flux = std if np.isfinite(std) else 0.0
    if sigma_flux <= 0:
        return None

    variance = float(np.sum((weights * sigma_flux) ** 2))
    if variance <= 0:
        return None
    return variance ** 0.5


def _trapezoid_weights(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size < 2:
        return np.asarray([], dtype=float)

    dx = np.diff(x)
    if not np.all(np.isfinite(dx)) or np.any(dx <= 0):
        return np.asarray([], dtype=float)

    weights = np.zeros_like(x, dtype=float)
    weights[0] = dx[0] / 2.0
    weights[-1] = dx[-1] / 2.0
    if x.size > 2:
        weights[1:-1] = (dx[:-1] + dx[1:]) / 2.0
    return weights


def _integrate_trapezoid(y: np.ndarray, x: np.ndarray) -> float:
    if callable(_numpy_trapezoid):
        return float(_numpy_trapezoid(y, x))
    if callable(_numpy_trapz):
        return float(_numpy_trapz(y, x))
    raise PahScoreServiceError("NumPy trapezoid integration function unavailable")


def _confidence_from_band_stats(
    *,
    snr_max: float,
    snr_count_ge3: int,
    bands_considered_count: int,
) -> float:
    # Deterministic threshold map tuned for a conservative v1 heuristic.
    if snr_max < 1.5:
        confidence = 0.1
    elif snr_max < 3.0:
        confidence = 0.3
    elif snr_max < 5.0:
        confidence = 0.55
    elif snr_max < 8.0:
        confidence = 0.75
    else:
        confidence = 0.9

    if snr_count_ge3 >= 2:
        confidence += 0.05
    if snr_count_ge3 >= 3:
        confidence += 0.05
    if bands_considered_count == 1:
        confidence -= 0.1

    return max(0.0, min(1.0, confidence))


def _band_key(center: float) -> str:
    return f"{center:.1f}"
