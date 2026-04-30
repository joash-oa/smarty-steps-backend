class LearnerNotFoundError(Exception):
    pass


class LearnerOwnershipError(Exception):
    pass


class InvalidPinError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class LessonNotFoundError(Exception):
    pass


class ExerciseNotFoundError(Exception):
    pass


class QuizNotFoundError(Exception):
    pass


class IncompleteAnswersError(Exception):
    def __init__(self, missing_exercise_ids: list[str]):
        self.missing_exercise_ids = missing_exercise_ids
        super().__init__(f"Missing answers for exercises: {missing_exercise_ids}")
