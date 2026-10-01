"""Review dashboard web UI (TASK-025).

Server-rendered HTML (Jinja2) + HTMX for the one interaction that
benefits from a partial update (correcting a field), chosen over a
React/Vite SPA specifically to avoid introducing Node tooling, a build
step, and CORS configuration into a project that has none of that
today -- see docs/architecture/api-specification.md's Week 5 review
for the full tradeoff.

Every mutating route here calls the exact same business-logic
functions the JSON API uses (correct_field, approve_document,
reject_document) -- this is a second *presentation* layer over the
same rules, not a second copy of them.

Auth is the cookie-based sibling of security/tenancy.py's X-User-Id
placeholder (see auth.py): identification, not real authentication --
see that module's docstring.
"""

import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.routes.documents import (
    UnsupportedFileTypeError,
    UploadTooLargeError,
    get_storage,
    handle_upload,
)
from apps.web.auth import COOKIE_NAME, get_current_web_actor
from ascent.documents.corrections import (
    DocumentNotInReviewError,
    FieldNotFoundError,
    correct_field,
)
from ascent.documents.models import ExtractedField
from ascent.documents.repository import (
    DocumentNotFoundError,
    InvalidTransitionError,
    get_document,
    list_extracted_fields,
    list_review_queue,
)
from ascent.documents.storage import ObjectStorage
from ascent.documents.workflow import (
    MissingRejectionCommentError,
    approve_document,
    reject_document,
)
from ascent.security.tenancy import AuthContext
from ascent.shared.config import Settings, get_settings
from ascent.shared.db import get_db
from ascent.shared.models import Tenant, User

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Below this, a field is highlighted as needing scrutiny. Matches the
# gap between invoices/validation.py's _PRESENT_CONFIDENCE (0.95) and
# _INCONSISTENT_CONFIDENCE (0.4) tiers -- anything under 0.5 is either
# "flagged as inconsistent" or "missing" by that scoring, never a
# field that scored cleanly.
_LOW_CONFIDENCE_THRESHOLD = 0.5


def _render_detail(
    request: Request,
    *,
    db: Session,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    document = get_document(db, tenant_id=tenant_id, document_id=document_id)
    if document is None:
        return templates.TemplateResponse(request, "not_found.html", {}, status_code=404)

    fields = list_extracted_fields(db, tenant_id=tenant_id, document_id=document_id)
    return templates.TemplateResponse(
        request,
        "detail.html",
        {
            "document": document,
            "fields": fields,
            "error": error,
            "low_confidence_threshold": _LOW_CONFIDENCE_THRESHOLD,
        },
        status_code=status_code,
    )


def _field_row_context(field: ExtractedField, *, document_id: uuid.UUID) -> dict[str, Any]:
    return {
        "field": field,
        "document_id": document_id,
        "low_confidence_threshold": _LOW_CONFIDENCE_THRESHOLD,
    }


@router.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url="/review", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    users = list(db.scalars(select(User).order_by(User.email)))
    return templates.TemplateResponse(request, "login.html", {"users": users})


@router.post("/login")
def login_submit(user_id: Annotated[uuid.UUID, Form()]) -> RedirectResponse:
    response = RedirectResponse(url="/review", status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=str(user_id), httponly=True)
    return response


@router.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "signup.html", {})


@router.post("/signup", response_class=HTMLResponse, response_model=None)
def signup_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    # Both default to "" rather than being required -- same FastAPI
    # quirk as review_reject's comment field: a required Form(str)
    # submitted empty is treated as missing entirely (a raw 422)
    # rather than reaching this function's own validation.
    email: Annotated[str, Form()] = "",
    company_name: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    email = email.strip()
    company_name = company_name.strip()

    if not email or not company_name:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"error": "Both email and company name are required."},
            status_code=422,
        )

    # The only uniqueness that actually matters is the email -- User.email
    # is already unique at the database level (one email, one tenant,
    # always -- see shared/models.py). Tenant.name is just a display
    # label with nothing keyed off it for identity or security, so two
    # tenants sharing a name is harmless and not checked for here.
    existing_user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if existing_user is not None:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"error": "That email is already registered -- log in instead."},
            status_code=409,
        )

    tenant = Tenant(name=company_name)
    db.add(tenant)
    db.flush()

    user = User(tenant_id=tenant.id, email=email, role="reviewer")
    db.add(user)
    db.commit()

    response = RedirectResponse(url="/review", status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=str(user.id), httponly=True)
    return response


@router.get("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/upload", response_class=HTMLResponse)
def upload_form(
    request: Request, actor: Annotated[AuthContext, Depends(get_current_web_actor)]
) -> HTMLResponse:
    return templates.TemplateResponse(request, "upload.html", {})


