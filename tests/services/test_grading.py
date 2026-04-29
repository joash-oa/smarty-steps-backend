from datetime import datetime, timedelta, timezone

from app.services.grading import (
    compute_effective_stars,
    compute_level,
    compute_new_streak,
    compute_quiz_xp,
    compute_stars,
    compute_xp,
    grade_exercise,
)


def test_grade_multiple_choice_correct():
    exercise = {"type": "multiple_choice", "correct_option_id": "b"}
    assert grade_exercise(exercise, {"selected_option_id": "b"}) is True


def test_grade_multiple_choice_wrong():
    exercise = {"type": "multiple_choice", "correct_option_id": "b"}
    assert grade_exercise(exercise, {"selected_option_id": "a"}) is False


def test_grade_fill_blank_correct_case_insensitive():
    exercise = {"type": "fill_blank", "correct_word": "On"}
    assert grade_exercise(exercise, {"selected_word": "on"}) is True


def test_grade_fill_blank_wrong():
    exercise = {"type": "fill_blank", "correct_word": "on"}
    assert grade_exercise(exercise, {"selected_word": "under"}) is False


def test_grade_matching_correct():
    exercise = {
        "type": "matching",
        "pairs": [{"left": "🐟", "right": "🌊"}, {"left": "🦅", "right": "🏔️"}],
    }
    assert grade_exercise(exercise, {"pairs": [["🐟", "🌊"], ["🦅", "🏔️"]]}) is True


def test_grade_matching_wrong_pair():
    exercise = {
        "type": "matching",
        "pairs": [{"left": "🐟", "right": "🌊"}, {"left": "🦅", "right": "🏔️"}],
    }
    assert grade_exercise(exercise, {"pairs": [["🐟", "🏔️"], ["🦅", "🌊"]]}) is False


def test_compute_stars_100_percent():
    assert compute_stars(correct=5, total=5) == 3


def test_compute_stars_80_percent():
    assert compute_stars(correct=4, total=5) == 2


def test_compute_stars_60_percent():
    assert compute_stars(correct=9, total=15) == 1


def test_compute_stars_below_50():
    assert compute_stars(correct=3, total=10) == 0


def test_compute_stars_zero_total():
    assert compute_stars(correct=0, total=0) == 0


def test_compute_xp_values():
    assert compute_xp(0) == 10
    assert compute_xp(1) == 20
    assert compute_xp(2) == 30
    assert compute_xp(3) == 40


def test_compute_effective_stars():
    assert compute_effective_stars(3) == 6
    assert compute_effective_stars(2) == 3
    assert compute_effective_stars(1) == 1
    assert compute_effective_stars(0) == 0


def test_compute_quiz_xp():
    assert compute_quiz_xp(3) == 70
    assert compute_quiz_xp(2) == 40
    assert compute_quiz_xp(1) == 20
    assert compute_quiz_xp(0) == 10


def test_compute_level():
    assert compute_level(0) == 1
    assert compute_level(99) == 1
    assert compute_level(100) == 2
    assert compute_level(250) == 3


def test_streak_first_ever_activity():
    assert compute_new_streak(0, None) == 1


def test_streak_same_day_no_change():
    last = datetime.now(timezone.utc)
    assert compute_new_streak(5, last) == 5


def test_streak_yesterday_increments():
    last = datetime.now(timezone.utc) - timedelta(days=1)
    assert compute_new_streak(5, last) == 6


def test_streak_older_resets():
    last = datetime.now(timezone.utc) - timedelta(days=3)
    assert compute_new_streak(5, last) == 1
