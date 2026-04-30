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


# The Common Standards Project API returns standards as a flat dict of entries, each with a
# "depth" field indicating its level in the hierarchy:
#   depth 0 → Domain   (e.g. "Number and Operations in Base Ten")
#   depth 1 → Cluster  (e.g. "Understand place value")
#   depth 2 → Standard (the actual learning objective we turn into a lesson)
_DEPTH_DOMAIN = 0
_DEPTH_STANDARD = 2


def _parse_standards(standards_dict: dict, subject: str, grade_level: int) -> list[StandardData]:
    # Sort by position so domains appear before their child standards.
    entries = sorted(standards_dict.values(), key=lambda entry: entry.get("position", 0))

    results = []
    current_domain = ""

    for entry in entries:
        depth = entry.get("depth", -1)
        label = entry.get("statementLabel", "")

        if depth == _DEPTH_DOMAIN and label == "Domain":
            # Track the current domain so each standard below it gets the right chapter title.
            current_domain = entry.get("description", "").strip()
            continue

        if depth == _DEPTH_STANDARD and label == "Standard":
            notation = entry.get("statementNotation", "").strip()
            description = entry.get("description", "").strip()
            # Prefer the human-readable notation (e.g. "2.NBT.A.1") as the unique code;
            # fall back to ASN identifier or raw ID if notation is absent.
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
                    # Fall back to capitalised subject name if no domain has been seen yet.
                    domain=current_domain or subject.title(),
                )
            )

    return results
