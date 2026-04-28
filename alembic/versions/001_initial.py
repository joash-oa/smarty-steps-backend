"""Initial schema — all 7 tables + indexes

Revision ID: 001
Revises:
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parents",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("cognito_id", sa.String, unique=True, nullable=False),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("pin_hash", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "learners",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("parents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("age", sa.Integer, nullable=False),
        sa.Column("grade_level", sa.Integer, nullable=False),
        sa.Column("avatar_emoji", sa.String, nullable=False, server_default="🚀"),
        sa.Column("total_stars", sa.Integer, server_default="0"),
        sa.Column("level", sa.Integer, server_default="1"),
        sa.Column("xp", sa.Integer, server_default="0"),
        sa.Column("streak_days", sa.Integer, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_learners_parent_id", "learners", ["parent_id"])
    op.create_index("idx_learners_total_stars", "learners", ["total_stars"])
    op.create_index("idx_learners_last_active", "learners", ["last_active_at"])

    op.create_table(
        "standards",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("code", sa.String, unique=True, nullable=False),
        sa.Column("subject", sa.String, nullable=False),
        sa.Column("grade_level", sa.Integer, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_standards_subject_grade", "standards", ["subject", "grade_level"])

    op.create_table(
        "chapters",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("subject", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
    )
    op.create_index("idx_chapters_subject_order", "chapters", ["subject", "order_index"])

    op.create_table(
        "lessons",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "chapter_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "standard_id",
            UUID(as_uuid=True),
            sa.ForeignKey("standards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subject", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("difficulty", sa.String, nullable=False, server_default="easy"),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("stars_available", sa.Integer, server_default="3"),
    )
    op.create_index("idx_lessons_chapter_order", "lessons", ["chapter_id", "order_index"])
    op.create_index("idx_lessons_standard", "lessons", ["standard_id"])

    op.create_table(
        "lesson_progress",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "learner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            UUID(as_uuid=True),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("completed", sa.Boolean, server_default="false"),
        sa.Column("stars_earned", sa.Integer, server_default="0"),
        sa.Column("score_correct", sa.Integer, nullable=True),
        sa.Column("score_total", sa.Integer, nullable=True),
        sa.Column("time_seconds", sa.Integer, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("learner_id", "lesson_id", name="uq_lesson_progress"),
    )
    op.create_index("idx_lesson_progress_learner", "lesson_progress", ["learner_id"])

    op.create_table(
        "chapter_quizzes",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "learner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chapter_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("difficulty", sa.String, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("stars_earned", sa.Integer, server_default="0"),
        sa.Column("score_correct", sa.Integer, nullable=True),
        sa.Column("score_total", sa.Integer, nullable=True),
        sa.Column("time_seconds", sa.Integer, nullable=True),
        sa.Column("completed", sa.Boolean, server_default="false"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("learner_id", "chapter_id", name="uq_chapter_quiz"),
    )


def downgrade() -> None:
    op.drop_table("chapter_quizzes")
    op.drop_table("lesson_progress")
    op.drop_table("lessons")
    op.drop_table("chapters")
    op.drop_table("standards")
    op.drop_table("learners")
    op.drop_table("parents")
