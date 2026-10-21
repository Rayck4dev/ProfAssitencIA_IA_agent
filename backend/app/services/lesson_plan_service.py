"""Regras do assistente de planejamento docente: RAG + histórico + prompt + orçamento de tokens."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.config import Settings
from app.domain import (
    ROLE_USER,
    SOURCES_MARKER,
    TRUNCATED_RE,
    ChatTurn,
)
from app.prompts import DEFAULT_SYSTEM_PROMPT, GENERIC_SYSTEM_PROMPT, STRICT_SYSTEM_PROMPT
from app.rag.intent import parse_intent
from app.rag.store import KnowledgeBase, Retrieval
from app.rag.text import tokenize
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

# Mensagens com menos termos que isso (ex.: "e para o 6º ano?") herdam o tema das
# perguntas anteriores na hora de buscar nos documentos.
MIN_TERMS_STANDALONE = 3
_CONTINUE_RE = re.compile(r"^\s*(continu\w*|prossig\w*|segu\w+|termine|complete)\b", re.IGNORECASE)

# Estimativa de tokens (conservadora para português) e margens do orçamento.
CHARS_PER_TOKEN = 3.0
MESSAGE_OVERHEAD = 8  # tokens de formatação por mensagem
TPM_MARGIN = 250
MIN_OUTPUT_FLOOR = 600
TRUNCATION_MARK = " […]"


@dataclass
class LessonPlanResult:
    answer: str  # texto final, com a linha de documentos consultados e alertas
    retrieval: Retrieval


def estimate_tokens(*texts: str) -> int:
    return int(sum(len(t) / CHARS_PER_TOKEN + MESSAGE_OVERHEAD for t in texts))


class LessonPlanService:
    def __init__(self, ai_service: AIService, knowledge: KnowledgeBase, settings: Settings) -> None:
        self._ai = ai_service
        self._kb = knowledge
        self._settings = settings

    @property
    def rag_active(self) -> bool:
        return self._settings.rag_enabled and self._kb.available

    def prof_message(self, message: str, history: list[ChatTurn]) -> LessonPlanResult:
        """Gera a resposta para a nova mensagem do professor.

        Levanta ``AIServiceError`` se a IA falhar.
        """
        retrieval = self._retrieve_safely(message, history)
        system = self._system_prompt(retrieval)
        past = self._history_messages(history, self._history_budget(system, message))
        messages = [
            {"role": "system", "content": system},
            *past,
            {"role": "user", "content": message},
        ]
        max_tokens = self._output_budget(messages)
        logger.info(
            "IA: %d mensagem(ns), ~%d tokens de entrada, resposta de até %d tokens (contexto: %d trecho(s)).",
            len(messages), estimate_tokens(*(m["content"] for m in messages)), max_tokens, len(retrieval.hits),
        )
        raw = self._ai.chat(messages, max_tokens=max_tokens)
        return LessonPlanResult(self._compose(raw, retrieval), retrieval)

    # ------------------------------------------------------------------ RAG
    def _retrieve_safely(self, message: str, history: list[ChatTurn]) -> Retrieval:
        """A busca nos documentos nunca pode impedir a resposta: se falhar, segue sem ela."""
        try:
            return self._retrieve(message, history)
        except Exception:  # noqa: BLE001 - qualquer falha da busca vira "sem contexto"
            logger.exception("Falha na busca nos documentos; respondendo sem contexto.")
            return Retrieval()

    def _retrieve(self, message: str, history: list[ChatTurn]) -> Retrieval:
        if not self.rag_active:
            return Retrieval()
        settings = self._settings
        query = message
        short = len(tokenize(message, drop_stopwords=True)) < MIN_TERMS_STANDALONE
        if short or _CONTINUE_RE.match(message):
            previous = [t.content for t in history if t.role == ROLE_USER and not _CONTINUE_RE.match(t.content)][-2:]
            query = " ".join([*previous, message])
        # O ano/etapa citado na mensagem atual vale mais do que os das anteriores.
        intent_text = message if parse_intent(message).etapa else query
        return self._kb.search(
            query,
            intent_text=intent_text,
            k=settings.rag_top_k,
            max_chars=settings.rag_max_chars,
        )

    def _system_prompt(self, retrieval: Retrieval) -> str:
        settings = self._settings
        if not self.rag_active:
            return settings.system_prompt.strip() or GENERIC_SYSTEM_PROMPT
        base = STRICT_SYSTEM_PROMPT if settings.rag_strict else DEFAULT_SYSTEM_PROMPT
        parts = [settings.system_prompt.strip() or base]
        docs = self._kb.docs()
        if docs:
            listing = "; ".join(
                f"{d['name']} — {d['title']} ({d['scope']})" if d["scope"] else f"{d['name']} — {d['title']}"
                for d in docs
            )
            parts.append(f"DOCUMENTOS DISPONÍVEIS: {listing}.")
        if retrieval:
            parts.append(
                "CONTEXTO CURRICULAR (trechos dos documentos oficiais; cite a fonte e a página):\n\n"
                + retrieval.context_block()
            )
        elif settings.rag_strict:
            parts.append(
                "CONTEXTO CURRICULAR: nenhum trecho dos documentos foi recuperado para esta mensagem."
            )
        else:
            parts.append(
                "CONTEXTO CURRICULAR: nenhum trecho dos documentos foi recuperado para esta mensagem. "
                "Responda mesmo assim, com boas práticas pedagógicas, sem inventar códigos de habilidade."
            )
        return "\n\n".join(parts)

    # ------------------------------------------------------ orçamento de tokens
    def _history_budget(self, system: str, message: str) -> int:
        """Quantos caracteres de histórico cabem sem tirar o espaço mínimo da resposta."""
        settings = self._settings
        if settings.groq_tpm_limit <= 0:
            return settings.history_max_chars
        free = (
            settings.groq_tpm_limit
            - settings.groq_min_output_tokens
            - TPM_MARGIN
            - estimate_tokens(system, message)
        )
        return max(0, min(settings.history_max_chars, int(free * CHARS_PER_TOKEN)))

    def _output_budget(self, messages: list[dict[str, str]]) -> int:
        """Quanto de resposta pedir: o máximo que couber no limite por minuto."""
        settings = self._settings
        if settings.groq_tpm_limit <= 0:
            return settings.groq_max_tokens
        room = settings.groq_tpm_limit - estimate_tokens(*(m["content"] for m in messages)) - TPM_MARGIN
        return max(MIN_OUTPUT_FLOOR, min(settings.groq_max_tokens, room))

    # ------------------------------------------------------------- histórico
    def _history_messages(self, history: list[ChatTurn], budget: int) -> list[dict[str, str]]:
        """Histórico mais recente que cabe no orçamento (sem rodapés nem avisos de corte)."""
        selected: list[dict[str, str]] = []
        used = 0
        for turn in reversed(history):
            content = turn.content.split(SOURCES_MARKER, 1)[0].strip()
            was_cut = bool(TRUNCATED_RE.search(content))
            content = TRUNCATED_RE.sub("", content).strip()
            if not content:
                continue
            remaining = budget - used
            if len(content) > remaining:
                if selected:
                    break
                # A resposta mais recente é essencial ("deixe mais curto", "continue").
                # Se ela foi cortada, o que importa é o FIM (de onde continuar).
                keep = max(remaining, 1500)
                content = (TRUNCATION_MARK.lstrip() + " " + content[-keep:].lstrip()) if was_cut \
                    else content[:keep].rstrip() + TRUNCATION_MARK
            selected.append({"role": turn.role, "content": content})
            used += len(content)
        selected.reverse()
        return selected

    # --------------------------------------------------------- pós-processo
    def _compose(self, raw: str, retrieval: Retrieval) -> str:
        """Acrescenta os documentos consultados e alerta sobre códigos inexistentes."""
        unknown = self._kb.unknown_codes(raw) if self.rag_active else []
        if not retrieval and not unknown:
            return raw
        sources = retrieval.sources_line() or "nenhum trecho relevante encontrado"
        text = f"{raw}{SOURCES_MARKER} {sources}"
        if unknown:
            names = ", ".join(f"`{c}`" for c in unknown)
            plural = len(unknown) > 1
            text += (
                f"\n\n> ⚠️ **Confira:** {'os códigos' if plural else 'o código'} {names} "
                f"não {'aparecem' if plural else 'aparece'} nos documentos carregados "
                f"— a IA pode {'tê-los' if plural else 'tê-lo'} inventado. "
                "Use apenas códigos que constem na BNCC ou no RCSEERO."
            )
        return text
