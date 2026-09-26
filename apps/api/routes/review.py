"""Review queue endpoint (FR5, TASK-022).

GET /api/v1/documents -- lists documents for the current tenant,
filterable by status, document type, and confidence, paginated. This
is the endpoint a reviewer's dashboard polls to see what needs
attention; see docs/architecture/api-specification.md.

Shares its path prefix with documents.py's upload endpoint (that
router owns POST, this one owns GET) rather than being a distinct
resource -- the two are the same `documents` collection, just
different operations on it.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ascent.documents.models import DocumentStatus, DocumentType
from ascent.documents.repository import list_review_queue
from ascent.security.tenancy import AuthContext, get_current_actor
from ascent.shared.db import get_db

router = APIRouter(prefix="/api/v1/documents", tags=["review"])


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    status: DocumentStatus
    confidence: float | None
    original_filename: str
    created_at: datetime
    updated_at: datetime


class ReviewQueuePage(BaseModel):
    items: list[DocumentSummary]
    page: int
    page_size: int
    total: int


@router.get("")
def get_review_queue(
    actor: Annotated[AuthContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db)],
    status: DocumentStatus | None = None,
    document_type: DocumentType | None = None,
    min_confidence: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    max_confidence: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReviewQueuePage:
    items, total = list_review_queue(
        db,
        tenant_id=actor.tenant_id,
        status=status,
        document_type=document_type,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        page=page,
        page_size=page_size,
    )
    return ReviewQueuePage(
        items=[DocumentSummary.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
