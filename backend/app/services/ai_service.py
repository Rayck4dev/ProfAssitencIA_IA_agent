"""Geração de respostas e títulos com o modelo de texto (via Groq).

Cuida de um detalhe importante dos modelos de **raciocínio** (gpt-oss, qwen3): os
tokens que o modelo "pensa" contam dentro de ``max_completion_tokens``. Com um limite
apertado ele gasta tudo raciocinando e devolve **texto vazio**. Por isso:

* o limite padrão é folgado e o esforço de raciocínio é baixo;
* se mesmo assim vier vazio por falta de espaço, o pedido é refeito com mais espaço;
* parâmetros de raciocínio só são enviados aos modelos que os aceitam.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.domain import TRUNCATED_NOTE
from app.services.groq_client import GENERIC_ERROR, AIServiceError, GroqClient

logger = logging.getLogger(__name__)

TITLE_PROMPT = (
    "Gere um título curto e objetivo para esta conversa com base na mensagem do "
    "usuário. Retorne apenas o título, sem explicações e com no máximo 8 palavras. "
    "{message}"
)
MAX_TITLE_LENGTH = 80
MAX_ATTEMPTS = 4  # tentativas de ajuste (espaço, parâmetro recusado) por pergunta
MIN_TOKENS = 400  # abaixo disso não vale a pena tentar de novo
OVERFLOW_MARGIN = 64


def reasoning_params(model: str, effort: str) -> dict[str, Any]:
    """Parâmetros de raciocínio aceitos pelo modelo (vazio para modelos comuns).

    Conforme a documentação da Groq: no gpt-oss ``reasoning_format`` NÃO é suportado
    (usa-se ``include_reasoning``), e os dois são mutuamente exclusivos.
    """
    name = model.lower()
    if name.startswith("openai/gpt-oss") and "safeguard" not in name:
        level = effort if effort in {"low", "medium", "high"} else "low"
        return {"include_reasoning": False, "reasoning_effort": level}
    if "qwen3" in name:
        level = effort if effort in {"none", "default", "low", "medium", "high"} else "low"
        return {"reasoning_format": "hidden", "reasoning_effort": level}
    return {}


class AIService:
    def __init__(self, groq: GroqClient, settings: Settings) -> None:
        self._groq = groq
        self._settings = settings

    # ------------------------------------------------------------------ chat
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        purpose: str = "resposta",
        mark_truncated: bool = True,
    ) -> str:
        """Envia as mensagens (formato OpenAI) e devolve o texto da resposta."""
        settings = self._settings
        limit = max_tokens or settings.groq_max_tokens
        params = reasoning_params(settings.groq_model, settings.groq_reasoning_effort)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            payload: dict[str, Any] = {
                "model": settings.groq_model,
                "messages": messages,
                "temperature": settings.temperature,
                "max_completion_tokens": limit,
                **params,
            }
            try:
                body = self._groq.post("/chat/completions", purpose=purpose, json=payload)
            except AIServiceError as exc:
                if exc.status_code == 413 and exc.overflow and attempt < MAX_ATTEMPTS:
                    smaller = limit - exc.overflow - OVERFLOW_MARGIN
                    if smaller >= MIN_TOKENS:
                        logger.warning("Pedido acima do limite por minuto; reduzindo a resposta de %d para %d tokens.",
                                       limit, smaller)
                        limit = smaller
                        continue
                if params and _mentions_reasoning(exc.detail):
                    logger.warning("O modelo %s recusou parâmetros de raciocínio; repetindo sem eles.",
                                   settings.groq_model)
                    params = {}
                    continue
                raise

            text, finish, reasoning_tokens = self._extract(body)
            if text:
                self._log_usage(body, limit, reasoning_tokens)
                return text + (TRUNCATED_NOTE if finish == "length" and mark_truncated else "")

            logger.warning(
                "O modelo devolveu texto vazio (finish_reason=%s, limite=%d, raciocínio=%s).",
                finish, limit, reasoning_tokens,
            )
            if finish == "length" and attempt < MAX_ATTEMPTS:
                # O raciocínio consumiu todo o espaço: dá mais espaço e pede menos raciocínio.
                if "reasoning_effort" in params:
                    params = {**params, "reasoning_effort": "low"}
                limit = limit + max(limit // 2, 800)
                continue
            break

        raise AIServiceError(
            "A IA gastou o limite pensando e não chegou a escrever a resposta. "
            "Tente de novo ou reformule o pedido.",
            502,
        )

    # ---------------------------------------------------------------- título
    def generate_title(self, first_message: str) -> str | None:
        """Título curto feito pela IA (opcional). Nunca levanta erro."""
        try:
            text = self.chat(
                [{"role": "user", "content": TITLE_PROMPT.format(message=first_message[:1500])}],
                max_tokens=400,  # modelos de raciocínio precisam de folga mesmo para um título
                purpose="título",
                mark_truncated=False,
            )
        except AIServiceError as exc:
            logger.warning("Não foi possível gerar o título com a IA: %s", exc.message)
            return None
        return self._clean_title(text)

    # --------------------------------------------------------------- internos
    @staticmethod
    def _extract(body: dict[str, Any]) -> tuple[str | None, str | None, int | None]:
        choices = body.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            return None, None, None
        choice = choices[0]
        content = (choice.get("message") or {}).get("content")
        text = content.strip() if isinstance(content, str) and content.strip() else None
        details = (body.get("usage") or {}).get("completion_tokens_details") or {}
        reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
        return text, choice.get("finish_reason"), reasoning

    @staticmethod
    def _log_usage(body: dict[str, Any], limit: int, reasoning: int | None) -> None:
        usage = body.get("usage") or {}
        if usage:
            logger.info("Groq: entrada %s, saída %s tokens (raciocínio %s) de até %d.",
                        usage.get("prompt_tokens"), usage.get("completion_tokens"),
                        reasoning if reasoning is not None else "n/d", limit)

    @staticmethod
    def _clean_title(text: str | None) -> str | None:
        if not text:
            return None
        lines = text.strip().splitlines()
        title = lines[0].strip().strip("\"'“”*# ").strip() if lines else ""
        return title[:MAX_TITLE_LENGTH] or None


def _mentions_reasoning(detail: str) -> bool:
    lowered = (detail or "").lower()
    return "reasoning" in lowered
