"""Modelos de entrada e saída da API (Pydantic).

Contrato mantido com o frontend:
* requisições usam ``snake_case`` (``installation_id``, ``conversation_id``);
* respostas usam ``camelCase`` (``conversationId``, ``updatedAt``).
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ----------------------------------------------------------------- requisições
class LessonPlanRequest(BaseModel):
    """Corpo de ``POST /api/lessonplan``.

    Campos extras enviados pelo frontend (como ``messages``) são ignorados: o
    histórico usado na IA vem sempre do banco de dados.
    """

    installation_id: str
    conversation_id: str | int | None = Field(
        default=None,
        description="Omitir (ou null) para iniciar uma nova conversa.",
    )
    message: str


class UpdateConversationRequest(BaseModel):
    installation_id: str
    title: str = Field(max_length=200)


# ------------------------------------------------------------------- respostas
class LessonPlanResponse(CamelModel):
    response: str
    conversation_id: str


class MessageOut(CamelModel):
    id: int
    conversation_id: int
    role: str
    content: str


class ConversationOut(CamelModel):
    id: int
    title: str | None
    installation_id: str
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def _as_utc(cls, value: datetime) -> datetime:
        # O banco guarda UTC sem fuso; sem o "Z" o navegador interpretaria
        # a data como horário local e mostraria a hora errada.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class ConversationListOut(CamelModel):
    conversations: list[ConversationOut]


class KnowledgeBaseOut(CamelModel):
    available: bool
    documents: int
    chunks: int
    names: list[str] = []


class HealthOut(CamelModel):
    status: str
    ai_configured: bool
    version: str
    model: str
    knowledge_base: KnowledgeBaseOut


class TranscriptionOut(CamelModel):
    text: str
