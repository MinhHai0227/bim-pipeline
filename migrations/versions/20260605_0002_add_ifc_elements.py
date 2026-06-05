"""add ifc elements for viewer lookups

Revision ID: 20260605_0002
Revises: 20260605_0001
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260605_0002"
down_revision: str | None = "20260605_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ifc_elements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ifc_file_id", sa.Integer(), nullable=False),
        sa.Column("express_id", sa.Integer(), nullable=True),
        sa.Column("global_id", sa.String(length=64), nullable=True),
        sa.Column("ifc_class", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("tag", sa.String(length=255), nullable=True),
        sa.Column("floor", sa.String(length=255), nullable=True),
        sa.Column("room", sa.String(length=255), nullable=True),
        sa.Column("material", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quantities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ifc_file_id"], ["ifc_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ifc_file_id", "express_id", name="uq_ifc_elements_file_express_id"),
    )
    op.create_index("ix_ifc_elements_express_id", "ifc_elements", ["express_id"])
    op.create_index("ix_ifc_elements_file_id", "ifc_elements", ["ifc_file_id"])
    op.create_index("ix_ifc_elements_global_id", "ifc_elements", ["global_id"])
    op.create_index("ix_ifc_elements_ifc_class", "ifc_elements", ["ifc_class"])
    op.create_index("ix_ifc_elements_name", "ifc_elements", ["name"])

    op.add_column("assets", sa.Column("ifc_element_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_assets_ifc_element_id_ifc_elements",
        "assets",
        "ifc_elements",
        ["ifc_element_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_assets_ifc_element_id", "assets", ["ifc_element_id"])
    op.create_unique_constraint("uq_assets_ifc_element_id", "assets", ["ifc_element_id"])

    op.add_column("validation_issues", sa.Column("ifc_element_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_validation_issues_ifc_element_id_ifc_elements",
        "validation_issues",
        "ifc_elements",
        ["ifc_element_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_validation_issues_ifc_element_id",
        "validation_issues",
        ["ifc_element_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_validation_issues_ifc_element_id", table_name="validation_issues")
    op.drop_constraint(
        "fk_validation_issues_ifc_element_id_ifc_elements",
        "validation_issues",
        type_="foreignkey",
    )
    op.drop_column("validation_issues", "ifc_element_id")

    op.drop_constraint("uq_assets_ifc_element_id", "assets", type_="unique")
    op.drop_index("ix_assets_ifc_element_id", table_name="assets")
    op.drop_constraint(
        "fk_assets_ifc_element_id_ifc_elements",
        "assets",
        type_="foreignkey",
    )
    op.drop_column("assets", "ifc_element_id")

    op.drop_index("ix_ifc_elements_name", table_name="ifc_elements")
    op.drop_index("ix_ifc_elements_ifc_class", table_name="ifc_elements")
    op.drop_index("ix_ifc_elements_global_id", table_name="ifc_elements")
    op.drop_index("ix_ifc_elements_file_id", table_name="ifc_elements")
    op.drop_index("ix_ifc_elements_express_id", table_name="ifc_elements")
    op.drop_table("ifc_elements")
