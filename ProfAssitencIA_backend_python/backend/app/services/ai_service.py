"""Geração de respostas e títulos com o Llama (via Groq)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.services.groq_client import GENERIC_ERROR, AIServiceError, GroqClient

logger = logging.getLogger(__name__)

TITLE_PROMPT = (
    "Gere um título curto e objetivo para esta conversa com base na mensagem do "
    "usuário. Retorne apenas o título, sem explicações e com no máximo 8 palavras. "
    "{message}"
)
MAX_TITLE_LENGTH = 80
TRUNCATED_NOTE = (
    "\n\n*(A resposta foi cortada pelo limite de tamanho. Peça para continuar.)*"
)


class AIService:
    def __init__(self, groq: GroqClient, settings: Settings) -> None:
        self._groq = groq
        self._settings = settings

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Envia as mensagens (formato OpenAI) e devolve o texto da resposta."""
        settings = self._settings
        body = self._groq.post(
            "/chat/completions",
            purpose="resposta",
            json={
                "model": settings.groq_model,
                "messages": messages,
                "temperature": settings.temperature,
                "max_completion_tokens": settings.groq_max_tokens,
                "reasoning_format": "hidden",
                "reasoning_effort": "low",
            },
        )
        text, finish = self._extract(body)
        if not text:
            logger.error("O Groq devolveu uma resposta sem texto.")
            raise AIServiceError(GENERIC_ERROR, 502)
        return text + (TRUNCATED_NOTE if finish == "length" else "")

    def generate_title(self, first_message: str) -> str | None:
        """Título curto para uma conversa nova. Nunca levanta erro (usa o padrão)."""
        try:
            body = self._groq.post(
                "/chat/completions",
                purpose="título",
                json={
                    "model": self._settings.groq_model,
                    "messages": [
                        {"role": "user", "content": TITLE_PROMPT.format(message=first_message[:1500])}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 32,
                },
            )
        except AIServiceError:
            return None
        text, _ = self._extract(body)
        return self._clean_title(text)

    @staticmethod
    def _extract(body: dict[str, Any]) -> tuple[str | None, str | None]:
        choices = body.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            return None, None
        choice = choices[0]
        content = (choice.get("message") or {}).get("content")
        text = content.strip() if isinstance(content, str) and content.strip() else None
        return text, choice.get("finish_reason")

    @staticmethod
    def _clean_title(text: str | None) -> str | None:
        if not text:
            return None
        lines = text.strip().splitlines()
        title = lines[0].strip().strip("\"'“”*# ").strip() if lines else ""
        return title[:MAX_TITLE_LENGTH] or None
