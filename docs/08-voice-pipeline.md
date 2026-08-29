# 08 — Voice Pipeline

The voice pipeline enables spoken interaction with AI specialists: record audio → transcribe → get a specialist answer → hear it spoken back.

---

## Module Structure

```
voice/
├── __init__.py      # Package marker
├── service.py       # ask_with_voice() — full orchestration
├── stt.py           # speech_to_text() — Gemini multimodal STT
└── tts.py           # text_to_speech() — Google Cloud TTS
```

---

## Pipeline Overview

```
User records audio (browser)
        │
        │  POST /api/voice/ask/  (multipart: audio file, mime_type, specialist)
        ▼
voice.service.ask_with_voice()
        │
        ├─── 1. speech_to_text(audio, mime_type)
        │         └── Sends audio bytes to Gemini with prompt:
        │              "Transcribe this audio. Return only the spoken words."
        │         └── Returns: transcript string
        │
        ├─── 2. Check permissions (user_can_access)
        │
        ├─── 3. Load Echo context (get_context + get_relevant_facts)
        │
        ├─── 4. Build EchoContext(response_style="voice", stream=False)
        │
        ├─── 5. echo.write_turn(user, specialist, "user", transcript)
        │
        ├─── 6. specialist.handle(transcript, context)
        │         └── Gemini call with style="voice":
        │              "At most 2 short sentences. Plain speech. One key number."
        │         └── Returns: SpecialistResponse
        │
        ├─── 7. echo.write_turn(user, specialist, "specialist", response_text)
        │
        └─── 8. text_to_speech(response_text, voice_id)
                  └── Google Cloud TTS → WAV bytes → base64 encoded
                  └── OR: tts_fallback=true (client uses browser speech synthesis)
        │
        ▼
JSON response: { transcript, result, audio_base64, tts_fallback, ... }
```

---

## Speech-to-Text ([`voice/stt.py`](../voice/stt.py))

Uses **Google Gemini** (multimodal) to transcribe audio.

```python
speech_to_text(audio: bytes, mime_type: str = "audio/webm") -> str
```

The audio bytes are sent as inline data to Gemini with a transcription-focused prompt. Supports any MIME type Gemini accepts (WebM, WAV, OGG, MP4, FLAC, etc.).

**Pros:** No separate STT service key needed — reuses the existing `GEMINI_API_KEY`.  
**Cons:** Slightly higher latency than dedicated STT; quality depends on Gemini's multimodal capabilities.

---

## Text-to-Speech ([`voice/tts.py`](../voice/tts.py))

Uses **Google Cloud Text-to-Speech** to synthesize speech.

```python
text_to_speech(text: str, voice_id: str | None = None) -> bytes  # returns WAV bytes
```

Enabled only when `VOICE_SERVER_TTS=true` in the backend `.env`.

### Available voice IDs
The function accepts any valid Google Cloud TTS voice name (e.g., `en-US-Wavenet-D`, `en-IN-Neural2-A`). The default is configured in `tts.py`.

### Browser TTS fallback
When `VOICE_SERVER_TTS=false` (the default):
- `audio_base64` in the response is `null`.
- `tts_fallback` is `true`.
- The frontend uses the [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis) (`window.speechSynthesis`) to speak the response text.

---

## Voice Response Style

When a specialist is called via voice, `response_style` is set to `"voice"`. This changes the Gemini prompt style rules:

**Voice style (injected into prompt):**
```
- At most 2 short sentences.
- Plain speech only. No markdown, no bullets, no emoji, no section headers.
- One key number + one comparison or action. Nothing else.
```

This keeps spoken responses natural and brief. All seven registered specialists support the voice route (the `voice_enabled = True` default on `BaseSpecialist`), including Ledger for spoken reconciliation summaries.

---

## API Endpoint

```
POST /api/voice/ask/
Content-Type: multipart/form-data

Fields:
  audio      (file)    — recorded audio blob
  mime_type  (string)  — MIME type (default: audio/webm)
  specialist (string)  — target specialist (default: Nova)
  voice_id   (string)  — optional TTS voice override
```

**Auth required:** Yes (`IsAuthenticated`)

**Default specialist:** Nova (`voice/service.py` line: `DEFAULT_VOICE_SPECIALIST = "Nova"`)

To change the default voice specialist, update `DEFAULT_VOICE_SPECIALIST` in `voice/service.py`.

---

## Frontend Integration

The Chat page's `AssistantPresence` component handles:
- Toggling the microphone on/off.
- Recording audio via the browser's `MediaRecorder` API.
- Posting to `/api/voice/ask/`.
- Playing the returned `audio_base64` WAV (or falling back to browser TTS).
- Animating the presence indicator between `listening`, `thinking`, and `speaking` states.

---

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `VOICE_SERVER_TTS` | `false` | Set to `true` to enable Google Cloud TTS |
| `GEMINI_API_KEY` | — | Used for both STT (Gemini multimodal) and LLM calls |
| `GEMINI_MODEL` | — | Model used for STT transcription and specialist answers |

No additional environment variables are needed for browser-TTS fallback mode.

---

## Extending Voice to Other Specialists

By default, all `BaseSpecialist` subclasses have `voice_enabled = True`. The voice endpoint currently only uses Nova as the default, but any specialist can be targeted via the `specialist` field in the request. To change the default or restrict voice access, update `voice/service.py`.
