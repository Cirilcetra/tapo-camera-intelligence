"""
Singleton AsyncOpenAI client with exponential-backoff retry wrappers.

Call `get_vision_summary(image_b64)` or `get_embedding(text)` from any
async context. Both return None on permanent failure (exhausted retries)
so callers can treat the result as optional.
"""
import asyncio
import base64
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_VISION_SYSTEM_PROMPT = (
    "You are a CCTV event labeler. Given a single snapshot from a security camera, "
    "respond in ONE short sentence (max 25 words) describing what is happening. "
    "Be factual and concrete. If you see people, describe attire and direction. "
    "If you see a vehicle, describe color and type. "
    'If the scene is empty or unclear, say "No clear activity in frame."'
)

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


def _get_client():
    """Lazy-import so the module loads even without the openai package installed."""
    from openai import AsyncOpenAI  # type: ignore[import]

    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# Module-level singleton — created on first use
_client = None


def client() -> "AsyncOpenAI":  # type: ignore[name-defined]
    global _client
    if _client is None:
        _client = _get_client()
    return _client


async def _with_retry(coro_fn, *args, **kwargs):
    """Call `coro_fn(*args, **kwargs)` with exponential backoff on transient errors."""
    delay = _BASE_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "OpenAI call failed (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= 2
    logger.error("OpenAI call permanently failed after %d retries: %s", _MAX_RETRIES, last_exc)
    return None


async def get_vision_summary(image_b64: str) -> Optional[str]:
    """
    Send a base64-encoded JPEG to GPT-4o-mini vision and return a one-sentence summary.
    Returns None if all retries are exhausted or the API key is not configured.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; skipping vision summary")
        return None

    async def _call():
        response = await client().chat.completions.create(
            model=settings.OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": _VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "low",
                            },
                        }
                    ],
                },
            ],
            max_tokens=60,
            temperature=0,
        )
        return response.choices[0].message.content.strip()

    return await _with_retry(_call)


async def get_embedding(text: str) -> Optional[list[float]]:
    """
    Embed `text` with text-embedding-3-small.
    Returns a list of 1536 floats, or None on failure.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; skipping embedding")
        return None

    async def _call():
        response = await client().embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=text,
        )
        return response.data[0].embedding

    return await _with_retry(_call)
