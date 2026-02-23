from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.mast import router as mast_router
from app.api.routes.obs import router as obs_router
from app.api.routes.search import router as search_router

app = FastAPI(title="JWST Spectrum Viewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mast_router, prefix="/api/mast", tags=["mast"])
app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(obs_router, prefix="/api", tags=["obs"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
