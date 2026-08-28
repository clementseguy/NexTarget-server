"""Read-only administration endpoints (NT-049)."""

import hmac
from html import escape
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session, select

from ..core.config import get_settings
from ..models.user import User
from ..services.admin_auth import verify_admin_password
from ..services.database import get_session


router = APIRouter(prefix="/app/admin", tags=["admin"])
settings = get_settings()
basic_auth = HTTPBasic(auto_error=False)

ADMIN_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Content-Security-Policy": (
        "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'none'; img-src https:"
    ),
}


def require_admin(
    credentials: Optional[HTTPBasicCredentials] = Depends(basic_auth),
) -> None:
    """Require configured administrator credentials for an admin request.

    Args:
        credentials: Credentials supplied using HTTP Basic over HTTPS.

    Raises:
        HTTPException: If configuration is missing or credentials are invalid.
    """
    if not settings.admin_username or not settings.admin_password_hash:
        raise HTTPException(status_code=503, detail="Administration is not configured")

    username_matches = credentials is not None and hmac.compare_digest(
        credentials.username.encode("utf-8"),
        settings.admin_username.encode("utf-8"),
    )
    password_matches = credentials is not None and verify_admin_password(
        credentials.password,
        settings.admin_password_hash,
    )
    if not username_matches or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials",
            headers={"WWW-Authenticate": 'Basic realm="NexTarget Admin", charset="UTF-8"'},
        )


def _safe_avatar_url(url: Optional[str]) -> Optional[str]:
    """Return an escaped HTTPS avatar URL, or no URL when it is unsafe."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return escape(url, quote=True)


def _render_users(users: List[User]) -> str:
    """Render the read-only users table as a standalone HTML document."""
    rows = []
    for user in users:
        avatar_url = _safe_avatar_url(user.avatar_url)
        avatar = (
            f'<img src="{avatar_url}" alt="" width="40" height="40" '
            'loading="lazy" referrerpolicy="no-referrer">'
            if avatar_url
            else "—"
        )
        rows.append(
            "<tr>"
            f"<td><code>{escape(user.id)}</code></td>"
            f"<td>{escape(user.email)}</td>"
            f"<td>{escape(user.provider)}</td>"
            f"<td>{escape(user.display_name or '—')}</td>"
            f"<td>{'Active' if user.is_active else 'Inactive'}</td>"
            f"<td>{avatar}</td>"
            f"<td><time>{escape(user.created_at.isoformat())}</time></td>"
            "</tr>"
        )

    table_rows = "".join(rows) or '<tr><td colspan="7">No registered users.</td></tr>'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>NexTarget administration — Users</title>
</head>
<body>
  <main>
    <h1>Registered users</h1>
    <p>{len(users)} user(s). Read-only view.</p>
    <table>
      <thead><tr><th>Internal ID</th><th>Email</th><th>Provider</th><th>Display name</th><th>Status</th><th>Avatar</th><th>Created at (UTC)</th></tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
  </main>
</body>
</html>"""


@router.get("/users", response_class=HTMLResponse, include_in_schema=False)
def list_users(
    _: None = Depends(require_admin),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Display registered users without exposing mutation operations."""
    users = list(session.exec(select(User).order_by(User.created_at.desc())).all())
    return HTMLResponse(_render_users(users), headers=ADMIN_HEADERS)
