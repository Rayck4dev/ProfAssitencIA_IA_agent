"""Gera o programa executável do ProfAssistenc e o .zip para distribuir.

Uso (dentro de backend/, com o ambiente virtual ativo):

    python build_exe.py              # pasta com o programa (recomendado) + .zip
    python build_exe.py --onefile    # um único arquivo (inicia mais devagar)
    python build_exe.py --sem-zip    # só o programa, sem compactar

Requer:  pip install -r requirements-build.txt

O executável só roda no sistema em que foi gerado: para obter o .exe, rode no Windows
(o arquivo construir_windows.bat faz tudo com um clique).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NAME = "ProfAssistenc"
DIST = HERE / "dist"
BUILD = HERE / "build"


def read_version() -> str:
    text = (HERE / "app" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "0.0.0"


def platform_name() -> str:
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")


def fail(message: str) -> None:
    print(f"\nERRO: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_requirements() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        fail("PyInstaller não está instalado. Rode:  pip install -r requirements-build.txt")
    required = [
        HERE / "data" / "knowledge.sqlite",
        ROOT / "frontend" / "index.html",
        ROOT / "assets" / "logo-mark.svg",
    ]
    for path in required:
        if not path.exists():
            fail(f"arquivo necessário não encontrado: {path}")


def run_pyinstaller(onefile: bool) -> None:
    for folder in (DIST, BUILD):
        shutil.rmtree(folder, ignore_errors=True)
    sep = os.pathsep  # ";" no Windows, ":" nos demais
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--name", NAME,
        "--onefile" if onefile else "--onedir",
        "--collect-submodules", "uvicorn",
        "--add-data", f"{ROOT / 'frontend'}{sep}frontend",
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--add-data", f"{HERE / 'data' / 'knowledge.sqlite'}{sep}data",
        "--distpath", str(DIST), "--workpath", str(BUILD), "--specpath", str(BUILD),
    ]
    icon = ROOT / "assets" / "favicon.ico"
    if sys.platform == "win32" and icon.exists():
        command += ["--icon", str(icon)]
    command.append(str(HERE / "run.py"))
    print("Gerando o programa (leva de 1 a 3 minutos)...")
    result = subprocess.run(command)
    if result.returncode != 0:
        fail("o PyInstaller falhou. Leia as mensagens acima.")


def make_package(onefile: bool) -> Path:
    """Monta a pasta final (programa + LEIA-ME.txt) e devolve o caminho dela."""
    if onefile:
        package = DIST / "pacote" / NAME
        package.mkdir(parents=True)
        suffix = ".exe" if sys.platform == "win32" else ""
        shutil.copy2(DIST / f"{NAME}{suffix}", package / f"{NAME}{suffix}")
    else:
        package = DIST / NAME
    readme = ROOT / "installer" / "LEIA-ME.txt"
    if readme.exists():
        shutil.copy2(readme, package / "LEIA-ME.txt")
    return package


def make_zip(package: Path, version: str) -> Path:
    archive = DIST / f"{NAME}-{version}-{platform_name()}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file in sorted(package.rglob("*")):
            if file.is_file():
                zf.write(file, Path(NAME) / file.relative_to(package))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (archive.parent / (archive.name + ".sha256")).write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--onefile", action="store_true", help="gera um único arquivo em vez de uma pasta")
    parser.add_argument("--sem-zip", action="store_true", help="não compacta o resultado")
    args = parser.parse_args()

    version = read_version()
    print(f"ProfAssistenc {version} — {platform_name()}")
    check_requirements()
    run_pyinstaller(args.onefile)
    package = make_package(args.onefile)
    print(f"\nPrograma pronto em: {package}")
    if not args.sem_zip:
        archive = make_zip(package, version)
        print(f"Pacote para distribuir: {archive} ({archive.stat().st_size / 1e6:.1f} MB)")
        print(f"SHA-256: {archive.with_name(archive.name + '.sha256').read_text(encoding='utf-8').split()[0]}")
    print("\nPróximo passo: teste em um computador limpo (veja docs/DISTRIBUICAO.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
