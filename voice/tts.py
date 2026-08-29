"""Text-to-speech via Gemini TTS (google-genai Interactions API)."""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import wave

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "Kore"
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"


def _clean_for_speech(text: str, max_chars: int = 360) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"[#*_`>|]", " ", text)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return cleaned


def _pcm_to_wav(pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def text_to_speech(text: str, voice_id: str | None = None) -> bytes:
    """Return WAV bytes for spoken text.

    Raises on failure so callers can fall back to browser TTS.
    """
    spoken = _clean_for_speech(text)
    if not spoken:
        raise ValueError("No speakable text")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    voice = voice_id or os.getenv("VOICE_TTS_VOICE", DEFAULT_VOICE)
    model = os.getenv("VOICE_TTS_MODEL", DEFAULT_TTS_MODEL)

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required for TTS. Run: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)

    # Prefer Interactions TTS API; fall back to generate_content speech modality.
    try:
        interaction = client.interactions.create(
            model=model,
            input=f"Speak clearly and professionally as a financial advisor: {spoken}",
            response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": voice}]},
        )
        audio_b64 = getattr(getattr(interaction, "output_audio", None), "data", None)
        if not audio_b64:
            raise RuntimeError("TTS response missing audio data")
        pcm = base64.b64decode(audio_b64)
        return _pcm_to_wav(pcm)
    except Exception as interactions_err:
        logger.warning(
            "Interactions TTS failed (%s); trying generate_content speech",
            interactions_err,
        )

    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=f"Speak clearly and professionally as a financial advisor: {spoken}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )

    try:
        inline = response.candidates[0].content.parts[0].inline_data
        pcm = inline.data
        if isinstance(pcm, str):
            pcm = base64.b64decode(pcm)
        return _pcm_to_wav(pcm)
    except Exception as exc:
        logger.exception("generate_content TTS parse failed")
        raise RuntimeError("Unable to synthesize speech") from exc
