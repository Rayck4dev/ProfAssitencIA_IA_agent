"""Dependências injetadas nas rotas (equivalente ao AddScoped do ASP.NET)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.rag.store import KnowledgeBase
from app.services.ai_service import AIService
from app.services.conversation_service import ConversationService
from app.services.groq_client import GroqClient
from app.services.lesson_plan_service import LessonPlanService
from app.services.transcription_service import TranscriptionService


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_groq_client(request: Request) -> GroqClient:
    return GroqClient(request.app.state.http_client, request.app.state.settings)


def get_knowledge_base(request: Request) -> KnowledgeBase:
    return request.app.state.knowledge_base


def get_ai_service(
    request: Request, groq: GroqClient = Depends(get_groq_client)
) -> AIService:
    return AIService(groq, request.app.state.settings)


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    return ConversationService(db)


def get_lesson_plan_service(
    request: Request,
    ai: AIService = Depends(get_ai_service),
    knowledge: KnowledgeBase = Depends(get_knowledge_base),
) -> LessonPlanService:
    return LessonPlanService(ai, knowledge, request.app.state.settings)


def get_transcription_service(
    request: Request, groq: GroqClient = Depends(get_groq_client)
) -> TranscriptionService:
    return TranscriptionService(groq, request.app.state.settings)
