"""Configuração inicial: o professor informa a chave da Groq pela interface.

Substitui a edição manual do arquivo .env. A chave é testada na Groq antes de ser
gravada e passa a valer na hora, sem reiniciar o programa.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import get_groq_client
from app.envfile import mask_key, set_env_value
from app.schemas import SetupKeyRequest, SetupStatusOut
from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/setup", tags=["Configuração"])

REQUIRED_HEADER = "x-profassistenc"


def _ensure_local_request(request: Request) -> None:
    """Só aceita pedidos feitos pela própria interface do programa.

    Um site qualquer aberto no navegador não consegue mandar o cabeçalho
    personalizado (o navegador exigiria permissão CORS, que não é concedida) nem
    falsificar a origem.
    """
    if request.headers.get(REQUIRED_HEADER) != "1":
        raise HTTPException(status_code=403, detail="Pedido não autorizado.")
    origin = request.headers.get("origin")
    if origin and urlparse(origin).netloc != request.headers.get("host"):
        raise HTTPException(status_code=403, detail="Pedido não autorizado.")


@router.get("", response_model=SetupStatusOut, summary="Situação da chave da IA")
def setup_status(request: Request) -> SetupStatusOut:
    settings = request.app.state.settings
    key = settings.groq_api_key
    return SetupStatusOut(
        configured=bool(key),
        key_hint=mask_key(key) if key else None,
        stored_in=str(settings.env_path),
    )


@router.post(
    "/key",
    response_model=SetupStatusOut,
    summary="Testa e salva a chave da Groq",
    responses={
        400: {"description": "Chave com formato inválido ou recusada pela Groq"},
        403: {"description": "Pedido não veio da interface do programa"},
        502: {"description": "Não foi possível testar a chave (sem internet?)"},
    },
)
def save_key(
    body: SetupKeyRequest,
    request: Request,
    groq: GroqClient = Depends(get_groq_client),
) -> SetupStatusOut:
    _ensure_local_request(request)
    key = body.api_key.strip().strip("\"'")
    if len(key) < 20 or any(ch.isspace() for ch in key):
        raise HTTPException(
            status_code=400,
            detail="Essa chave não parece válida. Copie a chave inteira, sem espaços.",
        )

    groq.check_key(key)  # levanta AIServiceError (tratado em main.py) se recusada

    settings = request.app.state.settings
    try:
        set_env_value(settings.env_path, "GROQ_API_KEY", key)
    except OSError:
        logger.exception("Não foi possível gravar o arquivo de configuração.")
        raise HTTPException(
            status_code=500,
            detail="Não consegui salvar a chave neste computador (pasta sem permissão de escrita).",
        ) from None
    settings.groq_api_key = key  # vale na hora, sem reiniciar
    logger.info("Chave da IA configurada pela interface.")
    return SetupStatusOut(configured=True, key_hint=mask_key(key), stored_in=str(settings.env_path))
