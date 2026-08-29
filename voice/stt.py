"""Speech-to-text via Gemini multimodal (uses existing GEMINI_API_KEY)."""

from __future__ import annotations

import logging
import os

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

_TRANSCRIBE_PROMPT = (
    "Transcribe the user's spoken question exactly. "
    "Return ONLY the transcript text with no quotes, labels, or commentary. "
    "If the audio is empty or unintelligible, return an empty string."
)


def speech_to_text(audio: bytes, mime_type: str = "audio/webm") -> str:
    if not audio:
        return ""

    model_name = os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                _TRANSCRIBE_PROMPT,
                types.Part.from_bytes(data=audio, mime_type=mime_type),
            ]
        )
        text = (response.text or "").strip()
        # Models sometimes wrap transcripts in quotes
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
            text = text[1:-1].strip()
        logger.info("STT transcript length=%s", len(text))
        return text
    except Exception:
        logger.exception("speech_to_text failed")
        raise
