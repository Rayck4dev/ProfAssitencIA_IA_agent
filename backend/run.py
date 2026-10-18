"""Ponto de entrada: inicia o servidor e abre o navegador.

Uso:  python run.py   (ou o executável ProfAssistenc)
"""

from __future__ import annotations

import sys
import threading
import time
import traceback
import webbrowser

import uvicorn

from app import __version__
from app.config import APP_DIR, get_settings
from app.launcher import (
    already_running,
    configure_file_logging,
    pause_before_closing,
    port_in_use,
)


def _open_browser_when_ready(server: uvicorn.Server, url: str) -> None:
    for _ in range(100):  # espera até ~10 s
        if server.started:
            webbrowser.open(url)
            return
        if server.should_exit:
            return
        time.sleep(0.1)


def main() -> int:
    settings = get_settings()
    url = f"http://localhost:{settings.port}"

    # Já está aberto em outra janela? Só abre o navegador nele.
    if already_running(settings.port):
        print(f"O ProfAssistenc já está aberto em {url}. Abrindo no navegador...", flush=True)
        if settings.open_browser:
            webbrowser.open(url)
        time.sleep(1.5)
        return 0

    if port_in_use(settings.port, settings.host):
        print(
            f"\nA porta {settings.port} está ocupada por outro programa.\n"
            f"Feche o outro programa, ou escolha outra porta: no arquivo .env (em {APP_DIR}),\n"
            f"acrescente a linha  PORT={settings.port + 1}  e abra o ProfAssistenc de novo.\n"
        )
        pause_before_closing()
        return 1

    from app.main import app  # import tardio: só depois das checagens acima

    print(f"\n  ProfAssistenc {__version__}", flush=True)
    print(f"  Aberto em {url}", flush=True)
    print("  Para encerrar, feche esta janela (ou aperte Ctrl+C).\n", flush=True)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
        )
    )
    if getattr(sys, "frozen", False):
        # Depois de criar o app e o uvicorn: antes disso o logging ainda não está configurado
        # e o uvicorn apagaria os handlers dos seus loggers.
        configure_file_logging(APP_DIR)
    if settings.open_browser:
        threading.Thread(
            target=_open_browser_when_ready, args=(server, url), daemon=True
        ).start()
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    except Exception:  # noqa: BLE001 - mostra o erro em vez de a janela sumir
        traceback.print_exc()
        print(f"\nO ProfAssistenc não conseguiu iniciar. Mande o arquivo profassistenc.log (em {APP_DIR}) ao suporte.")
        pause_before_closing()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
