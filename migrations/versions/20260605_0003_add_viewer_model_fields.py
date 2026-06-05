"""add viewer model fields

Revision ID: 20260605_0003
Revises: 20260605_0002
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0003"
down_revision: str | None = "20260605_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ifc_files", sa.Column("viewer_model_key", sa.String(length=1024), nullable=True))
    op.add_column("ifc_files", sa.Column("viewer_model_format", sa.String(length=32), nullable=True))
    op.add_column("ifc_files", sa.Column("viewer_model_status", sa.String(length=32), nullable=True))
    op.add_column("ifc_files", sa.Column("viewer_model_size", sa.BigInteger(), nullable=True))
    op.add_column("ifc_files", sa.Column("viewer_model_error", sa.Text(), nullable=True))
    op.create_index("ix_ifc_files_viewer_model_status", "ifc_files", ["viewer_model_status"])


def downgrade() -> None:
    op.drop_index("ix_ifc_files_viewer_model_status", table_name="ifc_files")
    op.drop_column("ifc_files", "viewer_model_error")
    op.drop_column("ifc_files", "viewer_model_size")
    op.drop_column("ifc_files", "viewer_model_status")
    op.drop_column("ifc_files", "viewer_model_format")
    op.drop_column("ifc_files", "viewer_model_key")
