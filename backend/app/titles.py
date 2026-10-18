"""Título automático da conversa, feito localmente (sem chamar a IA).

Antes o título vinha de uma segunda chamada à IA logo depois da resposta. Isso
falhava em silêncio quando o modelo gastava o limite raciocinando (texto vazio) ou
quando o limite por minuto já estava consumido pela resposta. Gerar o título aqui é
instantâneo, não gasta cota e funciona sempre.
"""

from __future__ import annotations

import re

from app.domain import DEFAULT_TITLE
from app.rag.intent import parse_intent
from app.rag.text import strip_accents

MAX_LENGTH = 70

# (palavras-chave sem acento, rótulo). A ordem importa: o mais específico primeiro.
_KINDS = [
    (("sequencia didatica",), "Sequência didática"),
    (("plano de aula", "plano de ensino", "planejamento de aula", "plano de estudo"), "Plano de aula"),
    (("atividade avaliativa",), "Atividade avaliativa"),
    (("avaliacao", "prova", "questoes", "simulado"), "Avaliação"),
    (("aula de revisao", "revisao"), "Aula de revisão"),
    (("projeto",), "Projeto"),
    (("adaptar", "adaptacao"), "Adaptação"),
    (("atividade", "exercicio", "exercicios"), "Atividade"),
    (("plano",), "Plano de aula"),
    (("aula",), "Aula"),
]

_TOPIC_RE = re.compile(
    r"\b(?:sobre|acerca de|a respeito de|tema|assunto)\s*[:\-]?\s+(.+?)"
    r"(?=[,.;:!?\n]|\s+(?:com|para|em|no|na|nos|nas|durante|usando|utilizando|de\s+\d+)\b|$)",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"\[[^\]\n]*\]")
_LEADING_ARTICLE_RE = re.compile(r"^(?:o|a|os|as|um|uma)\s+", re.IGNORECASE)
_DANGLING = {"de", "do", "da", "dos", "das", "e", "o", "a", "os", "as", "no", "na", "nos", "nas",
             "em", "com", "para", "por", "um", "uma"}


def make_title(message: str) -> str:
    """Resume o primeiro pedido em um título curto (ex.: "Plano de aula · Matemática · 5º ano · frações")."""
    text = re.sub(r"\s+", " ", _PLACEHOLDER_RE.sub(" ", message or "")).strip()
    if not text:
        return DEFAULT_TITLE

    plain = strip_accents(text).lower()
    kind = next((label for keys, label in _KINDS if any(k in plain for k in keys)), None)

    intent = parse_intent(text)
    where: list[str] = [*intent.components]
    if intent.anos:
        where.append(", ".join(f"{y}º" for y in intent.anos) + " ano")
    elif intent.etapa == "EM":
        where.append("Ensino Médio")
    elif intent.etapa == "EI":
        where.append("Educação Infantil")

    topic = ""
    if match := _TOPIC_RE.search(text):
        words = _LEADING_ARTICLE_RE.sub("", match.group(1).strip()).split()[:6]
        while words and words[-1].lower() in _DANGLING:  # não termina em "do", "e"...
            words.pop()
        topic = " ".join(words).strip(" .,;:-")

    parts = [p for p in (kind, " · ".join(where) if where else "", topic) if p]
    if not parts:
        words = re.sub(r"[^\w\sºª°-]", " ", text, flags=re.UNICODE).split()
        parts = [" ".join(words[:7])] if words else [DEFAULT_TITLE]

    title = " · ".join(parts)
    title = title[0].upper() + title[1:]
    if len(title) > MAX_LENGTH:
        title = title[: MAX_LENGTH - 1].rsplit(" ", 1)[0].rstrip(" ·,;:") + "…"
    return title
