"""premium audio assets and protected delivery

Revision ID: 0005_premium_audio_assets
Revises: 0004_guided_curriculum_audio
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0005_premium_audio_assets"
down_revision = "0004_guided_curriculum_audio"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if _has_table(inspector, "audio_assets"):
        return

    op.create_table(
        "audio_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("attachment_role", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("variant", sa.String(length=32), nullable=False, server_default="default"),
        sa.Column("source_language", sa.String(length=16), nullable=True),
        sa.Column("target_language", sa.String(length=16), nullable=True),
        sa.Column("storage_backend", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False, server_default="audio/mpeg"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("transcript", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("transcript_mode", sa.String(length=32), nullable=False, server_default="toggle"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("premium_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("compliance_state", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("cache_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
        sa.Column("updated_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=True),
        sa.Column("lesson_block_id", sa.Integer(), sa.ForeignKey("lesson_blocks.id"), nullable=True),
        sa.Column("exercise_id", sa.Integer(), sa.ForeignKey("exercises.id"), nullable=True),
        sa.Column("vocabulary_id", sa.Integer(), sa.ForeignKey("vocabulary.id"), nullable=True),
        sa.Column("example_sentence_id", sa.Integer(), sa.ForeignKey("example_sentences.id"), nullable=True),
        sa.Column("dialogue_line_id", sa.Integer(), sa.ForeignKey("dialogue_lines.id"), nullable=True),
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("public_id", name="uq_audio_assets_public_id"),
    )
    op.create_index("ix_audio_assets_attachment_role", "audio_assets", ["attachment_role"])
    op.create_index("ix_audio_assets_variant", "audio_assets", ["variant"])
    op.create_index("ix_audio_assets_status", "audio_assets", ["status"])
    op.create_index("ix_audio_assets_compliance_state", "audio_assets", ["compliance_state"])
    op.create_index("ix_audio_assets_is_deleted", "audio_assets", ["is_deleted"])
    op.create_index("ix_audio_assets_expires_at", "audio_assets", ["expires_at"])
    op.create_index("ix_audio_assets_lesson_id", "audio_assets", ["lesson_id"])
    op.create_index("ix_audio_assets_lesson_block_id", "audio_assets", ["lesson_block_id"])
    op.create_index("ix_audio_assets_exercise_id", "audio_assets", ["exercise_id"])
    op.create_index("ix_audio_assets_vocabulary_id", "audio_assets", ["vocabulary_id"])
    op.create_index("ix_audio_assets_example_sentence_id", "audio_assets", ["example_sentence_id"])
    op.create_index("ix_audio_assets_dialogue_line_id", "audio_assets", ["dialogue_line_id"])
    op.create_index("ix_audio_assets_scenario_id", "audio_assets", ["scenario_id"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not _has_table(inspector, "audio_assets"):
        return

    for index_name in [
        "ix_audio_assets_scenario_id",
        "ix_audio_assets_dialogue_line_id",
        "ix_audio_assets_example_sentence_id",
        "ix_audio_assets_vocabulary_id",
        "ix_audio_assets_exercise_id",
        "ix_audio_assets_lesson_block_id",
        "ix_audio_assets_lesson_id",
        "ix_audio_assets_expires_at",
        "ix_audio_assets_is_deleted",
        "ix_audio_assets_compliance_state",
        "ix_audio_assets_status",
        "ix_audio_assets_variant",
        "ix_audio_assets_attachment_role",
    ]:
        op.drop_index(index_name, table_name="audio_assets")
    op.drop_table("audio_assets")
