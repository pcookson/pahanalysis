from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.mast_service import ping_mast


router = APIRouter()


@router.get("/ping")
def mast_ping():
    try:
        ping_mast()
        return {"status": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": str(exc)},
        )
