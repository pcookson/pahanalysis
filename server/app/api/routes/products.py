from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


router = APIRouter()


class ProductDownloadRequest(BaseModel):
    product_id: str


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
