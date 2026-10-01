"""Browser-compatible version of the X-User-Id auth placeholder
(security/tenancy.py).

That mechanism works for API clients that explicitly set a header, but
not for a human clicking through a dashboard: a plain <a href> or typed
URL never attaches a custom header. A cookie is the browser-native
equivalent -- set once (the login route in routes.py), sent
automatically on every subsequent request. The identity check itself
is identical to the header version: a verified lookup against the
users table, never a value trusted outright. This is the same
placeholder, in the same spirit, just carried differently -- not a
step toward real session authentication. No expiration is set on the
cookie (session-only): it's cleared when the browser closes, matching
the lack of any real session-invalidation story behind it either way.
"""

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ascent.security.tenancy import AuthContext
from ascent.shared.db import get_db
from ascent.shared.models import User

COOKIE_NAME = "user_id"


def get_current_web_actor(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[uuid.UUID | None, Cookie(alias=COOKIE_NAME)] = None,
) -> AuthContext:
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})

    return AuthContext(user_id=user.id, tenant_id=user.tenant_id)
