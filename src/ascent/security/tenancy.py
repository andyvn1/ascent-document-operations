"""Authentication placeholder and tenant-scoping dependency.

Real authentication (passwords, sessions, signed tokens) is a separate,
larger feature and is not built here. This module closes a narrower
gap: every request must resolve to a *verified* user record, so the
tenant identity comes from a database lookup, never from a value the
client supplies directly -- see docs/architecture/api-specification.md
("the tenant is derived from the auth context, never from a
client-supplied parameter").

The placeholder mechanism is a required `X-User-Id` header naming an
existing user row. This does not prevent a client that already knows
another tenant's user ID from impersonating them -- there is no
password or token check. It only removes the ability to claim an
arbitrary, unverified tenant_id, which is the gap this task targets.
Replacing this with real authentication later should only require
changing this function's implementation, not any endpoint's signature.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ascent.shared.db import get_db
from ascent.shared.models import User


@dataclass(frozen=True)
class AuthContext:
    user_id: uuid.UUID
    tenant_id: uuid.UUID


def get_current_actor(
    db: Annotated[Session, Depends(get_db)],
    x_user_id: Annotated[uuid.UUID | None, Header()] = None,
) -> AuthContext:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header is required",
        )

    user = db.get(User, x_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown user",
        )

    return AuthContext(user_id=user.id, tenant_id=user.tenant_id)