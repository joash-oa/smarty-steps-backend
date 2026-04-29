from datetime import datetime, timedelta, timezone
from typing import Optional


def grade_exercise(exercise: dict, answer: dict) -> bool:
    exercise_type = exercise.get("type")
    if exercise_type == "multiple_choice":
        return answer.get("selected_option_id") == exercise.get("correct_option_id")
    elif exercise_type == "fill_blank":
        submitted = answer.get("selected_word", "").strip().lower()
        correct = exercise.get("correct_word", "").strip().lower()
        return submitted == correct
    elif exercise_type == "matching":
        submitted = {tuple(pair) for pair in answer.get("pairs", [])}
        correct = {(pair["left"], pair["right"]) for pair in exercise.get("pairs", [])}
        return submitted == correct
    return False


def compute_stars(correct: int, total: int) -> int:
    if total == 0:
        return 0
    accuracy = correct / total
    if accuracy == 1.0:
        return 3
    elif accuracy >= 0.70:
        return 2
    elif accuracy >= 0.50:
        return 1
    return 0


def compute_xp(stars: int) -> int:
    return 10 * (stars + 1)


def compute_effective_stars(raw_stars: int) -> int:
    return {3: 6, 2: 3, 1: 1, 0: 0}.get(raw_stars, 0)


def compute_quiz_xp(raw_stars: int) -> int:
    return 10 * (compute_effective_stars(raw_stars) + 1)


def compute_level(xp: int) -> int:
    return (xp // 100) + 1


def compute_new_streak(current_streak: int, last_active_at: Optional[datetime]) -> int:
    today = datetime.now(timezone.utc).date()
    if last_active_at is None:
        return 1
    last_date = last_active_at.date()
    if last_date == today:
        return current_streak
    elif last_date == today - timedelta(days=1):
        return current_streak + 1
    return 1
