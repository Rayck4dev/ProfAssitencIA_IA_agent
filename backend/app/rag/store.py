"""Consulta à base de conhecimento (somente leitura)."""

from __future__ import annotations

import difflib
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.rag.intent import Intent, parse_intent
from app.rag.text import CODE_RE, decode_code, tokenize

logger = logging.getLogger(__name__)

MAX_QUERY_TERMS = 14
CANDIDATES = 14  # candidatos por consulta antes da fusão
RRF_K = 60  # constante da fusão por rank recíproco
SCOPED_WEIGHT = 1.0  # consulta restrita por ano/componente
GLOBAL_WEIGHT = 0.6  # consulta só por tema
TYPO_MIN_LEN = 4  # termos menores que isso não são corrigidos
TYPO_CUTOFF = 0.78  # similaridade mínima para aceitar a correção


@dataclass
class Hit:
    chunk_id: int
    doc: str
    page_label: int | None
    page_pdf: int
    section: str
    text: str
    score: float  # pontuação da fusão (maior = melhor)
    bm25: float  # melhor BM25 bruto (menor = melhor); só informativo

    @property
    def page(self) -> str:
        return f"p. {self.page_label}" if self.page_label else f"p. {self.page_pdf} do PDF"

    @property
    def heading(self) -> str:
        """Descrição curta do trecho: etapa/ano/componente (pelos códigos) ou seção."""
        descriptions = {
            d.descricao for c in set(CODE_RE.findall(self.text)) if (d := decode_code(c))
        }
        if len(descriptions) == 1:
            return next(iter(descriptions))
        return self.section


@dataclass
class Retrieval:
    hits: list[Hit] = field(default_factory=list)
    intent: Intent = field(default_factory=Intent)
    terms: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.hits)

    def context_block(self) -> str:
        """Trechos formatados para o prompt do modelo."""
        parts = []
        for i, hit in enumerate(self.hits, start=1):
            title = f"[{i}] {hit.doc}, {hit.page}"
            if hit.heading:
                title += f" — {hit.heading}"
            parts.append(f"{title}\n{hit.text}")
        return "\n\n".join(parts)

    def sources_line(self) -> str:
        """Ex.: 'BNCC (p. 295, 296) · RCSEERO (p. 276)'."""
        by_doc: dict[str, list[str]] = {}
        for hit in self.hits:
            label = str(hit.page_label or f"{hit.page_pdf} do PDF")
            pages = by_doc.setdefault(hit.doc, [])
            if label not in pages:
                pages.append(label)
        return " · ".join(f"{doc} (p. {', '.join(pages)})" for doc, pages in by_doc.items())


