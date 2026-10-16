"""Tipos simples compartilhados entre as camadas."""

from __future__ import annotations

from typing import NamedTuple

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
DEFAULT_TITLE = "Nova conversa"


class ChatTurn(NamedTuple):
    """Uma mensagem do histórico (``role`` é ``user`` ou ``assistant``)."""

    role: str
    content: str

# Linha que o backend acrescenta ao fim das respostas. É retirada do histórico
# antes de reenviá-lo à IA, para não gastar tokens nem confundir o modelo.
SOURCES_MARKER = "\n\n---\n**Documentos consultados:**"
