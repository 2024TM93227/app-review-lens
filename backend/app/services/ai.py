"""
AI wrapper service for generating suggestions using an LLM provider.
This module expects `OPENAI_API_KEY` to be set in the environment.
"""
from typing import Any, Dict
import os
import logging

logger = logging.getLogger(__name__)

try:
    import openai
except Exception:
    openai = None


def _get_api_key() -> str:
    return os.getenv('OPENAI_API_KEY', '')


def generate_suggestions(payload: Dict[str, Any], model: str = 'gpt-3.5-turbo') -> Dict[str, Any]:
    """Call the LLM provider with a prompt built from the payload and return structured suggestions.

    The payload should include comparison data, top_issues, aspect diffs, and recent trends.
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY not set in environment')

    if openai is None:
        raise RuntimeError('openai package not installed')

    openai.api_key = api_key

    system_prompt = (
        "You are an expert product manager helping prioritize app store review issues. "
        "Given comparison data, aspect sentiment diffs, top issues and trends, produce:\n"
        "1) A concise executive summary (1-2 sentences),\n"
        "2) A prioritized list of 3 action items with rationale and estimated impact,\n"
        "3) Suggested release note bullet(s) to address top issues,\n"
        "4) Optional short A/B test idea or quick experiment to validate fixes.\n"
        "Return only JSON with keys: summary, action_items, release_notes, experiment."
    )

    # Build user content with a compact representation of the payload
    user_content = f"Context payload:\n{payload}\n\nRespond in JSON only."

    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=512,
            temperature=0.2,
        )

        text = resp['choices'][0]['message']['content']

        # Try to parse JSON from assistant response; be defensive
        import json

        try:
            parsed = json.loads(text)
            return parsed
        except Exception:
            # If parsing fails, wrap raw text into a JSON structure
            logger.warning('LLM returned non-JSON content; returning raw text')
            return {
                'summary': text.strip(),
                'action_items': [],
                'release_notes': [],
                'experiment': None
            }

    except Exception as e:
        logger.exception('Error calling LLM provider')
        raise
