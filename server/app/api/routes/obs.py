from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.services.product_service import (
    ProductServiceError,
    list_products_for_obs,
)


router = APIRouter()


@router.get("/obs/{obsid}/products", response_model=None)
def obs_products(obsid: str) -> Any:
    if not obsid.isdigit():
        raise HTTPException(status_code=400, detail="obsid must contain digits only")

    try:
        return list_products_for_obs(obsid)
    except ProductServiceError as exc:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": str(exc)},
        )
