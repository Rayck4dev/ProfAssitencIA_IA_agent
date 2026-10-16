"""Ponto de entrada: inicia o servidor e abre o navegador.

Uso:  python run.py
"""

from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn

from app.config import get_settings
from app.main import app


def _open_browser_when_ready(server: uvicorn.Server, url: str) -> None:
    for _ in range(100):  # espera até ~10 s
        if server.started:
            webbrowser.open(url)
            return
        if server.should_exit:
            return
        time.sleep(0.1)


def main() -> None:
    settings = get_settings()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
        )
    )
    if settings.open_browser:
        url = f"http://localhost:{settings.port}"
        threading.Thread(
            target=_open_browser_when_ready, args=(server, url), daemon=True
        ).start()
    server.run()


if __name__ == "__main__":
    main()
