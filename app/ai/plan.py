import logging

import anthropic
from anthropic import APIConnectionError, APIStatusError, RateLimitError
from anthropic.types import TextBlock

from app.core.config import settings

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8192

SYSTEM_PROMPT = """You are an expert web navigation assistant helping to create annotation plans for browser tasks.
Your job is to break down a web task into clear, executable steps that a human annotator will follow.
Each step must be specific and actionable — describe exactly what to click, type, or observe."""

USER_PROMPT_TEMPLATE = """Create a step-by-step annotation plan for the following task:

Target URL: {url}
Task description: {task}

Requirements:
- Number each step starting from 1
- Each step on its own line
- Be explicit about UI elements to interact with
- Include a verification step at the end
- Use active voice ("Click on...", "Type...", "Navigate to...")
- Start directly with step 1, no preamble or introduction sentence"""


class PlanGenerationError(Exception):
    pass


def _build_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise PlanGenerationError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def generate_plan(url: str, task: str) -> str:
    client = _build_client()

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(url=url, task=task),
                }
            ],
        )
        block = response.content[0]
        if not isinstance(block, TextBlock):
            raise PlanGenerationError("Unexpected response type from API")
        return block.text

    except APIConnectionError as e:
        logger.exception("Anthropic connection error")
        raise PlanGenerationError(f"Connection failed: {e}") from e
    except RateLimitError as e:
        logger.warning("Anthropic rate limit hit")
        raise PlanGenerationError("Rate limit exceeded, please retry later") from e
    except APIStatusError as e:
        logger.exception("Anthropic API returned status %s", e.status_code)
        raise PlanGenerationError(f"API error {e.status_code}: {e.message}") from e
