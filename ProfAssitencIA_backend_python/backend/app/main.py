"""Criação da aplicação FastAPI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from app import __version__
from app.config import Settings, get_settings
from app.database import build_engine, build_session_factory, create_tables
from app.rag.store import KnowledgeBase
from app.routers import conversations, lesson_plan, transcribe
from app.schemas import HealthOut, KnowledgeBaseOut
from app.services.groq_client import AIServiceError

logger = logging.getLogger("app")


class CaseInsensitiveApiPaths:
    """Faz as rotas ``/api/...`` ignorarem maiúsculas/minúsculas.

    O ASP.NET fazia isso por padrão e o frontend depende disso: ele chama
    ``/api/LessonPlan`` e ``/api/conversations``.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].lower().startswith("/api/"):
            scope = dict(scope)
            scope["path"] = scope["path"].lower()
            if scope.get("raw_path"):
                scope["raw_path"] = scope["raw_path"].lower()
        await self.app(scope, receive, send)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # O httpx registra cada requisição em INFO; é só ruído no console.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app(
    settings: Settings | None = None,
    http_client: httpx.Client | None = None,
) -> FastAPI:
    """Monta a aplicação. ``http_client`` permite trocar o cliente HTTP nos testes."""
    settings = settings or get_settings()
    _configure_logging(settings.log_level)

    engine = build_engine(settings.database_path)
    create_tables(engine)
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=settings.groq_timeout_seconds)
    knowledge = KnowledgeBase(settings.knowledge_db_path)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if not settings.groq_api_key:
            logger.warning(
                "GROQ_API_KEY não configurada: as respostas da IA e a voz vão falhar. "
                "Veja docs/INSTALACAO.md."
            )
        if knowledge.available:
            info = knowledge.stats()
            logger.info("Base de conhecimento: %d documento(s), %d trechos.",
                        info["documents"], info["chunks"])
        yield
        if owns_client:
            client.close()
        engine.dispose()

    app = FastAPI(
        title="ProfAssistenc IA",
        version=__version__,
        description="API do assistente de planejamento docente (Llama + Whisper via Groq, com RAG na BNCC e no RCSEERO).",
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = build_session_factory(engine)
    app.state.http_client = client
    app.state.knowledge_base = knowledge

    # --- erros em texto puro, como o frontend espera (response.text()) ---
    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException):
        return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(AIServiceError)
    async def _ai_error(_request: Request, exc: AIServiceError):
        return PlainTextResponse(exc.message, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", []) if part != "body")
        detail = f"Requisição inválida ({field}): {first.get('msg', 'dados incorretos')}"
        return PlainTextResponse(detail, status_code=400)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CaseInsensitiveApiPaths)

    # --- rotas ---
    @app.get("/api/health", response_model=HealthOut, tags=["Health"], summary="Status da API")
    def health() -> HealthOut:
        info = knowledge.stats()
        return HealthOut(
            status="ok",
            ai_configured=bool(settings.groq_api_key),
            version=__version__,
            model=settings.groq_model,
            knowledge_base=KnowledgeBaseOut(
                available=info["available"],
                documents=info["documents"],
                chunks=info["chunks"],
                names=info["names"],
            ),
        )

    app.include_router(lesson_plan.router)
    app.include_router(conversations.router)
    app.include_router(transcribe.router)

    # --- frontend (deve ser o último: o mount "/" captura o que sobrar) ---
    if settings.assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=settings.assets_dir), name="assets")
    if settings.frontend_dir.is_dir():
        app.mount(
            "/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend"
        )
    else:
        logger.warning("Pasta do frontend não encontrada: %s", settings.frontend_dir)

    return app


app = create_app()
