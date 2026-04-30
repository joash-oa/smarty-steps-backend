from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.constants import (
    STANDARD_SET_IDS,
    STANDARDS_API_TIMEOUT_SECONDS,
    STANDARDS_DEPTH_DOMAIN,
    STANDARDS_DEPTH_STANDARD,
)


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
        async with httpx.AsyncClient(timeout=STANDARDS_API_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers={"Api-Key": self._api_key})
            response.raise_for_status()
            data = response.json()

        standards_dict = data.get("data", {}).get("standards", {})
        return _parse_standards(standards_dict, subject, grade_level)


def _parse_standards(standards_dict: dict, subject: str, grade_level: int) -> list[StandardData]:
    # Sort by position so domains appear before their child standards.
    entries = sorted(standards_dict.values(), key=lambda entry: entry.get("position", 0))

    results = []
    current_domain = ""

    for entry in entries:
        depth = entry.get("depth", -1)
        label = entry.get("statementLabel", "")

        if depth == STANDARDS_DEPTH_DOMAIN and label == "Domain":
            # Track the current domain so each standard below it gets the right chapter title.
            current_domain = entry.get("description", "").strip()
            continue

        if depth == STANDARDS_DEPTH_STANDARD and label == "Standard":
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
