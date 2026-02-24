from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.download_service import JWST_PRODUCT_PREFIX


@dataclass
class CacheCatalogServiceError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def list_cached_products() -> list[dict[str, Any]]:
    cache_root = Path(settings.jwst_cache_dir)
    if not cache_root.exists():
        return []

    rows: list[dict[str, Any]] = []
    try:
        files = [p for p in cache_root.iterdir() if p.is_file()]
    except OSError as exc:
        raise CacheCatalogServiceError(f"Failed to scan cache directory: {exc}") from exc

    for path in sorted(files, key=lambda p: p.name.lower()):
        filename = path.name
        kind, is_plottable_candidate = _classify_product(filename)
        try:
            size = path.stat().st_size
        except OSError:
            size = None
        rows.append(
            {
                "product_id": f"{JWST_PRODUCT_PREFIX}{filename}",
                "productFilename": filename,
                "kind": kind,
                "is_plottable_candidate": is_plottable_candidate,
                "is_cached": True,
                "cached_path": str(path.resolve()),
                "cached_bytes": size,
                "size": size,
                "description": None,
            }
        )

    return rows


def _classify_product(filename: str | None) -> tuple[str, bool]:
    if not filename:
        return ("other", False)

    lower = filename.lower()
    if lower.endswith("_s3d.fits"):
        return ("cube3d", True)
    if lower.endswith(("_x1d.fits", "_c1d.fits")):
        return ("spectrum1d", True)
    return ("other", False)

