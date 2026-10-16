"""Configurações da aplicação.

Os valores são lidos, nesta ordem de prioridade, de:
1. variáveis de ambiente;
2. arquivo ``backend/.env`` (ao lado do executável, quando empacotado);
3. valores padrão definidos abaixo.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _is_frozen() -> bool:
    """True quando rodando dentro de um executável gerado pelo PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def _app_dir() -> Path:
    """Pasta onde ficam o ``.env`` e o banco de dados.

    Em desenvolvimento é a pasta ``backend/``; no executável, a pasta do ``.exe``.
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _bundle_dir() -> Path:
    """Pasta que contém ``frontend/`` e ``assets/``.

    Em desenvolvimento é a raiz do repositório; no executável, a pasta temporária
    onde o PyInstaller extrai os arquivos embutidos.
    """
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", _app_dir()))
    return _app_dir().parent


APP_DIR = _app_dir()
BUNDLE_DIR = _bundle_dir()
# Base de conhecimento (somente leitura): dentro do pacote no executável, ou backend/data.
DATA_DIR = (BUNDLE_DIR if _is_frozen() else APP_DIR) / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=APP_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Groq (Llama + Whisper) ---
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_whisper_model: str = "whisper-large-v3-turbo"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 60.0
    groq_max_attempts: int = 3
    groq_retry_delay_seconds: float = 1.0
    # Acima disso, em vez de esperar o fim do limite de taxa, avisa o usuário.
    groq_max_retry_wait_seconds: float = 20.0
    # Limite de resposta. No plano gratuito do modelo 8B o teto é de 6.000 tokens
    # por minuto somando entrada + saída, então este valor precisa ser moderado.
    groq_max_tokens: int = 1500
    temperature: float = 0.4

    # Instrução de sistema. Vazio = usa o prompt padrão embutido (app/prompts.py).
    system_prompt: str = ""
    # Máximo de caracteres do histórico reenviado a cada pergunta.
    history_max_chars: int = 4500

    # --- RAG (documentos curriculares) ---
    rag_enabled: bool = True
    rag_top_k: int = 6
    rag_max_chars: int = 4500
    knowledge_db_path: Path = DATA_DIR / "knowledge.sqlite"

    # --- Voz (Whisper) ---
    transcription_language: str = "pt"
    max_audio_mb: int = 20

    # --- Servidor ---
    host: str = "127.0.0.1"
    port: int = 5000
    open_browser: bool = True
    enable_docs: bool = True
    log_level: str = "INFO"
    # Origens extras autorizadas no CORS (ex.: frontend no Live Server).
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ]

    # --- Arquivos ---
    database_path: Path = APP_DIR / "profassistenc.db"
    frontend_dir: Path = BUNDLE_DIR / "frontend"
    assets_dir: Path = BUNDLE_DIR / "assets"

    @field_validator("groq_api_key", mode="before")
    @classmethod
    def _strip_key(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Aceita lista separada por vírgulas (``A,B``) ou JSON (``["A","B"]``)."""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                import json

                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
