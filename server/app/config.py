from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    mast_default_search_radius_arcsec: float = float(
        os.getenv("MAST_DEFAULT_SEARCH_RADIUS_ARCSEC", "1.0")
    )
    mast_ping_ra_deg: float = float(os.getenv("MAST_PING_RA_DEG", "10.6847083"))
    mast_ping_dec_deg: float = float(os.getenv("MAST_PING_DEC_DEG", "41.26875"))


settings = Settings()
