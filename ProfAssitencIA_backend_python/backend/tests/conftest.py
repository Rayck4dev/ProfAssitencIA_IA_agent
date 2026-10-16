"""Fixtures: app com banco temporário, Groq simulado e base de conhecimento sintética."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.rag.ingest import Page, SourceDoc, write_database  # noqa: E402

TITLE_PREFIX = "Gere um título curto"


class FakeGroq:
    """Transporte HTTP falso: registra as chamadas e devolve respostas roteirizadas."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.answer = "Resposta da IA"
        self.title = "Título gerado"
        self.finish_reason = "stop"
        self.fail_with: int | None = None
        self.fail_headers: dict[str, str] = {}
        self.transient: list[tuple[int, dict[str, str]]] = []  # falhas antes de dar certo
        self.transcript: dict = {"text": "texto falado", "segments": []}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.transient:
            status, headers = self.transient.pop(0)
            return httpx.Response(status, headers=headers, json={"error": {"message": "x"}})
        if self.fail_with is not None:
            return httpx.Response(self.fail_with, headers=self.fail_headers, json={"error": {"message": "x"}})

        if request.url.path.endswith("/audio/transcriptions"):
            return httpx.Response(200, json=self.transcript)

        body = json.loads(request.content)
        first_user = next(m["content"] for m in body["messages"] if m["role"] == "user")
        is_title = first_user.startswith(TITLE_PREFIX)
        text = self.title if is_title else self.answer
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": text},
                               "finish_reason": "stop" if is_title else self.finish_reason}]},
        )

    def chat_payloads(self) -> list[dict]:
        out = []
        for r in self.requests:
            if r.url.path.endswith("/chat/completions"):
                body = json.loads(r.content)
                if not next(m["content"] for m in body["messages"] if m["role"] == "user").startswith(TITLE_PREFIX):
                    out.append(body)
        return out

    def title_payloads(self) -> list[dict]:
        return [
            json.loads(r.content) for r in self.requests
            if r.url.path.endswith("/chat/completions")
            and json.loads(r.content)["messages"][0]["content"].startswith(TITLE_PREFIX)
        ]


def make_knowledge_base(path: Path) -> None:
    """Base pequena, mas com a mesma estrutura da real."""
    bncc = SourceDoc(
        "BNCC", "Base Nacional Comum Curricular", "EI, EF e EM", "bncc.pdf",
        pages=[
            Page(1, 295, ["MATEMÁTICA ENSINO FUNDAMENTAL\nHABILIDADES",
                          "(EF05MA03) Identificar e representar frações (menores e maiores que a unidade), "
                          "associando-as ao resultado de uma divisão ou à ideia de parte de um todo, "
                          "utilizando a reta numérica como recurso.",
                          "(EF05MA04) Identificar frações equivalentes."]),
            Page(2, 337, ["CIÊNCIAS DA NATUREZA ENSINO FUNDAMENTAL\nHABILIDADES",
                          "(EF03CI05) Descrever e comunicar as alterações que ocorrem desde o nascimento "
                          "em animais de diferentes meios terrestres ou aquáticos."]),
        ],
        toc=[],
    )
    rcseero = SourceDoc(
        "RCSEERO", "Referencial Curricular para o Ensino Médio de Rondônia", "Ensino Médio (Rondônia)",
        "rcseero.pdf",
        pages=[Page(1, 275, ["Estatística e Probabilidade | (EM13MAT102) Analisar tabelas, gráficos e "
                             "amostras de pesquisas estatísticas | Conceitos estatísticos: população e amostragem."]),
               Page(2, 797, ["Projeto de Vida integrado ao currículo de Rondônia: os estudantes constroem "
                             "seu projeto de vida a partir do autoconhecimento e do protagonismo juvenil."])],
        toc=[(1, "CAPÍTULO 1", 1), (2, "Projeto de Vida", 2)],
    )
    write_database([bncc, rcseero], path)


@pytest.fixture
def gemini() -> FakeGroq:  # nome mantido curto no uso: fixture "groq" abaixo
    return FakeGroq()


@pytest.fixture
def groq(gemini) -> FakeGroq:
    return gemini


@pytest.fixture
def settings(tmp_path) -> Settings:
    kb = tmp_path / "kb.sqlite"
    make_knowledge_base(kb)
    return Settings(
        _env_file=None,
        groq_api_key="chave-de-teste",
        groq_retry_delay_seconds=0,
        database_path=tmp_path / "test.db",
        knowledge_db_path=kb,
        frontend_dir=tmp_path / "sem-frontend",
        assets_dir=tmp_path / "sem-assets",
    )


def make_client(settings: Settings, groq: FakeGroq) -> TestClient:
    http = httpx.Client(transport=httpx.MockTransport(groq))
    return TestClient(create_app(settings, http_client=http))


@pytest.fixture
def client(settings, groq):
    with make_client(settings, groq) as test_client:
        yield test_client
