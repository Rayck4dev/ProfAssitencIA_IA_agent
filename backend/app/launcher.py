"""Rotinas de inicialização do programa (usadas por run.py e testáveis à parte)."""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import urllib.error
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_NAME = "profassistenc.log"


def already_running(port: int, host: str = "127.0.0.1", timeout: float = 1.5) -> bool:
    """True se já há um ProfAssistenc respondendo nessa porta (outra janela aberta)."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=timeout) as response:
            data = json.load(response)
        return data.get("status") == "ok" and "knowledgeBase" in data
    except (urllib.error.URLError, OSError, ValueError):
        return False


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """True se a porta está ocupada por outro programa.

    Em Linux/macOS, uma porta recém-usada fica em TIME_WAIT por ~1 min e um ``bind``
    simples falharia mesmo sem ninguém usando (o professor fecha e reabre o programa
    logo em seguida). O uvicorn usa SO_REUSEADDR, então o teste usa o mesmo. No Windows
    isso não é necessário e SO_REUSEADDR deixaria "roubar" uma porta em uso.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name != "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return True
    return False


def configure_file_logging(folder: Path) -> Path | None:
    """Grava o log também em arquivo (útil para o suporte pedir ao professor).

    O log registra o funcionamento do programa e erros, nunca o conteúdo das conversas nem a chave.
    """
    try:
        path = Path(folder) / LOG_NAME
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        for name in ("", "uvicorn", "uvicorn.access"):  # "uvicorn.error" já propaga para "uvicorn"
            logging.getLogger(name).addHandler(handler)
        return path
    except OSError:
        return None


def pause_before_closing(message: str = "Pressione Enter para fechar esta janela...") -> None:
    """Evita que a janela preta feche sozinha quando há uma mensagem importante."""
    if getattr(sys, "frozen", False) and sys.stdin is not None and sys.stdin.isatty():
        try:
            input(message)
        except EOFError:
            pass
