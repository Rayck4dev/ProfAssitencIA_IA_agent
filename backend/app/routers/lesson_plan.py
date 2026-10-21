"""Endpoint que conversa com a IA."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import (
    get_ai_service,
    get_conversation_service,
    get_lesson_plan_service,
)
from app.schemas import LessonPlanRequest, LessonPlanResponse
from app.titles import make_title
from app.services.ai_service import AIService
from app.services.conversation_service import ConversationService
from app.services.lesson_plan_service import LessonPlanService

router = APIRouter(prefix="/api/lessonplan", tags=["LessonPlan"])


@router.post(
    "",
    response_model=LessonPlanResponse,
    summary="Envia uma mensagem e gera a resposta da IA (com RAG nos documentos curriculares)",
    responses={
        400: {"description": "Mensagem vazia ou conversation_id inválido"},
        404: {"description": "Conversa não encontrada para esta instalação"},
        429: {"description": "Limite de uso da IA atingido"},
        502: {"description": "A IA (Groq) não devolveu uma resposta"},
    },
)
def generate_lesson_plan(
    request: LessonPlanRequest,
    http_request: Request,
    conversations: ConversationService = Depends(get_conversation_service),
    lesson_plans: LessonPlanService = Depends(get_lesson_plan_service),
    ai: AIService = Depends(get_ai_service),
) -> LessonPlanResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    conversation = None
    history = []

    if request.conversation_id is not None:
        try:
            conversation_id = int(str(request.conversation_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Erro de conversao") from None

        conversation = conversations.get(conversation_id, request.installation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversa nao encontrada")
        history = conversations.get_history(conversation.id)

    # Levanta AIServiceError (tratado em main.py) se a IA falhar: nada é gravado.
    result = lesson_plans.prof_message(request.message, history)

    title = None
    if conversation is None:
        # Título local e instantâneo; a IA só entra se TITLE_WITH_AI=true (e nunca bloqueia).
        if http_request.app.state.settings.title_with_ai:
            title = ai.generate_title(request.message)
        title = title or make_title(request.message)
    conversation = conversations.save_exchange(
        installation_id=request.installation_id,
        user_message=request.message,
        assistant_message=result.answer,
        conversation=conversation,
        title=title,
    )
    return LessonPlanResponse(response=result.answer, conversation_id=str(conversation.id))
