from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings

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


@dataclass
class StandardData:
    code: str
    subject: str  # "math" | "science" | "english"
    grade_level: int  # 0-3
    title: str
    description: Optional[str]
    domain: str  # chapter grouping — human-readable domain name from the standard set


class StandardsAPIClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self._base_url = base_url or settings.standards_api_base_url
        self._api_key = api_key or settings.standards_api_key

    async def fetch_standards(self, subject: str, grade_level: int) -> list[StandardData]:
        """Fetch NY Next Generation standards for one subject+grade.

        Uses the Common Standards Project API with hardcoded standard set IDs.
        """
        standard_set_id = STANDARD_SET_IDS.get((subject, grade_level))
        if not standard_set_id:
            return []

        url = f"{self._base_url}/{standard_set_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Api-Key": self._api_key})
            response.raise_for_status()
            data = response.json()

        standards_dict = data.get("data", {}).get("standards", {})
        return _parse_standards(standards_dict, subject, grade_level)


def _parse_standards(standards_dict: dict, subject: str, grade_level: int) -> list[StandardData]:
    """Extract leaf standards (depth=2) from the standard set, associating each with its domain.

    Standards are nested: depth=0 is Domain, depth=1 is Cluster, depth=2 is the actual standard.
    We track the current domain as we iterate by position so each standard gets the right chapter.
    """
    entries = sorted(standards_dict.values(), key=lambda entry: entry.get("position", 0))

    results = []
    current_domain = ""

    for entry in entries:
        depth = entry.get("depth", -1)
        label = entry.get("statementLabel", "")

        if depth == 0 and label == "Domain":
            current_domain = entry.get("description", "").strip()
            continue

        if depth == 2 and label == "Standard":
            notation = entry.get("statementNotation", "").strip()
            description = entry.get("description", "").strip()
            code = notation or entry.get("asnIdentifier", "") or entry.get("id", "")
            if not code or not description:
                continue
            results.append(
                StandardData(
                    code=code,
                    subject=subject,
                    grade_level=grade_level,
                    title=notation or description[:80],
                    description=description,
                    domain=current_domain or subject.title(),
                )
            )

    return results
