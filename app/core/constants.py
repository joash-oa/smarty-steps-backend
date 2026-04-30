# Grading — star accuracy thresholds
STAR_THRESHOLD_THREE = 1.0
STAR_THRESHOLD_TWO = 0.70
STAR_THRESHOLD_ONE = 0.50

# Grading — XP and level progression
XP_MULTIPLIER = 10
XP_PER_LEVEL = 100

# Grading — effective-star multipliers for quiz scoring (raw → effective)
EFFECTIVE_STARS_MAP: dict[int, int] = {3: 6, 2: 3, 1: 1, 0: 0}

# Content — difficulty assignment by lesson position within a chapter
DIFFICULTY_EASY_MAX_INDEX = 2
DIFFICULTY_MEDIUM_MAX_INDEX = 4

# Quiz — difficulty assignment by learner average stars
QUIZ_HARD_STAR_THRESHOLD = 2.5
QUIZ_MEDIUM_STAR_THRESHOLD = 1.5

# Claude API
CLAUDE_MODEL = "claude-opus-4-7"
CLAUDE_TIMEOUT_SECONDS = 60.0
LESSON_MAX_TOKENS = 4096
QUIZ_MAX_TOKENS = 3000
GRADE_LABELS: dict[int, str] = {
    0: "Kindergarten",
    1: "Grade 1",
    2: "Grade 2",
    3: "Grade 3",
}

# Standards API
STANDARDS_API_TIMEOUT_SECONDS = 30.0
STANDARDS_DEPTH_DOMAIN = 0
STANDARDS_DEPTH_STANDARD = 2

# Standard set IDs from Common Standards Project — NY Next Generation standards (most recent)
STANDARD_SET_IDS: dict[tuple[str, int], str] = {
    ("math", 0): "DA1743190A534CB0AEC12F494BE1F8D7_D2868537_grade-k",
    ("math", 1): "DA1743190A534CB0AEC12F494BE1F8D7_D2868537_grade-01",
    ("math", 2): "DA1743190A534CB0AEC12F494BE1F8D7_D2868537_grade-02",
    ("math", 3): "DA1743190A534CB0AEC12F494BE1F8D7_D2868537_grade-03",
    ("science", 0): "DA1743190A534CB0AEC12F494BE1F8D7_D2778655_grade-k",
    ("science", 1): "DA1743190A534CB0AEC12F494BE1F8D7_D2778655_grade-01",
    ("science", 2): "DA1743190A534CB0AEC12F494BE1F8D7_D2778655_grade-02",
    ("science", 3): "DA1743190A534CB0AEC12F494BE1F8D7_D2778655_grade-03",
    ("english", 0): "DA1743190A534CB0AEC12F494BE1F8D7_D2867744_grade-k",
    ("english", 1): "DA1743190A534CB0AEC12F494BE1F8D7_D2867744_grade-01",
    ("english", 2): "DA1743190A534CB0AEC12F494BE1F8D7_D2867744_grade-02",
    ("english", 3): "DA1743190A534CB0AEC12F494BE1F8D7_D2867744_grade-03",
}

# Leaderboard
LEADERBOARD_MAX_RESULTS = 50
LEADERBOARD_WEEKLY_DAYS = 7
LEADERBOARD_MONTHLY_DAYS = 30

# Dashboard
DASHBOARD_MASTERED_STARS = 3
DASHBOARD_NEEDS_PRACTICE_MAX_STARS = 1
DASHBOARD_RECENT_ACTIVITY_LIMIT = 10
