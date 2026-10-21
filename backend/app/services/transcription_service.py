"""Transcrição de voz com o Whisper (via Groq)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.services.groq_client import AIServiceError, GroqClient

logger = logging.getLogger(__name__)

# tipo MIME do MediaRecorder -> extensão que o Groq reconhece
_EXTENSIONS = {
    "audio/webm": "webm", "video/webm": "webm",
    "audio/ogg": "ogg", "application/ogg": "ogg",
    "audio/mp4": "mp4", "video/mp4": "mp4", "audio/x-m4a": "m4a", "audio/m4a": "m4a",
    "audio/mpeg": "mp3", "audio/mp3": "mp3",
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
    "audio/flac": "flac",
}
# Critério do próprio Whisper para descartar trechos de silêncio/ruído
# (evita "Obrigado por assistir!" quando a gravação está quase muda).
NO_SPEECH_THRESHOLD = 0.6
LOGPROB_THRESHOLD = -1.0


class TranscriptionService:
    def __init__(self, groq: GroqClient, settings: Settings) -> None:
        self._groq = groq
        self._settings = settings

    def transcribe(self, audio: bytes, content_type: str) -> str:
        mime = (content_type or "").split(";")[0].strip().lower()
        extension = _EXTENSIONS.get(mime)
        if extension is None:
            raise AIServiceError(f"Formato de áudio não suportado: {mime or 'desconhecido'}.", 415)

        body = self._groq.post(
            "/audio/transcriptions",
            purpose="transcrição",
            data={
                "model": self._settings.groq_whisper_model,
                "language": self._settings.transcription_language,
                "response_format": "verbose_json",
                "temperature": "0",
            },
            files={"file": (f"audio.{extension}", audio, mime)},
        )
        return self._text_from(body)

    @staticmethod
    def _text_from(body: dict[str, Any]) -> str:
        segments = body.get("segments")
        if isinstance(segments, list) and segments:
            kept = [
                str(s.get("text", "")).strip()
                for s in segments
                if isinstance(s, dict)
                and not (
                    s.get("no_speech_prob", 0) > NO_SPEECH_THRESHOLD
                    and s.get("avg_logprob", 0) < LOGPROB_THRESHOLD
                )
            ]
            return " ".join(t for t in kept if t).strip()
        return str(body.get("text", "")).strip()
