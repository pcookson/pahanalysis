from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic import field_validator

from app.db import get_pah_override, upsert_pah_override

from app.services.download_service import (
    DownloadServiceError,
    InvalidProductIdError,
    ProductAuthRequiredError,
    download_product,
)
from app.services.spectrum_service import (
    InvalidSpectrumProductError,
    SpectrumNoTableFoundError,
    SpectrumNotCachedError,
    SpectrumServiceError,
    read_cached_spectrum,
)
from app.services.pah_score_service import (
    PahScoreServiceError,
    get_or_compute_pah_score,
)


router = APIRouter()


class ProductDownloadRequest(BaseModel):
    product_id: str


class ProductAnnotationRequest(BaseModel):
    product_id: str
    user_label: Literal["yes", "no", "unknown"]
    user_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    note: str | None = None

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("product_id is required")
        return value


@router.post("/products/download", response_model=None)
def download_product_endpoint(payload: ProductDownloadRequest) -> Any:
    try:
        return download_product(payload.product_id)
    except InvalidProductIdError as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(exc)},
        )
    except ProductAuthRequiredError as exc:
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "requires_auth": True,
                "message": str(exc),
            },
        )
    except DownloadServiceError as exc:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": str(exc)},
        )


@router.get("/products/spectrum", response_model=None)
def get_product_spectrum(product_id: str = Query(...)) -> Any:
    try:
        return read_cached_spectrum(product_id)
    except InvalidSpectrumProductError as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(exc)},
        )
    except SpectrumNotCachedError as exc:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": str(exc)},
        )
    except SpectrumNoTableFoundError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "message": str(exc),
                "available_hdus": exc.available_hdus,
            },
        )
    except SpectrumServiceError as exc:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": str(exc)},
        )


@router.get("/products/pah_score", response_model=None)
def get_product_pah_score(
    product_id: str = Query(...),
    force: bool = Query(False),
) -> Any:
    try:
        return get_or_compute_pah_score(product_id, force=force)
    except InvalidSpectrumProductError as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(exc)},
        )
    except SpectrumNotCachedError as exc:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": str(exc)},
        )
    except SpectrumNoTableFoundError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "message": str(exc),
                "available_hdus": exc.available_hdus,
            },
        )
    except (PahScoreServiceError, SpectrumServiceError) as exc:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": str(exc)},
        )


@router.get("/products/annotation", response_model=None)
def get_product_annotation(product_id: str = Query(...)) -> Any:
    product_id = product_id.strip()
    if not product_id:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "product_id is required"},
        )
    return get_pah_override(product_id)


@router.put("/products/annotation", response_model=None)
def put_product_annotation(payload: ProductAnnotationRequest) -> Any:
    return upsert_pah_override(
        product_id=payload.product_id,
        user_label=payload.user_label,
        user_confidence=payload.user_confidence,
        note=payload.note,
    )
