"""create ifc import tables

Revision ID: 20260605_0001
Revises:
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260605_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ifc_file_status = postgresql.ENUM(
    "uploaded",
    "processing",
    "processed",
    "failed",
    name="ifc_file_status",
    create_type=False,
)
validation_stage = postgresql.ENUM(
    "file_validation",
    "ifc_parse",
    "schema_validation",
    "asset_detection",
    "asset_validation",
    name="validation_stage",
    create_type=False,
)
validation_severity = postgresql.ENUM(
    "error",
    "warning",
    "info",
    name="validation_severity",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    ifc_file_status.create(bind, checkfirst=True)
    validation_stage.create(bind, checkfirst=True)
    validation_severity.create(bind, checkfirst=True)

    op.create_table(
        "ifc_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("bucket_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("status", ifc_file_status, nullable=False),
        sa.Column("schema_name", sa.String(length=64), nullable=True),
        sa.Column("total_elements", sa.Integer(), nullable=False),
        sa.Column("total_assets", sa.Integer(), nullable=False),
        sa.Column("total_issues", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_ifc_files_created_at", "ifc_files", ["created_at"])
    op.create_index("ix_ifc_files_status", "ifc_files", ["status"])

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ifc_file_id", sa.Integer(), nullable=False),
        sa.Column("asset_code", sa.String(length=255), nullable=True),
        sa.Column("global_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("tag", sa.String(length=255), nullable=True),
        sa.Column("ifc_class", sa.String(length=128), nullable=True),
        sa.Column("asset_type", sa.String(length=128), nullable=True),
        sa.Column("system_name", sa.String(length=255), nullable=True),
        sa.Column("floor", sa.String(length=255), nullable=True),
        sa.Column("room", sa.String(length=255), nullable=True),
        sa.Column("manufacturer", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("material", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quantities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ifc_file_id"], ["ifc_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_asset_code", "assets", ["asset_code"])
    op.create_index("ix_assets_file_id", "assets", ["ifc_file_id"])
    op.create_index("ix_assets_global_id", "assets", ["global_id"])
    op.create_index("ix_assets_ifc_class", "assets", ["ifc_class"])

    op.create_table(
        "validation_issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ifc_file_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("global_id", sa.String(length=64), nullable=True),
        sa.Column("ifc_class", sa.String(length=128), nullable=True),
        sa.Column("object_name", sa.String(length=512), nullable=True),
        sa.Column("stage", validation_stage, nullable=False),
        sa.Column("severity", validation_severity, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("field", sa.String(length=128), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ifc_file_id"], ["ifc_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_validation_issues_asset_id", "validation_issues", ["asset_id"])
    op.create_index("ix_validation_issues_code", "validation_issues", ["code"])
    op.create_index("ix_validation_issues_file_id", "validation_issues", ["ifc_file_id"])
    op.create_index("ix_validation_issues_severity", "validation_issues", ["severity"])
    op.create_index("ix_validation_issues_stage", "validation_issues", ["stage"])


def downgrade() -> None:
    op.drop_index("ix_validation_issues_stage", table_name="validation_issues")
    op.drop_index("ix_validation_issues_severity", table_name="validation_issues")
    op.drop_index("ix_validation_issues_file_id", table_name="validation_issues")
    op.drop_index("ix_validation_issues_code", table_name="validation_issues")
    op.drop_index("ix_validation_issues_asset_id", table_name="validation_issues")
    op.drop_table("validation_issues")

    op.drop_index("ix_assets_ifc_class", table_name="assets")
    op.drop_index("ix_assets_global_id", table_name="assets")
    op.drop_index("ix_assets_file_id", table_name="assets")
    op.drop_index("ix_assets_asset_code", table_name="assets")
    op.drop_table("assets")

    op.drop_index("ix_ifc_files_status", table_name="ifc_files")
    op.drop_index("ix_ifc_files_created_at", table_name="ifc_files")
    op.drop_table("ifc_files")

    bind = op.get_bind()
    validation_severity.drop(bind, checkfirst=True)
    validation_stage.drop(bind, checkfirst=True)
    ifc_file_status.drop(bind, checkfirst=True)
