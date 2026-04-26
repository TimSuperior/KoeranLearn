"""guided curriculum and listening support

Revision ID: 0004_guided_curriculum_audio
Revises: 0003_phase_c_content_ops
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0004_guided_curriculum_audio"
down_revision = "0003_phase_c_content_ops"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column(table_name: str, column: sa.Column) -> None:
    inspector = inspect(op.get_bind())
    if _has_table(inspector, table_name) and not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column("dialogue_lines", sa.Column("audio_asset_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    pass
