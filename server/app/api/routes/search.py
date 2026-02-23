from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.search_service import SearchServiceError, search_jwst_by_target


router = APIRouter()


@router.get("/search", response_model=None)
def search(
    target: str = Query(..., description="Target name to resolve via MAST"),
    radiusArcsec: float | None = Query(
        None, description="Search radius in arcseconds (0 < radius <= 3600)"
    ),
) -> Any:
    normalized_target = target.strip()
    if not normalized_target:
        raise HTTPException(status_code=400, detail="target must not be blank")

    radius_arcsec = (
        settings.mast_default_search_radius_arcsec
        if radiusArcsec is None
        else radiusArcsec
    )
    if radius_arcsec <= 0 or radius_arcsec > 3600:
        raise HTTPException(
            status_code=400, detail="radiusArcsec must be > 0 and <= 3600"
        )

    try:
        return search_jwst_by_target(
            target=normalized_target,
            radius_arcsec=radius_arcsec,
        )
    except SearchServiceError as exc:
        payload: dict[str, Any] = {"status": "error", "message": str(exc)}
        if exc.details:
            payload["details"] = exc.details
        return JSONResponse(status_code=502, content=payload)
