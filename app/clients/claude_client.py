# ruff: noqa: E501
import json
import logging
import re

import anthropic

from app.core.config import settings
from app.core.constants import (
    CLAUDE_MODEL,
    CLAUDE_TIMEOUT_SECONDS,
    GRADE_LABELS,
    LESSON_MAX_TOKENS,
    QUIZ_MAX_TOKENS,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an educational content creator for Smarty Steps, a learning app for children ages 5-8.

Generate lesson content as valid JSON matching this exact schema:
{
  "intro": {
    "title": "<lesson title>",
    "description": "<1-2 sentences, child-friendly>",
    "mascot_quote": "<encouraging quote from the mascot>"
  },
  "exercises": [
    // EXACTLY 15 exercises, mix of types below, progressing easy->medium->hard
    // Type: multiple_choice
    {
      "id": "ex_1",
      "type": "multiple_choice",
      "difficulty": "easy|medium|hard",
      "prompt": "<question text>",
      "mascot_hint": "<short hint>",
      "options": [{"id": "a", "text": "..."}, {"id": "b", "text": "..."}, {"id": "c", "text": "..."}, {"id": "d", "text": "..."}],
      "correct_option_id": "a|b|c|d",
      "explanation": "<why the answer is correct>"
    },
    // Type: fill_blank
    {
      "id": "ex_N",
      "type": "fill_blank",
      "difficulty": "easy|medium|hard",
      "prompt": "Fill in the blank",
      "sentence_parts": ["<part before blank>", "_____", "<part after blank>"],
      "word_bank": ["<correct word>", "<wrong1>", "<wrong2>", "<wrong3>"],
      "correct_word": "<correct word>",
      "mascot_hint": "<short hint>"
    },
    // Type: matching
    {
      "id": "ex_N",
      "type": "matching",
      "difficulty": "easy|medium|hard",
      "prompt": "<instruction>",
      "mascot_hint": "<short hint>",
      "pairs": [
        {"left": "<item>", "right": "<match>"},
        {"left": "<item>", "right": "<match>"},
        {"left": "<item>", "right": "<match>"}
      ]
    }
  ],
  "result": {
    "badge_name": "<achievement name>",
    "badge_description": "<1 sentence>"
  },
  "stars_available": 3
}

Rules:
- Exactly 15 exercises total
- Mix all 3 types (at least 4 multiple_choice, at least 3 fill_blank, at least 3 matching)
- First 5 exercises: difficulty easy. Next 5: difficulty medium. Last 5: difficulty hard.
- All content must be appropriate for ages 5-8
- IDs must be "ex_1" through "ex_15" in order
- Return ONLY the JSON object, no markdown fences or extra text"""


class ClaudeClient:
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=CLAUDE_TIMEOUT_SECONDS,
        )

    async def generate_lesson(
        self,
        standard_title: str,
        standard_description: str,
        subject: str,
        grade_level: int,
    ) -> dict:
        """Generate lesson JSONB for a standard. Returns parsed dict."""
        grade_label = GRADE_LABELS[grade_level]
        user_message = (
            f"Generate a lesson for this {subject} standard ({grade_label}):\n"
            f"Standard: {standard_title}\n"
            f"Description: {standard_description}\n\n"
            f"Return only the JSON object."
        )
        response = await self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=LESSON_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        return _parse_json(raw)

    async def generate_quiz(self, difficulty: str, lesson_summaries: str) -> dict:
        """Generate a chapter quiz for the given difficulty and lesson performance data."""
        system_prompt = (
            "You are an educational content creator for Smarty Steps, "
            "a learning app for children ages 5-8.\n\n"
            "Generate a personalized chapter quiz as valid JSON with this schema:\n"
            '{\n  "exercises": [\n'
            "    // 7-10 exercises, mix of multiple_choice, fill_blank, matching types\n"
            "    // Same format as lesson exercises, including correct answers\n"
            "  ]\n}\n\n"
            "Set exercise difficulty based on the provided learner performance data.\n"
            "Return ONLY the JSON object, no markdown fences."
        )
        user_message = (
            f"Generate a chapter quiz (difficulty: {difficulty}).\n"
            f"Learner performance:\n{lesson_summaries}\n"
            f"Focus on weaker areas. Return only the JSON."
        )
        response = await self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=QUIZ_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    text = fenced.group(1) if fenced else raw
    return json.loads(text)


_claude_client: ClaudeClient | None = None


def get_claude_client() -> ClaudeClient:
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
