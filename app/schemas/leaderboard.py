from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    avatar_emoji: str
    total_stars: int
    streak_days: int


class LeaderboardResponse(BaseModel):
    period: str
    rankings: list[LeaderboardEntry]
