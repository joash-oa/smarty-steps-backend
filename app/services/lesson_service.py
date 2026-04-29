import copy
import random
from uuid import UUID


def compute_lock_states(
    chapters: list,
    lessons_by_chapter: dict,
    completed_lesson_ids: set,
) -> dict[UUID, bool]:
    """Return {lesson_id: is_locked} for every lesson. Pure function — no DB calls."""
    lock_states = {}
    for chapter_index, chapter in enumerate(chapters):
        lessons = sorted(
            lessons_by_chapter.get(chapter.id, []), key=lambda lesson: lesson.order_index
        )
        for lesson_index, lesson in enumerate(lessons):
            if chapter_index == 0 and lesson_index == 0:
                lock_states[lesson.id] = False
            elif lesson_index == 0:
                previous_chapter = chapters[chapter_index - 1]
                previous_lessons = lessons_by_chapter.get(previous_chapter.id, [])
                all_previous_complete = all(
                    pl.id in completed_lesson_ids for pl in previous_lessons
                )
                lock_states[lesson.id] = not all_previous_complete
            else:
                previous_lesson = lessons[lesson_index - 1]
                lock_states[lesson.id] = previous_lesson.id not in completed_lesson_ids
    return lock_states


def sanitize_lesson_content(content: dict) -> dict:
    """Strip correct answers from lesson JSONB. Returns a new dict — does not mutate input."""
    sanitized = copy.deepcopy(content)
    for exercise in sanitized.get("exercises", []):
        exercise_type = exercise.get("type")
        if exercise_type == "multiple_choice":
            exercise.pop("correct_option_id", None)
            exercise.pop("explanation", None)
        elif exercise_type == "fill_blank":
            exercise.pop("correct_word", None)
        elif exercise_type == "matching":
            pairs = exercise.pop("pairs", [])
            left_items = [pair["left"] for pair in pairs]
            right_items = [pair["right"] for pair in pairs]
            random.shuffle(right_items)
            exercise["left_items"] = left_items
            exercise["right_items"] = right_items
    return sanitized


def compute_effective_stars(raw_stars: int) -> int:
    """Apply chapter quiz star multiplier: 3→6, 2→3, 1→1, 0→0."""
    return {3: 6, 2: 3, 1: 1, 0: 0}.get(raw_stars, 0)
