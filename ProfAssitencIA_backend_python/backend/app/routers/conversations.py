"""Endpoints do histórico de conversas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_conversation_service
from app.schemas import (
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    UpdateConversationRequest,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])

NOT_FOUND = "Conversa nao encontrada"


@router.get("", response_model=ConversationListOut, summary="Lista as conversas da instalação")
def list_conversations(
    installation_id: str = Query(...),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ConversationListOut:
    items = conversations.list_for_installation(installation_id)
    return ConversationListOut(
        conversations=[ConversationOut.model_validate(c) for c in items]
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailOut,
    summary="Consulta uma conversa e suas mensagens",
    responses={404: {"description": NOT_FOUND}},
)
def get_conversation(
    conversation_id: int,
    installation_id: str = Query(...),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ConversationDetailOut:
    conversation = conversations.get(conversation_id, installation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return ConversationDetailOut.model_validate(conversation)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationOut,
    summary="Atualiza o título de uma conversa",
    responses={400: {"description": "Título vazio"}, 404: {"description": NOT_FOUND}},
)
def update_conversation_title(
    conversation_id: int,
    request: UpdateConversationRequest,
    conversations: ConversationService = Depends(get_conversation_service),
) -> ConversationOut:
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Titulo vazio")

    conversation = conversations.get(conversation_id, request.installation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return ConversationOut.model_validate(conversations.rename(conversation, title))


@router.delete(
    "/{conversation_id}",
    response_model=ConversationOut,
    summary="Exclui uma conversa (e suas mensagens)",
    responses={404: {"description": NOT_FOUND}},
)
def delete_conversation(
    conversation_id: int,
    installation_id: str = Query(...),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ConversationOut:
    conversation = conversations.get(conversation_id, installation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    deleted = ConversationOut.model_validate(conversation)  # copia antes de apagar
    conversations.delete(conversation)
    return deleted
