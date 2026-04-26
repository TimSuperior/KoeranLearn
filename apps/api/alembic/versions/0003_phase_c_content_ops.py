"""phase c content operations upgrade

Revision ID: 0003_phase_c_content_ops
Revises: 0002_phase_ab_additive_upgrade
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0003_phase_c_content_ops"
down_revision = "0002_phase_ab_additive_upgrade"
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


def _create_table_if_missing(table_name: str, *columns, **kwargs) -> None:
    inspector = inspect(op.get_bind())
    if not _has_table(inspector, table_name):
        op.create_table(table_name, *columns, **kwargs)


def upgrade() -> None:
    governed_tables = (
        "learning_paths",
        "courses",
        "modules",
        "lessons",
        "exercises",
        "vocabulary",
        "grammar_points",
        "example_sentences",
        "scenarios",
        "dialogues",
    )

    for table_name in governed_tables:
        _add_column(table_name, sa.Column("access_state", sa.String(length=32), nullable=False, server_default="free"))
        _add_column(table_name, sa.Column("resolved_access_state", sa.String(length=32), nullable=False, server_default="free"))
        _add_column(table_name, sa.Column("created_by_admin_id", sa.Integer(), nullable=True))
        _add_column(table_name, sa.Column("updated_by_admin_id", sa.Integer(), nullable=True))

    _add_column("lessons", sa.Column("cover_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    _add_column("lessons", sa.Column("audience_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    _add_column("lessons", sa.Column("prerequisite_lesson_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    _add_column("exercises", sa.Column("instructions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    _add_column("exercises", sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    _add_column("vocabulary", sa.Column("notes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    _add_column("vocabulary", sa.Column("variants", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    _add_column("grammar_points", sa.Column("usage_notes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    _add_column("scenarios", sa.Column("audience_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    _add_column("dialogue_lines", sa.Column("reveal_mode", sa.String(length=32), nullable=False, server_default="toggle"))
    _add_column("dialogue_lines", sa.Column("highlighted_expressions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    _add_column("premium_packs", sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"))
    _add_column("premium_packs", sa.Column("status", sa.String(length=32), nullable=False, server_default="published"))
    _add_column("premium_packs", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    _create_table_if_missing(
        "content_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=128), nullable=False, unique=True),
        sa.Column("title", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("description", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="topic"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="published"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "lesson_vocabulary_links",
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), primary_key=True),
        sa.Column("vocabulary_id", sa.Integer(), sa.ForeignKey("vocabulary.id"), primary_key=True),
    )

    _create_table_if_missing(
        "lesson_grammar_links",
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), primary_key=True),
        sa.Column("grammar_point_id", sa.Integer(), sa.ForeignKey("grammar_points.id"), primary_key=True),
    )

    _create_table_if_missing(
        "lesson_scenario_links",
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), primary_key=True),
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), primary_key=True),
    )

    _create_table_if_missing(
        "scenario_vocabulary_links",
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), primary_key=True),
        sa.Column("vocabulary_id", sa.Integer(), sa.ForeignKey("vocabulary.id"), primary_key=True),
    )

    _create_table_if_missing(
        "scenario_grammar_links",
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), primary_key=True),
        sa.Column("grammar_point_id", sa.Integer(), sa.ForeignKey("grammar_points.id"), primary_key=True),
    )


def downgrade() -> None:
    pass
