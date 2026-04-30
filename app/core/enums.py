from enum import IntEnum, StrEnum


class Subject(StrEnum):
    MATH = "math"
    SCIENCE = "science"
    ENGLISH = "english"


class GradeLevel(IntEnum):
    KINDERGARTEN = 0
    GRADE_1 = 1
    GRADE_2 = 2
    GRADE_3 = 3


class LeaderboardPeriod(StrEnum):
    ALL_TIME = "all_time"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
