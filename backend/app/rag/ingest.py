"""Gera a base de conhecimento (SQLite + FTS5) a partir dos PDFs oficiais.

Uso (dentro de ``backend/``, com o ambiente virtual ativo)::

    pip install -r requirements-ingest.txt
    python -m app.rag.ingest knowledge/            # pasta com os PDFs
    python -m app.rag.ingest a.pdf b.pdf --out data/knowledge.sqlite

O índice é recriado do zero a cada execução.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.rag.text import CODE_RE, decode_code, index_text

TARGET_CHARS = 900  # tamanho-alvo de um trecho
MAX_UNIT_CHARS = 1300  # blocos maiores que isso são quebrados por frase
MIN_CHUNK_CHARS = 60  # trechos menores (sem código) são descartados
DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "knowledge.sqlite"

# Nome curto, título completo e etapas cobertas dos documentos conhecidos.
# Para outros PDFs, o nome vem do arquivo.
KNOWN_DOCS = {
    "bncc": (
        "BNCC",
        "Base Nacional Comum Curricular",
        "Educação Infantil, Ensino Fundamental e Ensino Médio",
    ),
    "rcseero": (
        "RCSEERO",
        "Referencial Curricular para o Ensino Médio de Rondônia",
        "Ensino Médio (Rondônia)",
    ),
}

SCHEMA = """
CREATE TABLE docs (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, title TEXT NOT NULL, scope TEXT NOT NULL,
    pages INTEGER NOT NULL, page_offset INTEGER, source_file TEXT NOT NULL
);
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL REFERENCES docs(id),
    page_pdf INTEGER NOT NULL, page_label INTEGER, section TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL
);
CREATE VIRTUAL TABLE chunks_fts USING fts5(body, content='', tokenize='unicode61 remove_diacritics 2');
CREATE TABLE codes (
    code TEXT PRIMARY KEY, doc_id INTEGER NOT NULL, chunk_id INTEGER NOT NULL
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


# ----------------------------------------------------------------- extração
@dataclass
class Page:
    number: int  # número da página no PDF (1-based)
    printed: int | None  # número impresso na página, se detectado
    units: list[str]  # blocos de texto já ordenados (linhas de tabela / parágrafos)


def _clean(text: str) -> str:
    text = re.sub(r"-\n(?=[a-zà-ú])", "", text)  # hifenização no fim da linha
    return re.sub(r"\s+", " ", text).strip()


def extract_pages(pdf_path: Path) -> tuple[list[Page], list[tuple[int, str, int]]]:
    import pymupdf  # só necessário na ingestão

    doc = pymupdf.open(pdf_path)  # PyMuPDF repara PDFs com xref quebrada sozinho
    pages: list[Page] = []
    for index, page in enumerate(doc, start=1):
        height = page.rect.height
        blocks = []
        printed = None
        for x0, y0, x1, y1, text, _no, kind in page.get_text("blocks"):
            if kind != 0:
                continue
            clean = _clean(text)
            if not clean:
                continue
            if re.fullmatch(r"\d{1,4}", clean) and (y1 < 0.12 * height or y0 > 0.85 * height):
                printed = int(clean)  # número da página (cabeçalho/rodapé)
                continue
            blocks.append((x0, y0, x1, y1, clean))
        pages.append(Page(index, printed, _band_units(blocks)))
    return pages, doc.get_toc()


def _band_units(blocks: list[tuple]) -> list[str]:
    """Agrupa blocos em "faixas" horizontais (linhas de tabela) e ordena por coluna.

    Em tabelas de habilidades cada célula é um bloco; blocos cujos intervalos
    verticais se sobrepõem pertencem à mesma linha da tabela.
    """
    if not blocks:
        return []
    blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
    bands: list[list[tuple]] = []
    band_end = -1e9
    for block in blocks:
        if bands and block[1] < band_end - 2:
            bands[-1].append(block)
            band_end = max(band_end, block[3])
        else:
            bands.append([block])
            band_end = block[3]
    units = []
    for band in bands:
        band.sort(key=lambda b: (round(b[0] / 30), b[1]))
        columns = {round(b[0] / 30) for b in band}
        sep = " | " if len(columns) > 1 else "\n"
        units.append(sep.join(b[4] for b in band))
    return units


def _split_long(unit: str) -> list[str]:
    if len(unit) <= MAX_UNIT_CHARS:
        return [unit]
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?;:])\s+", unit):
        if current and len(current) + len(sentence) + 1 > TARGET_CHARS:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def chunk_page(page: Page) -> list[str]:
    """Junta unidades da página em trechos de ~TARGET_CHARS, sem cruzar páginas."""
    chunks, current = [], ""
    for unit in (p for u in page.units for p in _split_long(u)):
        if current and len(current) + len(unit) + 1 > TARGET_CHARS:
            chunks.append(current)
            current = unit
        else:
            current = f"{current}\n{unit}".strip()
    if current:
        chunks.append(current)
    return [
        c
        for c in chunks
        if (len(c) >= MIN_CHUNK_CHARS or CODE_RE.search(c)) and not _is_toc(c)
    ]


def _is_toc(chunk: str) -> bool:
    """Sumários ("Capítulo 1 ........ 10") só poluem a busca."""
    return len(re.findall(r"\.{5,}", chunk)) >= 2


# ------------------------------------------------------------------ metadados
def _page_offset(pages: list[Page]) -> int | None:
    """Diferença típica entre a página do PDF e o número impresso."""
    diffs = [p.number - p.printed for p in pages if p.printed]
    if len(diffs) < 10:
        return None
    value, count = Counter(diffs).most_common(1)[0]
    return value if count / len(diffs) >= 0.6 else None


