from astroquery.mast import Mast
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="JWST Spectrum Viewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/mast/ping")
def mast_ping():
    try:
        # Lightweight MAST service ping without running an observations search.
        Mast.session_info(verbose=False)
        return {"status": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": str(exc)},
        )
