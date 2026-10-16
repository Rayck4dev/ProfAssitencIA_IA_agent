"""Cliente HTTP do Groq (API compatível com a da OpenAI), com repetição e erros claros."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

GENERIC_ERROR = "Não foi possível obter uma resposta da IA."
RETRYABLE_STATUS = {500, 502, 503, 504}


class AIServiceError(Exception):
    """Falha ao falar com o Groq. ``message`` é seguro para mostrar ao usuário."""

    def __init__(self, message: str = GENERIC_ERROR, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GroqClient:
    def __init__(self, client: httpx.Client, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @property
    def configured(self) -> bool:
        return bool(self._settings.groq_api_key)

    def post(
        self,
        path: str,
        *,
        purpose: str,
        json: dict[str, Any] | None = None,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> dict[str, Any]:
        """POST autenticado. Devolve o JSON ou levanta ``AIServiceError``."""
        settings = self._settings
        if not settings.groq_api_key:
            logger.error("Chave do Groq não configurada. Defina GROQ_API_KEY no arquivo .env.")
            raise AIServiceError(
                "A IA não está configurada: falta a GROQ_API_KEY no arquivo .env.", 502
            )

        url = f"{settings.groq_base_url.rstrip('/')}{path}"
        headers = {"Authorization": f"Bearer {settings.groq_api_key}"}

        for attempt in range(1, settings.groq_max_attempts + 1):
            last = attempt >= settings.groq_max_attempts
            try:
                response = self._client.post(
                    url, headers=headers, json=json, data=data, files=files
                )
            except httpx.HTTPError as exc:
                logger.error("Falha de comunicação com o Groq (%s): %s", purpose, type(exc).__name__)
                raise AIServiceError(GENERIC_ERROR, 502) from None

            if response.is_success:
                try:
                    body = response.json()
                except ValueError:
                    logger.error("Resposta do Groq (%s) não é um JSON válido.", purpose)
                    raise AIServiceError(GENERIC_ERROR, 502) from None
                if isinstance(body, dict):
                    return body
                raise AIServiceError(GENERIC_ERROR, 502)

            status = response.status_code

            if status == 429:  # limite de taxa (por minuto ou por dia)
                wait = _retry_after(response)
                if wait is None:
                    wait = settings.groq_retry_delay_seconds * attempt
                if wait > settings.groq_max_retry_wait_seconds or last:
                    logger.warning("Groq: limite de uso atingido (%s); espera sugerida %.0fs.", purpose, wait)
                    raise AIServiceError(
                        f"Limite de uso da IA atingido. Tente novamente em {_human(wait)}.", 429
                    )
                logger.warning("Groq: limite de taxa (%s); aguardando %.1fs.", purpose, wait)
                time.sleep(wait)
                continue

            if status in RETRYABLE_STATUS and not last:
                logger.warning("Groq indisponível (HTTP %s) ao gerar %s; tentativa %d/%d.",
                               status, purpose, attempt, settings.groq_max_attempts)
                time.sleep(settings.groq_retry_delay_seconds * attempt)
                continue

            logger.error("Erro do Groq ao gerar %s: HTTP %s — %s", purpose, status, response.text[:500])
            if status in (401, 403):
                raise AIServiceError(
                    "O Groq recusou a chave. Confira a GROQ_API_KEY no arquivo .env.", 502
                )
            if status == 413:
                raise AIServiceError(
                    "A conversa ficou grande demais para o limite do modelo. "
                    "Inicie uma nova conversa.", 413
                )
            raise AIServiceError(GENERIC_ERROR, 502)

        raise AIServiceError(GENERIC_ERROR, 502)


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["retry-after"])
    except (KeyError, ValueError):
        return None


def _human(seconds: float) -> str:
    seconds = max(1, round(seconds))
    if seconds < 90:
        return f"{seconds} segundos"
    return f"{round(seconds / 60)} minutos"
