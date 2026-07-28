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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        SqlEnum(DocumentType, native_enum=False, length=20),
        nullable=False,
        default=DocumentType.UNRECOGNIZED,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SqlEnum(DocumentStatus, native_enum=False, length=20),
        nullable=False,
        default=DocumentStatus.UPLOADED,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="document", order_by="AuditEvent.created_at"
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="audit_events")