import uuid7
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey,
    DateTime, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Parent(Base):
    __tablename__ = "parents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    cognito_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    pin_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    learners = relationship("Learner", back_populates="parent", cascade="all, delete-orphan")


class Learner(Base):
    __tablename__ = "learners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    grade_level = Column(Integer, nullable=False)
    avatar_emoji = Column(String, nullable=False, server_default="🚀")
    total_stars = Column(Integer, server_default="0")
    level = Column(Integer, server_default="1")
    xp = Column(Integer, server_default="0")
    streak_days = Column(Integer, server_default="0")
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("Parent", back_populates="learners")

    __table_args__ = (
        Index("idx_learners_parent_id", "parent_id"),
        Index("idx_learners_total_stars", "total_stars"),
        Index("idx_learners_last_active", "last_active_at"),
    )


class Standard(Base):
    __tablename__ = "standards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    code = Column(String, unique=True, nullable=False)
    subject = Column(String, nullable=False)
    grade_level = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_standards_subject_grade", "subject", "grade_level"),
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)

    lessons = relationship("Lesson", back_populates="chapter", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_chapters_subject_order", "subject", "order_index"),
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    standard_id = Column(UUID(as_uuid=True), ForeignKey("standards.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    difficulty = Column(String, nullable=False, server_default="easy")
    order_index = Column(Integer, nullable=False)
    content = Column(JSONB, nullable=False)
    stars_available = Column(Integer, server_default="3")

    chapter = relationship("Chapter", back_populates="lessons")

    __table_args__ = (
        Index("idx_lessons_chapter_order", "chapter_id", "order_index"),
        Index("idx_lessons_standard", "standard_id"),
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    completed = Column(Boolean, server_default="false")
    stars_earned = Column(Integer, server_default="0")
    score_correct = Column(Integer, nullable=True)
    score_total = Column(Integer, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("learner_id", "lesson_id", name="uq_lesson_progress"),
        Index("idx_lesson_progress_learner", "learner_id"),
    )


class ChapterQuiz(Base):
    __tablename__ = "chapter_quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    difficulty = Column(String, nullable=False)
    content = Column(JSONB, nullable=False)
    stars_earned = Column(Integer, server_default="0")
    score_correct = Column(Integer, nullable=True)
    score_total = Column(Integer, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    completed = Column(Boolean, server_default="false")
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("learner_id", "chapter_id", name="uq_chapter_quiz"),
    )
