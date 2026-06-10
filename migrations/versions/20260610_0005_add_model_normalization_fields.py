"""add model normalization fields

Revision ID: 20260610_0005
Revises: 20260608_0004
Create Date: 2026-06-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_0005"
down_revision: str | None = "20260608_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ifc_files",
        sa.Column("source_format", sa.String(length=16), nullable=False, server_default="ifc"),
    )
    op.add_column(
        "ifc_files",
        sa.Column("normalized_ifc_storage_key", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "ifc_files",
        sa.Column("normalized_ifc_filename", sa.String(length=255), nullable=True),
    )
    op.add_column("ifc_files", sa.Column("normalized_ifc_size", sa.BigInteger(), nullable=True))
    op.add_column("ifc_files", sa.Column("normalization_status", sa.String(length=32), nullable=True))
    op.add_column("ifc_files", sa.Column("normalization_error", sa.Text(), nullable=True))
    op.add_column("ifc_files", sa.Column("autodesk_activity_id", sa.String(length=255), nullable=True))
    op.add_column("ifc_files", sa.Column("autodesk_workitem_id", sa.String(length=128), nullable=True))

    op.execute(
        """
        UPDATE ifc_files
        SET normalized_ifc_storage_key = storage_key,
            normalized_ifc_filename = original_filename,
            normalized_ifc_size = file_size,
            normalization_status = 'ready'
        WHERE source_format = 'ifc'
        """
    )

    op.alter_column("ifc_files", "source_format", server_default=None)
    op.create_index("ix_ifc_files_source_format", "ifc_files", ["source_format"])
    op.create_index("ix_ifc_files_normalization_status", "ifc_files", ["normalization_status"])


def downgrade() -> None:
    op.drop_index("ix_ifc_files_normalization_status", table_name="ifc_files")
    op.drop_index("ix_ifc_files_source_format", table_name="ifc_files")
    op.drop_column("ifc_files", "autodesk_workitem_id")
    op.drop_column("ifc_files", "autodesk_activity_id")
    op.drop_column("ifc_files", "normalization_error")
    op.drop_column("ifc_files", "normalization_status")
    op.drop_column("ifc_files", "normalized_ifc_size")
    op.drop_column("ifc_files", "normalized_ifc_filename")
    op.drop_column("ifc_files", "normalized_ifc_storage_key")
    op.drop_column("ifc_files", "source_format")