class KnowledgeBase:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._vocab: dict[str, int] | None = None
        self._vocab_lock = threading.Lock()
        self.available = self._check()

    def _check(self) -> bool:
        if not self.path.is_file():
            logger.warning("Base de conhecimento não encontrada em %s (RAG desativado).", self.path)
            return False
        try:
            with self._connect() as db:
                db.execute("SELECT 1 FROM chunks_fts LIMIT 1").fetchall()
        except sqlite3.Error as exc:
            logger.warning("Base de conhecimento inutilizável (%s); RAG desativado.", exc)
            return False
        return True

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)

    # ------------------------------------------------------------- informações
    def docs(self) -> list[dict]:
        if not self.available:
            return []
        with self._connect() as db:
            rows = db.execute("SELECT name, title, scope, pages FROM docs ORDER BY id").fetchall()
        return [{"name": n, "title": t, "scope": s, "pages": p} for n, t, s, p in rows]

    def stats(self) -> dict:
        if not self.available:
            return {"available": False, "documents": 0, "chunks": 0, "names": []}
        with self._connect() as db:
            chunks = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        docs = self.docs()
        return {"available": True, "documents": len(docs), "chunks": chunks,
                "names": [d["name"] for d in docs]}

    def unknown_codes(self, text: str) -> list[str]:
        """Códigos de habilidade citados em ``text`` que não existem nos documentos."""
        found = sorted(set(CODE_RE.findall(text.upper())))
        if not found or not self.available:
            return []
        with self._connect() as db:
            known = {
                row[0]
                for row in db.execute(
                    f"SELECT code FROM codes WHERE code IN ({','.join('?' * len(found))})", found
                )
            }
        return [c for c in found if c not in known]

    # -------------------------------------------------- tolerância a erros de digitação
    def vocabulary(self) -> dict[str, int]:
        """Termos do índice e em quantos trechos aparecem (carregado uma vez)."""
        if self._vocab is None:
            with self._vocab_lock:
                if self._vocab is None:
                    with self._connect() as db:
                        # tabela virtual TEMPORÁRIA: funciona mesmo com o arquivo somente leitura
                        db.execute(
                            "CREATE VIRTUAL TABLE IF NOT EXISTS temp.vocab "
                            "USING fts5vocab('main', 'chunks_fts', 'row')"
                        )
                        self._vocab = {t: d for t, d in db.execute("SELECT term, doc FROM temp.vocab")}
        return self._vocab

    def correct_terms(self, terms: list[str]) -> list[str]:
        """Troca por termos parecidos do índice os que não existem nele (typos).

        "matematca" → "matemat", "fotosintese" → "fotossintes", "istoria" → "histori".
        Termos que existem, curtos ou com dígitos (códigos) não são alterados.
        """
        try:
            vocab = self.vocabulary()
        except sqlite3.Error:
            return terms
        corrected = []
        for term in terms:
            if term in vocab or len(term) < TYPO_MIN_LEN or any(c.isdigit() for c in term):
                corrected.append(term)
                continue
            candidates = [
                v for v in vocab
                if abs(len(v) - len(term)) <= 2 and (v[0] == term[0] or v[-2:] == term[-2:])
            ]
            best = difflib.get_close_matches(term, candidates, n=3, cutoff=TYPO_CUTOFF)
            if best:
                choice = max(best, key=lambda v: vocab[v])  # o mais frequente entre os parecidos
                logger.debug("Corrigindo termo da busca: %s → %s", term, choice)
                corrected.append(choice)
            else:
                corrected.append(term)
        return list(dict.fromkeys(corrected))

    # ------------------------------------------------------------------ busca
    def search(
        self,
        question: str,
        *,
        intent_text: str | None = None,
        k: int = 6,
        max_chars: int = 5000,
    ) -> Retrieval:
        """Busca os trechos mais relevantes para ``question``.

        ``intent_text`` (opcional) é o texto de onde se lê ano/etapa/componente;
        por padrão é a própria pergunta.
        """
        if not self.available or not question.strip():
            return Retrieval()

        intent = parse_intent(intent_text or question)
        terms = tokenize(question, drop_stopwords=True)
        noise: set[str] = set()
        if intent.anos:  # "5º ano": o número e "ano" não são tema
            noise |= {t for t in terms if t.isdigit() and len(t) <= 2}
            noise |= set(tokenize("ano série"))
        if intent.etapa:  # a etapa já virou filtro; como termo só atrapalharia o ranking
            noise |= set(tokenize("ensino médio fundamental infantil educação série"))
            if intent.etapa == "EM":  # "1º ano do ensino médio" = 1ª série
                noise |= {"ano", "1", "2", "3"}
        terms = [t for t in terms if t not in noise]
        terms = self.correct_terms(list(dict.fromkeys(terms)))[:MAX_QUERY_TERMS]

        ranked: list[tuple[float, list[tuple[int, float]]]] = []
        with self._connect() as db:
            if intent.found:
                prefix = " OR ".join(f'"{p}"*' for p in intent.prefixes)
                query = f"({_or(terms)}) AND ({prefix})" if terms else prefix
                ranked.append((SCOPED_WEIGHT, self._run(db, query)))
            if terms:
                ranked.append((GLOBAL_WEIGHT, self._run(db, _or(terms))))

            if terms and not any(results for _, results in ranked):
                # nada casou nem corrigido: última tentativa por prefixo ("matem*", "frac*")
                prefix_or = " OR ".join(f'"{t[: max(4, len(t) - 2)]}"*' for t in terms if len(t) >= 4)
                if prefix_or:
                    ranked.append((GLOBAL_WEIGHT, self._run(db, prefix_or)))

            scores: dict[int, float] = {}
            best_bm25: dict[int, float] = {}
            for weight, results in ranked:
                for rank, (chunk_id, bm25) in enumerate(results):
                    scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (RRF_K + rank)
                    best_bm25[chunk_id] = min(best_bm25.get(chunk_id, 0.0), bm25)

            hits: list[Hit] = []
            used = 0
            for chunk_id in sorted(scores, key=scores.get, reverse=True):
                row = db.execute(
                    "SELECT d.name, c.page_label, c.page_pdf, c.section, c.text "
                    "FROM chunks c JOIN docs d ON d.id = c.doc_id WHERE c.id = ?",
                    (chunk_id,),
                ).fetchone()
                if used + len(row[4]) > max_chars and hits:
                    continue
                hits.append(Hit(chunk_id, *row, scores[chunk_id], best_bm25[chunk_id]))
                used += len(row[4])
                if len(hits) >= k:
                    break
        return Retrieval(hits, intent, terms)

    @staticmethod
    def _run(db: sqlite3.Connection, match: str) -> list[tuple[int, float]]:
        try:
            return db.execute(
                "SELECT rowid, bm25(chunks_fts) AS s FROM chunks_fts "
                "WHERE chunks_fts MATCH ? ORDER BY s LIMIT ?",
                (match, CANDIDATES),
            ).fetchall()
        except sqlite3.OperationalError as exc:  # consulta inválida: não derruba a conversa
            logger.warning("Consulta FTS inválida (%s): %s", exc, match[:120])
            return []


def _or(terms: list[str]) -> str:
    return " OR ".join(f'"{t}"' for t in terms)
