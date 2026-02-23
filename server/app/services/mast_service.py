from astroquery.mast import Mast


def ping_mast() -> None:
    """Lightweight MAST connectivity check without an observations search."""
    Mast.session_info(verbose=False)