def _sections_by_page(toc: list[tuple[int, str, int]], n_pages: int) -> dict[int, str]:
    """Caminho de seção (a partir do outline do PDF) para cada página."""
    useful = [
        (lvl, title.strip(), pg)
        for lvl, title, pg in toc
        if title.strip() and not title.startswith("_") and not re.match(r"(?i)back\d+$", title.strip())
    ]
    result, stack, i = {}, [], 0
    for page in range(1, n_pages + 1):
        while i < len(useful) and useful[i][2] <= page:
            lvl, title, _ = useful[i]
            stack = [s for s in stack if s[0] < lvl] + [(lvl, title)]
            i += 1
        names = [t for _, t in stack][-3:]
        result[page] = " › ".join(n[:70] for n in names)
    return result


def _doc_identity(path: Path) -> tuple[str, str, str]:
    stem = path.stem.lower()
    for key, identity in KNOWN_DOCS.items():
        if stem.startswith(key):
            return identity
    name = re.split(r"[_\s]", path.stem)[0].upper() or path.stem
    return name, path.stem, ""


# ----------------------------------------------------------------- construção
@dataclass
class SourceDoc:
    name: str
    title: str
    scope: str
    source_file: str
    pages: list[Page]
    toc: list[tuple[int, str, int]]


def load_pdf(pdf: Path) -> SourceDoc:
    pages, toc = extract_pages(pdf)
    name, title, scope = _doc_identity(pdf)
    return SourceDoc(name, title, scope, pdf.name, pages, toc)


def write_database(docs: list[SourceDoc], out: Path) -> dict:
    """Cria o arquivo SQLite com o índice a partir dos documentos já extraídos."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    db = sqlite3.connect(out)
    db.executescript(SCHEMA)
    started = time.time()
    total_chunks = 0

    for doc_id, doc in enumerate(docs, start=1):
        offset = _page_offset(doc.pages)
        sections = _sections_by_page(doc.toc, len(doc.pages))
        db.execute(
            "INSERT INTO docs VALUES (?,?,?,?,?,?,?)",
            (doc_id, doc.name, doc.title, doc.scope, len(doc.pages), offset, doc.source_file),
        )
        n_chunks = 0
        for page in doc.pages:
            label = page.printed or (page.number - offset if offset and page.number > offset else None)
            section = sections.get(page.number, "")
            for text in chunk_page(page):
                cur = db.execute(
                    "INSERT INTO chunks (doc_id, page_pdf, page_label, section, text) VALUES (?,?,?,?,?)",
                    (doc_id, page.number, label, section, text),
                )
                chunk_id = cur.lastrowid
                codes = sorted(set(CODE_RE.findall(text)))
                infos = [d for c in codes if (d := decode_code(c))]
                extra = " ".join(d.descricao for d in infos)
                if infos:  # facilita achar "5º ano" em consultas sem código
                    extra += " " + " ".join(str(a) for d in infos for a in d.anos) + " ano"
                db.execute(
                    "INSERT INTO chunks_fts (rowid, body) VALUES (?, ?)",
                    (chunk_id, index_text(text, f"{extra} {section}")),
                )
                for code in codes:
                    db.execute("INSERT OR IGNORE INTO codes VALUES (?,?,?)", (code, doc_id, chunk_id))
                n_chunks += 1
        total_chunks += n_chunks
        print(f"      {doc.name}: {len(doc.pages)} páginas → {n_chunks} trechos "
              f"(deslocamento de numeração: {offset})")

    db.execute("INSERT INTO meta VALUES ('built_at', datetime('now'))")
    db.execute("INSERT INTO meta VALUES ('schema_version', '1')")
    db.commit()
    n_codes = db.execute("SELECT COUNT(*) FROM codes").fetchone()[0]
    sizes = [r[0] for r in db.execute("SELECT LENGTH(text) FROM chunks")] or [0]
    db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('optimize')")
    db.commit()
    db.execute("VACUUM")
    db.close()
    stats = {
        "docs": len(docs), "chunks": total_chunks, "codes": n_codes,
        "median_chars": int(statistics.median(sizes)), "seconds": round(time.time() - started, 1),
        "mb": round(out.stat().st_size / 1e6, 1),
    }
    print(f"Pronto: {stats['chunks']} trechos, {stats['codes']} códigos de habilidade, "
          f"{stats['mb']} MB → {out}")
    return stats


def build(pdfs: list[Path], out: Path) -> dict:
    docs = []
    for i, pdf in enumerate(pdfs, start=1):
        print(f"[{i}/{len(pdfs)}] lendo {pdf.name} ...", flush=True)
        docs.append(load_pdf(pdf))
    return write_database(docs, out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Indexa PDFs curriculares para o RAG.")
    parser.add_argument("sources", nargs="+", type=Path, help="PDFs ou pastas com PDFs")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="arquivo de saída (.sqlite)")
    args = parser.parse_args(argv)

    pdfs: list[Path] = []
    for source in args.sources:
        pdfs += sorted(source.glob("*.pdf")) if source.is_dir() else [source]
    pdfs = [p for p in pdfs if p.is_file()]
    if not pdfs:
        print("Nenhum PDF encontrado.", file=sys.stderr)
        return 1
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        print("Falta o PyMuPDF: pip install -r requirements-ingest.txt", file=sys.stderr)
        return 1
    build(pdfs, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
