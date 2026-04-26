"""phase a/b additive upgrade for existing databases

Revision ID: 0002_phase_ab_additive_upgrade
Revises: 0001_initial_schema
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0002_phase_ab_additive_upgrade"
down_revision = "0001_initial_schema"
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
    _add_column("users", sa.Column("role", sa.String(length=32), nullable=False, server_default="user"))

    for table_name in ("learning_paths", "courses", "modules", "lessons", "exercises", "vocabulary", "grammar_points", "scenarios", "dialogues", "example_sentences", "localization_entries"):
        _add_column(table_name, sa.Column("status", sa.String(length=32), nullable=False, server_default="published"))
        _add_column(table_name, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    _add_column("lessons", sa.Column("objectives", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    _add_column("exercises", sa.Column("answer_validation", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    _add_column("scenarios", sa.Column("roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    _add_column("scenarios", sa.Column("target_grammar_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    _add_column("scenarios", sa.Column("target_vocabulary_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    _add_column("scenarios", sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    _add_column("scenarios", sa.Column("audience_languages", sa.JSON(), nullable=False, server_default=sa.text("'[\"ru\",\"uz\",\"en\"]'")))
    _add_column("scenarios", sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"))

    _add_column("dialogues", sa.Column("context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    _add_column("dialogues", sa.Column("checks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    _add_column("dialogues", sa.Column("useful_expressions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    _add_column("dialogues", sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"))

    _add_column("admin_users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    _add_column("admin_users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    _create_table_if_missing(
        "lesson_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False, index=True),
        sa.Column("block_type", sa.String(length=64), nullable=False, server_default="text"),
        sa.Column("title", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("body", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="published"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "dialogue_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dialogue_id", sa.Integer(), sa.ForeignKey("dialogues.id"), nullable=False, index=True),
        sa.Column("speaker", sa.String(length=128), nullable=False),
        sa.Column("korean", sa.Text(), nullable=False),
        sa.Column("translations", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_useful_expression", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True, index=True),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False, unique=True),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False, server_default="user"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "user_scenario_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), nullable=False, index=True),
        sa.Column("dialogue_id", sa.Integer(), sa.ForeignKey("dialogues.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("current_line_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comprehension_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "scenario_id", name="uq_user_scenario"),
    )

    _create_table_if_missing(
        "user_bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_bookmark"),
    )

    _create_table_if_missing(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True, index=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    pass
