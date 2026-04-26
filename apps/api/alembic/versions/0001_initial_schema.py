"""initial schema baseline

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-23
"""
from alembic import op

from app.core.db import Base
from app.models import schema  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
