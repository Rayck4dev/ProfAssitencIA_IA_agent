"""Leitura/gravação segura de valores no arquivo .env."""

from __future__ import annotations

import os
import re
from pathlib import Path

HEADER = (
    "# Configurações do ProfAssistenc. Este arquivo guarda a sua chave: não compartilhe.\n"
)


def set_env_value(path: Path, name: str, value: str) -> None:
    """Grava ``NOME=valor`` no .env, trocando a linha existente e preservando o resto."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=")
    new_line = f"{name}={value}"
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = new_line
            break
    else:
        if not lines:
            lines.append(HEADER.rstrip("\n"))
        lines.append(new_line)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, path)  # troca atômica: nunca deixa o arquivo pela metade
    try:
        os.chmod(path, 0o600)  # só o dono lê (ignorado no Windows)
    except OSError:
        pass


def mask_key(key: str) -> str:
    """"gsk_abcdefgh1234" -> "gsk_…1234" (para mostrar sem expor a chave)."""
    return f"{key[:4]}…{key[-4:]}" if len(key) > 12 else "…"