@router.post("/upload", response_model=None)
async def upload_submit(
    request: Request,
    file: UploadFile,
    actor: Annotated[AuthContext, Depends(get_current_web_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse | RedirectResponse:
    """Calls the exact same handle_upload() the JSON API's
    POST /api/v1/documents uses (apps/api/routes/documents.py) -- this
    is a second entry point into the same upload logic, not a copy of
    it, same principle as every other mutating route in this file.
    """
    try:
        document = await handle_upload(
            file=file, actor=actor, settings=settings, storage=storage, db=db
        )
    except UploadTooLargeError:
        return templates.TemplateResponse(
            request,
            "upload.html",
            {"error": "File exceeds the maximum upload size."},
            status_code=413,
        )
    except UnsupportedFileTypeError:
        return templates.TemplateResponse(
            request,
            "upload.html",
            {"error": "Only PDF and image (JPEG/PNG) files are accepted."},
            status_code=415,
        )

    db.commit()
    return RedirectResponse(url=f"/review/{document.id}", status_code=303)


@router.get("/review", response_class=HTMLResponse)
def review_queue(
    request: Request,
    actor: Annotated[AuthContext, Depends(get_current_web_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    documents, total = list_review_queue(db, tenant_id=actor.tenant_id, page=1, page_size=50)
    return templates.TemplateResponse(
        request, "queue.html", {"documents": documents, "total": total}
    )


@router.get("/review/{document_id}", response_class=HTMLResponse)
def review_detail(
    request: Request,
    document_id: uuid.UUID,
    actor: Annotated[AuthContext, Depends(get_current_web_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    return _render_detail(request, db=db, tenant_id=actor.tenant_id, document_id=document_id)


@router.patch("/review/{document_id}/fields/{field_name}", response_class=HTMLResponse)
def review_correct_field(
    request: Request,
    document_id: uuid.UUID,
    field_name: str,
    corrected_value: Annotated[str, Form()],
    actor: Annotated[AuthContext, Depends(get_current_web_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    try:
        field = correct_field(
            db,
            tenant_id=actor.tenant_id,
            document_id=document_id,
            field_name=field_name,
            corrected_value=corrected_value,
            user_id=actor.user_id,
        )
    except (DocumentNotFoundError, DocumentNotInReviewError, FieldNotFoundError) as exc:
        # No rollback here: these are guard-clause exceptions raised
        # before any mutation happens, so there's nothing uncommitted
        # to discard -- matching apps/api/routes/documents.py's
        # correct_document_field, which doesn't roll back either.
        # HTMX is swapping this response into the <tr> that was there
        # before (hx-swap="outerHTML") -- so the error response must
        # still be a valid <tr>, just carrying the error message
        # instead of the (unsaved) correction.
        return templates.TemplateResponse(
            request,
            "_field_row_error.html",
            {"field_name": field_name, "document_id": document_id, "error": str(exc)},
            status_code=409,
        )

    db.commit()
    return templates.TemplateResponse(
        request, "_field_row.html", _field_row_context(field, document_id=document_id)
    )


@router.post("/review/{document_id}/approve", response_class=HTMLResponse, response_model=None)
def review_approve(
    request: Request,
    document_id: uuid.UUID,
    actor: Annotated[AuthContext, Depends(get_current_web_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse | RedirectResponse:
    document = get_document(db, tenant_id=actor.tenant_id, document_id=document_id)
    if document is None:
        return templates.TemplateResponse(request, "not_found.html", {}, status_code=404)

    try:
        approve_document(db, document, user_id=actor.user_id)
    except InvalidTransitionError as exc:
        # No rollback -- see review_correct_field's comment above.
        return _render_detail(
            request,
            db=db,
            tenant_id=actor.tenant_id,
            document_id=document_id,
            error=str(exc),
            status_code=409,
        )

    db.commit()
    return RedirectResponse(url="/review", status_code=303)


@router.post("/review/{document_id}/reject", response_class=HTMLResponse, response_model=None)
def review_reject(
    request: Request,
    document_id: uuid.UUID,
    actor: Annotated[AuthContext, Depends(get_current_web_actor)],
    db: Annotated[Session, Depends(get_db)],
    # Defaults to "" rather than being required: FastAPI treats a
    # required Form(str) submitted as an empty string as *missing*
    # entirely and returns a raw 422 before this function ever runs --
    # confirmed behavior, not a guess. A browser submitting a blank
    # comment should see reject_document's own, nicely-rendered
    # MissingRejectionCommentError page, not a raw JSON 422.
    comment: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    document = get_document(db, tenant_id=actor.tenant_id, document_id=document_id)
    if document is None:
        return templates.TemplateResponse(request, "not_found.html", {}, status_code=404)

    try:
        reject_document(db, document, user_id=actor.user_id, comment=comment)
    except (InvalidTransitionError, MissingRejectionCommentError) as exc:
        # No rollback -- see review_correct_field's comment above.
        return _render_detail(
            request,
            db=db,
            tenant_id=actor.tenant_id,
            document_id=document_id,
            error=str(exc),
            status_code=409,
        )

    db.commit()
    return RedirectResponse(url="/review", status_code=303)
