"""add check constraints for document type and status

Revision ID: 712de95c1ba6
Revises: ac1ef6790ce3
Create Date: 2026-07-29 00:19:25.487811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '712de95c1ba6'
down_revision: Union[str, Sequence[str], None] = 'ac1ef6790ce3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows were written before values_callable was added to the
    # model, so document_type/status hold the enum member NAME
    # (e.g. 'UPLOADED') rather than its value ('uploaded'). For every
    # value in both enums, value == name.lower(), so this is a safe,
    # lossless normalization before the constraint below starts
    # rejecting anything that isn't a lowercase value.
    op.execute("UPDATE documents SET document_type = lower(document_type)")
    op.execute("UPDATE documents SET status = lower(status)")

    op.create_check_constraint(
        "document_type_enum",
        "documents",
        "document_type IN ('invoice', 'change_order', 'unrecognized')",
    )
    op.create_check_constraint(
        "document_status_enum",
        "documents",
        "status IN ('uploaded', 'processing', 'extracted', 'in_review', "
        "'approved', 'rejected', 'exported')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("document_status_enum", "documents", type_="check")
    op.drop_constraint("document_type_enum", "documents", type_="check")

    op.execute("UPDATE documents SET document_type = upper(document_type)")
    op.execute("UPDATE documents SET status = upper(status)")
