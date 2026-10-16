"""Regras do assistente de planejamento docente: RAG + histórico + prompt."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings
from app.domain import (
    ROLE_ASSISTANT,
    ROLE_USER,
    SOURCES_MARKER,
    ChatTurn,
)
from app.prompts import DEFAULT_SYSTEM_PROMPT, GENERIC_SYSTEM_PROMPT
from app.rag.intent import parse_intent
from app.rag.store import KnowledgeBase, Retrieval
from app.rag.text import tokenize
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

# Mensagens com menos termos que isso (ex.: "e para o 6º ano?") herdam o tema
# das perguntas anteriores na hora de buscar nos documentos.
MIN_TERMS_STANDALONE = 3
CHARS_PER_TOKEN = 3.3  # estimativa para o log


@dataclass
class LessonPlanResult:
    answer: str  # texto final, com a linha de documentos consultados e alertas
    retrieval: Retrieval


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

        Levanta ``AIServiceError`` se o Groq falhar.
        """
        retrieval = self._retrieve(message, history)
        system = self._system_prompt(retrieval)
        past = self._history_messages(history)
        messages = [
            {"role": "system", "content": system},
            *past,
            {"role": "user", "content": message},
        ]
        size = len(system) + sum(len(m["content"]) for m in past) + len(message)
        logger.info(
            "Groq: %d mensagem(ns), ~%d tokens de entrada (contexto: %d trecho(s)).",
            len(messages), size / CHARS_PER_TOKEN, len(retrieval.hits),
        )
        raw = self._ai.chat(messages)
        return LessonPlanResult(self._compose(raw, retrieval), retrieval)

    # ------------------------------------------------------------------ RAG
    def _retrieve(self, message: str, history: list[ChatTurn]) -> Retrieval:
        if not self.rag_active:
            return Retrieval()
        settings = self._settings
        query = message
        if len(tokenize(message, drop_stopwords=True)) < MIN_TERMS_STANDALONE:
            previous = [t.content for t in history if t.role == ROLE_USER][-2:]
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
        if not self.rag_active:
            return self._settings.system_prompt.strip() or GENERIC_SYSTEM_PROMPT
        parts = [self._settings.system_prompt.strip() or DEFAULT_SYSTEM_PROMPT]
        docs = self._kb.docs()
        if docs:
            listing = "; ".join(f"{d['name']} — {d['title']} ({d['scope']})" if d["scope"]
                                else f"{d['name']} — {d['title']}" for d in docs)
            parts.append(f"DOCUMENTOS DISPONÍVEIS: {listing}.")
        if retrieval:
            parts.append(
                "CONTEXTO CURRICULAR (trechos dos documentos oficiais; cite a fonte e a página):\n\n"
                + retrieval.context_block()
            )
        else:
            parts.append(
                "CONTEXTO CURRICULAR: nenhum trecho dos documentos foi recuperado para esta mensagem."
            )
        return "\n\n".join(parts)

    # ------------------------------------------------------------- histórico
    def _history_messages(self, history: list[ChatTurn]) -> list[dict[str, str]]:
        """Histórico mais recente que cabe no limite de caracteres (sem os rodapés)."""
        budget = self._settings.history_max_chars
        selected: list[dict[str, str]] = []
        used = 0
        for turn in reversed(history):
            content = turn.content.split(SOURCES_MARKER, 1)[0].strip()
            if not content:
                continue
            remaining = budget - used
            if len(content) > remaining:
                if selected:
                    break
                # A resposta mais recente é essencial para pedidos como "deixe mais
                # curto": mantém o início (identificação e habilidades).
                content = content[: max(remaining, 0)].rstrip() + " […]"
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
