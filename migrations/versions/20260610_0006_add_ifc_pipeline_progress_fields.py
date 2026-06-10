"""add ifc pipeline progress fields

Revision ID: 20260610_0006
Revises: 20260610_0005
Create Date: 2026-06-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_0006"
down_revision: str | None = "20260610_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ifc_files", sa.Column("pipeline_stage", sa.String(length=64), nullable=True))
    op.add_column(
        "ifc_files",
        sa.Column("pipeline_progress", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("ifc_files", sa.Column("pipeline_message", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE ifc_files
        SET pipeline_stage = CASE
                WHEN status = 'uploaded' THEN 'uploaded'
                WHEN status = 'processing' THEN 'processing'
                WHEN status = 'processed' THEN 'processed'
                WHEN status = 'failed' THEN 'failed'
                ELSE pipeline_stage
            END,
            pipeline_progress = CASE
                WHEN status = 'processed' THEN 100
                WHEN status = 'failed' THEN 100
                WHEN status = 'processing' THEN 50
                ELSE 0
            END
        """
    )

    op.alter_column("ifc_files", "pipeline_progress", server_default=None)
    op.create_index("ix_ifc_files_pipeline_stage", "ifc_files", ["pipeline_stage"])


def downgrade() -> None:
    op.drop_index("ix_ifc_files_pipeline_stage", table_name="ifc_files")
    op.drop_column("ifc_files", "pipeline_message")
    op.drop_column("ifc_files", "pipeline_progress")
    op.drop_column("ifc_files", "pipeline_stage")
