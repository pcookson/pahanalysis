from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from astroquery.mast import Observations

from app.config import settings

JWST_PRODUCT_PREFIX = "mast:JWST/product/"


@dataclass
class DownloadServiceError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class InvalidProductIdError(DownloadServiceError):
    pass


@dataclass
class ProductAuthRequiredError(DownloadServiceError):
    pass


def download_product(product_id: str) -> dict[str, Any]:
    if not product_id.startswith(JWST_PRODUCT_PREFIX):
        raise InvalidProductIdError("product_id must start with 'mast:JWST/product/'")

    filename = _filename_from_product_id(product_id)
    cache_root = Path(settings.jwst_cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    local_path = cache_root / filename

    if local_path.exists():
        return _download_result(
            product_id=product_id,
            filename=filename,
            cached=True,
            path=local_path,
        )

    try:
        status, msg, _url = Observations.download_file(
            product_id,
            local_path=str(local_path),
            cache=True,
            verbose=False,
        )
    except PermissionError as exc:
        raise ProductAuthRequiredError(f"Permission denied while caching file: {exc}") from exc
    except Exception as exc:
        if _looks_like_auth_error(str(exc)):
            raise ProductAuthRequiredError(str(exc)) from exc
        raise DownloadServiceError(f"Failed to download product: {exc}") from exc

    if status == "ERROR":
        error_message = msg or "Unknown download error"
        if _looks_like_auth_error(error_message):
            raise ProductAuthRequiredError(error_message)
        raise DownloadServiceError(error_message)

    if not local_path.exists():
        raise DownloadServiceError("Download completed but file was not found in cache")

    return _download_result(
        product_id=product_id,
        filename=filename,
        cached=False,
        path=local_path,
    )


def _filename_from_product_id(product_id: str) -> str:
    filename = product_id.rsplit("/", 1)[-1].strip()
    if not filename:
        raise InvalidProductIdError("product_id must include a filename")
    if "/" in filename or filename in {".", ".."}:
        raise InvalidProductIdError("Invalid product_id filename component")
    return filename


def _download_result(
    *,
    product_id: str,
    filename: str,
    cached: bool,
    path: Path,
) -> dict[str, Any]:
    return {
        "product_id": product_id,
        "filename": filename,
        "cached": cached,
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
    }


def _looks_like_auth_error(message: str) -> bool:
    lowered = message.lower()
    auth_markers = (
        "403",
        "401",
        "forbidden",
        "unauthorized",
        "authentication",
        "login",
        "proprietary",
        "restricted",
    )
    return any(marker in lowered for marker in auth_markers)
