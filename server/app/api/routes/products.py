from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.download_service import (
    DownloadServiceError,
    InvalidProductIdError,
    ProductAuthRequiredError,
    download_product,
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
