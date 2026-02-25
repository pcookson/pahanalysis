from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.mast import router as mast_router
from app.api.routes.obs import router as obs_router
from app.api.routes.products import router as products_router
from app.api.routes.search import router as search_router
from app.config import settings
from app.db import init_db

app = FastAPI(title="JWST Spectrum Viewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mast_router, prefix="/api/mast", tags=["mast"])
app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(obs_router, prefix="/api", tags=["obs"])
app.include_router(products_router, prefix="/api", tags=["products"])


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
