from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings

SUBJECT_MAP = {
    "math": "Mathematics",
    "science": "Science",
    "english": "English Language Arts",
}

GRADE_MAP = {0: "K", 1: "1", 2: "2", 3: "3"}


@dataclass
class StandardData:
    code: str
    subject: str  # "math" | "science" | "english"
    grade_level: int  # 0-3
    title: str
    description: Optional[str]
    domain: str  # chapter grouping, e.g. "K.CC"


def _extract_domain(item: dict, subject: str) -> str:
    notation = item.get("statementNotation", "")
    if notation and "." in notation:
        parts = notation.split(".")
        prefix = ".".join(parts[:2])
        return prefix
    return SUBJECT_MAP.get(subject, subject.title())


class StandardsAPIClient:
    def __init__(self, base_url: str = None):
        self._base_url = base_url or settings.standards_api_base_url

    async def fetch_standards(self, subject: str, grade_level: int) -> list[StandardData]:
        """Fetch NY State standards for one subject+grade from ASN API."""
        params = {
            "jurisdiction": "NYSED",
            "gradeBegin": GRADE_MAP[grade_level],
            "gradeEnd": GRADE_MAP[grade_level],
            "subjectArea": SUBJECT_MAP[subject],
            "limit": 200,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("resources", []):
            description = item.get("description", "")
            identifier = item.get("identifier", "")
            code = identifier or item.get("uri", "").split("/")[-1]
            title = item.get("statementNotation", identifier) or description[:80]
            if not code or not description:
                continue
            results.append(
                StandardData(
                    code=code,
                    subject=subject,
                    grade_level=grade_level,
                    title=title,
                    description=description,
                    domain=_extract_domain(item, subject),
                )
            )
        return results
