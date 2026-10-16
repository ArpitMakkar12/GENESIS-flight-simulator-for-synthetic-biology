"""Admin key: protects saved runs on the public site.

Anyone can run, view, compare and export simulations. Renaming or deleting
saved runs needs the admin key, sent in the X-Admin-Key header.

The key is the ADMIN_KEY environment variable on the server. When it is
empty (local development) nothing is locked.
"""

import hmac

from fastapi import APIRouter, Header, HTTPException

from app.config import settings

router = APIRouter()


def _key_ok(key: str | None) -> bool:
    if not settings.ADMIN_KEY:
        return True                      # no key set: nothing is locked
    if not key:
        return False
    # compare_digest takes the same time whether the first or the last
    # character is wrong, so the key cannot be guessed one letter at a time
    return hmac.compare_digest(key.encode(), settings.ADMIN_KEY.encode())


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """Add to an endpoint with dependencies=[Depends(require_admin)]."""
    if not _key_ok(x_admin_key):
        raise HTTPException(status_code=401, detail="Renaming and deleting saved runs needs the admin key.")


@router.get("/admin/status")
def admin_status(x_admin_key: str | None = Header(default=None)) -> dict:
    """locked: the server has an admin key. unlocked: this key may change saved runs."""
    return {"locked": bool(settings.ADMIN_KEY), "unlocked": _key_ok(x_admin_key)}