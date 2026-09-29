"""Document upload, detail, and field-correction endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ascent.documents.corrections import (
    DocumentNotInReviewError,
    FieldNotFoundError,
    correct_field,
)
from ascent.documents.models import DocumentStatus, DocumentType
from ascent.documents.repository import (
    DocumentNotFoundError,
    create_document,
    get_document,
    list_extracted_fields,
)
from ascent.documents.storage import LocalFileStorage, ObjectStorage
from ascent.jobs.queue import enqueue
from ascent.security.tenancy import AuthContext, get_current_actor
from ascent.shared.config import Settings, get_settings
from ascent.shared.db import get_db

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class ExtractedFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_name: str
    extracted_value: str | None
    confidence: float
    corrected_value: str | None
    is_corrected: bool


class DocumentDetail(BaseModel):
    id: uuid.UUID
    document_type: DocumentType
    status: DocumentStatus
    confidence: float | None
    original_filename: str
    fields: list[ExtractedFieldOut]


class FieldCorrectionRequest(BaseModel):
    corrected_value: str


_PDF_MAGIC = b"%PDF-"
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _detect_content_type(content: bytes) -> str | None:
    """Sniff the actual file content rather than trusting the client's
    Content-Type header or the filename extension — either of those can
    be wrong or spoofed; the magic bytes at the start of the file
    cannot.
    """
    if content.startswith(_PDF_MAGIC):
        return "application/pdf"
    if content.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    if content.startswith(_PNG_MAGIC):
        return "image/png"
    return None


def get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> ObjectStorage:
    return LocalFileStorage(settings.storage_dir)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    actor: Annotated[AuthContext, Depends(get_current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    content = await file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds maximum upload size",
        )

    if _detect_content_type(content) is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and image (JPEG/PNG) files are accepted",
        )

    storage_key = f"{actor.tenant_id}/{uuid.uuid4()}_{file.filename or 'upload'}"
    storage.save(key=storage_key, content=content)

    document = create_document(
        db,
        tenant_id=actor.tenant_id,
        uploaded_by_user_id=actor.user_id,
        original_filename=file.filename or "unknown",
        storage_key=storage_key,
    )
    # Enqueued in the same transaction as the document itself: either
    # both are saved together, or (on any earlier failure) neither is --
    # there's no window where a document exists with no processing job.
    enqueue(db, job_type="process_document", payload={"document_id": str(document.id)})
    db.commit()

    return {"id": str(document.id), "status": document.status.value}


@router.get("/{document_id}")
def get_document_detail(
    document_id: uuid.UUID,
    actor: Annotated[AuthContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentDetail:
    document = get_document(db, tenant_id=actor.tenant_id, document_id=document_id)
    if document is None:
        # Wrong tenant and "doesn't exist" look identical here on purpose
        # -- see api-specification.md: never confirm another tenant's
        # document id exists via a 403 instead of a 404.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    fields = list_extracted_fields(db, tenant_id=actor.tenant_id, document_id=document_id)
    return DocumentDetail(
        id=document.id,
        document_type=document.document_type,
        status=document.status,
        confidence=document.confidence,
        original_filename=document.original_filename,
        fields=[ExtractedFieldOut.model_validate(field) for field in fields],
    )


@router.patch("/{document_id}/fields/{field_name}")
def correct_document_field(
    document_id: uuid.UUID,
    field_name: str,
    body: FieldCorrectionRequest,
    actor: Annotated[AuthContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> ExtractedFieldOut:
    try:
        field = correct_field(
            db,
            tenant_id=actor.tenant_id,
            document_id=document_id,
            field_name=field_name,
            corrected_value=body.corrected_value,
            user_id=actor.user_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from exc
    except DocumentNotInReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"document is not in review (status={exc.status.value!r})",
        ) from exc
    except FieldNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Field not found"
        ) from exc

    db.commit()
    return ExtractedFieldOut.model_validate(field)
