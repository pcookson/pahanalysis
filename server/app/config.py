from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_repo_path(raw_path: str) -> str:
    path = Path(raw_path)
    if path.is_absolute():
        return str(path)
    return str((REPO_ROOT / path).resolve())


@dataclass(frozen=True)
class Settings:
    cors_allow_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")
        .split(",")
        if origin.strip()
    )
    mast_default_search_radius_arcsec: float = float(
        os.getenv("MAST_DEFAULT_SEARCH_RADIUS_ARCSEC", "1.0")
    )
    mast_ping_ra_deg: float = float(os.getenv("MAST_PING_RA_DEG", "10.6847083"))
    mast_ping_dec_deg: float = float(os.getenv("MAST_PING_DEC_DEG", "41.26875"))
    jwst_cache_dir: str = _resolve_repo_path(
        os.getenv("JWST_CACHE_DIR", "server/.cache/jwst")
    )
    sqlite_db_path: str = _resolve_repo_path(
        os.getenv("SQLITE_DB_PATH", "data/app.db")
    )


settings = Settings()
