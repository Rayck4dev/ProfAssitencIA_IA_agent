"""Tipos simples compartilhados entre as camadas."""

from __future__ import annotations

import re
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


# Aviso acrescentado quando o modelo para por limite de tamanho. O frontend o troca
# por um botão "Continuar"; ele também é retirado do histórico reenviado à IA.
TRUNCATED_NOTE = "\n\n*(Resposta cortada pelo limite de tamanho. Clique em “Continuar” para seguir.)*"
TRUNCATED_RE = re.compile(r"\s*\*\(Resposta cortada pelo limite de tamanho[^)]*\)\*\s*$")
