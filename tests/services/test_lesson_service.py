from unittest.mock import MagicMock
from uuid import uuid4

from app.db.models import Chapter, Lesson
from app.services.lesson_service import (
    compute_effective_stars,
    compute_lock_states,
    sanitize_lesson_content,
)


def _chapter(order):
    chapter = MagicMock(spec=Chapter)
    chapter.id = uuid4()
    chapter.order_index = order
    return chapter


def _lesson(chapter_id, order):
    lesson = MagicMock(spec=Lesson)
    lesson.id = uuid4()
    lesson.chapter_id = chapter_id
    lesson.order_index = order
    return lesson


def test_first_lesson_of_first_chapter_always_unlocked():
    chapter = _chapter(1)
    lesson = _lesson(chapter.id, 1)
    result = compute_lock_states(
        chapters=[chapter],
        lessons_by_chapter={chapter.id: [lesson]},
        completed_lesson_ids=set(),
    )
    assert result[lesson.id] is False


def test_second_lesson_locked_until_first_completed():
    chapter = _chapter(1)
    lesson_one = _lesson(chapter.id, 1)
    lesson_two = _lesson(chapter.id, 2)
    result = compute_lock_states(
        chapters=[chapter],
        lessons_by_chapter={chapter.id: [lesson_one, lesson_two]},
        completed_lesson_ids=set(),
    )
    assert result[lesson_one.id] is False
    assert result[lesson_two.id] is True


def test_second_lesson_unlocked_when_first_completed():
    chapter = _chapter(1)
    lesson_one = _lesson(chapter.id, 1)
    lesson_two = _lesson(chapter.id, 2)
    result = compute_lock_states(
        chapters=[chapter],
        lessons_by_chapter={chapter.id: [lesson_one, lesson_two]},
        completed_lesson_ids={lesson_one.id},
    )
    assert result[lesson_two.id] is False


def test_chapter_boundary_locked_until_all_previous_complete():
    chapter_one = _chapter(1)
    chapter_two = _chapter(2)
    lesson_a = _lesson(chapter_one.id, 1)
    lesson_b = _lesson(chapter_one.id, 2)
    lesson_c = _lesson(chapter_two.id, 1)
    result = compute_lock_states(
        chapters=[chapter_one, chapter_two],
        lessons_by_chapter={chapter_one.id: [lesson_a, lesson_b], chapter_two.id: [lesson_c]},
        completed_lesson_ids={lesson_a.id},
    )
    assert result[lesson_c.id] is True


def test_chapter_boundary_unlocked_when_all_previous_complete():
    chapter_one = _chapter(1)
    chapter_two = _chapter(2)
    lesson_a = _lesson(chapter_one.id, 1)
    lesson_b = _lesson(chapter_one.id, 2)
    lesson_c = _lesson(chapter_two.id, 1)
    result = compute_lock_states(
        chapters=[chapter_one, chapter_two],
        lessons_by_chapter={chapter_one.id: [lesson_a, lesson_b], chapter_two.id: [lesson_c]},
        completed_lesson_ids={lesson_a.id, lesson_b.id},
    )
    assert result[lesson_c.id] is False


def test_sanitize_strips_correct_answers_from_multiple_choice():
    content = {
        "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
        "exercises": [
            {
                "id": "ex_1",
                "type": "multiple_choice",
                "difficulty": "easy",
                "prompt": "Q?",
                "mascot_hint": "H",
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_option_id": "a",
                "explanation": "Because.",
            },
        ],
        "result": {"badge_name": "B", "badge_description": "BD"},
        "stars_available": 3,
    }
    sanitized = sanitize_lesson_content(content)
    exercise = sanitized["exercises"][0]
    assert "correct_option_id" not in exercise
    assert "explanation" not in exercise


def test_sanitize_strips_correct_word_from_fill_blank():
    content = {
        "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
        "exercises": [
            {
                "id": "ex_1",
                "type": "fill_blank",
                "difficulty": "medium",
                "prompt": "Fill",
                "sentence_parts": ["The", "_____", "cat."],
                "word_bank": ["big", "small"],
                "correct_word": "big",
                "mascot_hint": "H",
            },
        ],
        "result": {"badge_name": "B", "badge_description": "BD"},
        "stars_available": 3,
    }
    sanitized = sanitize_lesson_content(content)
    exercise = sanitized["exercises"][0]
    assert "correct_word" not in exercise


def test_sanitize_converts_matching_pairs_to_shuffled_items():
    content = {
        "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
        "exercises": [
            {
                "id": "ex_1",
                "type": "matching",
                "difficulty": "hard",
                "prompt": "Match",
                "mascot_hint": "H",
                "pairs": [
                    {"left": "🐟", "right": "🌊"},
                    {"left": "🦅", "right": "🏔️"},
                ],
            },
        ],
        "result": {"badge_name": "B", "badge_description": "BD"},
        "stars_available": 3,
    }
    sanitized = sanitize_lesson_content(content)
    exercise = sanitized["exercises"][0]
    assert "pairs" not in exercise
    assert set(exercise["left_items"]) == {"🐟", "🦅"}
    assert set(exercise["right_items"]) == {"🌊", "🏔️"}


def test_sanitize_does_not_mutate_original():
    content = {
        "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
        "exercises": [
            {
                "id": "ex_1",
                "type": "multiple_choice",
                "difficulty": "easy",
                "prompt": "Q?",
                "mascot_hint": "H",
                "options": [],
                "correct_option_id": "a",
                "explanation": "E",
            },
        ],
        "result": {"badge_name": "B", "badge_description": "BD"},
        "stars_available": 3,
    }
    sanitize_lesson_content(content)
    assert "correct_option_id" in content["exercises"][0]


def test_compute_effective_stars():
    assert compute_effective_stars(3) == 6
    assert compute_effective_stars(2) == 3
    assert compute_effective_stars(1) == 1
    assert compute_effective_stars(0) == 0
