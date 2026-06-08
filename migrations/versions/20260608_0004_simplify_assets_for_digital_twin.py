"""simplify assets for digital twin output

Revision ID: 20260608_0004
Revises: 20260605_0003
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260608_0004"
down_revision: str | None = "20260605_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column(
            "cleaning_log",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.execute(
        """
        UPDATE assets
        SET cleaning_log = COALESCE(
            CASE
                WHEN jsonb_typeof(properties -> '_cleaning') = 'array'
                THEN properties -> '_cleaning'
                ELSE '[]'::jsonb
            END,
            '[]'::jsonb
        )
        """
    )
    op.alter_column("assets", "cleaning_log", server_default=None)

    op.drop_column("assets", "raw_properties")
    op.drop_column("assets", "quantities")
    op.drop_column("assets", "properties")


def downgrade() -> None:
    op.add_column(
        "assets",
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "assets",
        sa.Column(
            "quantities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "assets",
        sa.Column(
            "raw_properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute(
        """
        UPDATE assets
        SET properties = jsonb_set(properties, '{_cleaning}', cleaning_log, true)
        WHERE jsonb_typeof(cleaning_log) = 'array'
          AND cleaning_log <> '[]'::jsonb
        """
    )
    op.alter_column("assets", "properties", server_default=None)
    op.alter_column("assets", "quantities", server_default=None)
    op.alter_column("assets", "raw_properties", server_default=None)

    op.drop_column("assets", "cleaning_log")
