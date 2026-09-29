"""Document and audit-event models.

Workflow state lives on Document.status as an enum, but every transition
between states is also recorded as a separate, append-only AuditEvent
row — the audit log is the ground truth of what happened; Document.status
is a cached projection of the most recent transition, not the source of
truth itself. See docs/architecture/database-design.md.

Stored as plain strings with a CHECK constraint (native_enum=False)
rather than a native Postgres ENUM type, matching the `text` column type
in the design doc and avoiding native-enum ALTER TYPE migration pain if
a new status/type is added later.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ascent.shared.db import Base


class DocumentType(enum.StrEnum):
    INVOICE = "invoice"
    CHANGE_ORDER = "change_order"
    UNRECOGNIZED = "unrecognized"


class DocumentStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        SqlEnum(
            DocumentType,
            name="document_type_enum",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentType.UNRECOGNIZED,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SqlEnum(
            DocumentStatus,
            name="document_status_enum",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentStatus.UPLOADED,
    )
    # An overall confidence for the document as a whole, so the review
    # queue (TASK-022) can filter/sort by "needs scrutiny" without
    # joining per-field data. Per-field confidence lives in
    # extracted_fields (docs/architecture/database-design.md) once that
    # table exists; this is a coarser, document-level signal, not a
    # replacement for it. Nullable and unpopulated until extraction is
    # actually wired into the processing pipeline -- see
    # documents/processing.py.
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="document", order_by="AuditEvent.created_at"
    )
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="document", order_by="ExtractedField.field_name"
    )


class ExtractedField(Base):
    """One row per field an extraction produced (TASK-018/021's
    InvoiceData/ChangeOrderData, flattened) -- see
    docs/architecture/database-design.md. extracted_value is never
    overwritten; a reviewer's correction goes in corrected_value with
    is_corrected flipped, so what the model actually said is always
    still there to audit later (see corrections.py).

    Carries tenant_id directly, same as AuditEvent, even though the
    original database-design.md sketch didn't -- every tenant-owned
    table in this codebase does, specifically so a query can be scoped
    by a plain equality filter instead of a join through documents,
    which would make a missing tenant_id filter easier to miss.
    """

    __tablename__ = "extracted_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    extracted_value: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False)
    corrected_value: Mapped[str | None] = mapped_column(String, nullable=True)
    is_corrected: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="extracted_fields")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="audit_events")
