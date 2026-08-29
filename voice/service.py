"""Voice ask orchestration — STT → Nova (Nexus/Echo) → TTS."""

from __future__ import annotations

import base64
import logging
import os

from echo import service as echo
from nexus.base import EchoContext
from nexus.permissions import user_can_access
from nexus.registry import get_specialist

from .stt import speech_to_text
from .tts import text_to_speech

logger = logging.getLogger(__name__)

# Phase 1: voice is opt-in and proven on Nova only.
DEFAULT_VOICE_SPECIALIST = "Nova"


def ask_with_voice(
    audio: bytes,
    mime_type: str,
    user,
    specialist_name: str | None = None,
    voice_id: str | None = None,
) -> dict:
    specialist_name = specialist_name or DEFAULT_VOICE_SPECIALIST
    specialist = get_specialist(specialist_name)

    if specialist is None:
        return {
            "error": f"Unknown specialist '{specialist_name}'.",
            "status": 404,
        }

    if not user_can_access(user, specialist):
        return {
            "error": "You do not have permission to use this specialist.",
            "status": 403,
        }

    try:
        transcript = speech_to_text(audio, mime_type=mime_type)
    except Exception:
        return {
            "error": "Could not transcribe audio. Please try again.",
            "status": 400,
        }

    if not transcript:
        return {
            "error": "No speech detected. Please try again.",
            "status": 400,
        }

    user_id = getattr(user, "id", None)
    turns = echo.get_context(user_id, specialist.name)
    facts = echo.get_relevant_facts(user_id, transcript)
    context = EchoContext(
        user_id=user_id,
        specialist_name=specialist.name,
        turns=turns,
        facts=facts,
        response_style="voice",
    )

    echo.write_turn(user_id, specialist.name, "user", transcript)

    try:
        response = specialist.handle(transcript, context)
    except Exception:
        logger.exception("Voice specialist %s failed", specialist.name)
        return {
            "error": "This specialist is temporarily unavailable.",
            "status": 503,
            "transcript": transcript,
        }

    payload = response.to_dict()
    echo.write_turn(
        user_id,
        specialist.name,
        "specialist",
        payload.get("analysis") or str(payload),
    )

    speak_text = payload.get("analysis") or payload.get("recommendation") or ""
    audio_base64 = None
    audio_mime = None
    tts_error = None

    if os.getenv("VOICE_SERVER_TTS", "false").lower() in {"1", "true", "yes"}:
        try:
            wav_bytes = text_to_speech(speak_text, voice_id=voice_id)
            audio_base64 = base64.b64encode(wav_bytes).decode("ascii")
            audio_mime = "audio/wav"
        except Exception as e:
            tts_error = str(e)
            logger.warning("TTS unavailable, client may use browser speech: %s", e)

    return {
        "transcript": transcript,
        "result": payload,
        "specialist": specialist.name,
        "audio_base64": audio_base64,
        "audio_mime": audio_mime,
        "tts_fallback": audio_base64 is None,
        "tts_error": tts_error,
    }
