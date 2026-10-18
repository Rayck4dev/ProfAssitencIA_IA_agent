from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_knowledge_base

from app.rag.ingest import Page, _band_units, _is_toc, chunk_page
from app.rag.intent import parse_intent
from app.rag.store import KnowledgeBase
from app.rag.text import CODE_RE, decode_code, tokenize

REAL_KB = Path(__file__).resolve().parent.parent / "data" / "knowledge.sqlite"


@pytest.fixture
def kb(tmp_path):
    make_knowledge_base(tmp_path / "kb.sqlite")
    return KnowledgeBase(tmp_path / "kb.sqlite")


# ---------------------------------------------------------------- texto
def test_stemmer_unifica_variacoes():
    same = [("fração", "frações"), ("função", "funções"), ("planejamento", "planejar"),
            ("português", "portuguesa"), ("inglês", "inglesa"), ("animais", "animal")]
    for a, b in same:
        assert tokenize(a) == tokenize(b), (a, b)


def test_codigos_passam_intactos_e_sao_decodificados():
    assert tokenize("(EF05MA03) Identificar") [0] == "ef05ma03"
    assert CODE_RE.findall("EF05MA03, EM13MAT102, EMIFCG01, XX05MA03") == ["EF05MA03", "EM13MAT102", "EMIFCG01"]
    assert decode_code("EF05MA03").descricao == "Ensino Fundamental · 5º ano · Matemática"
    assert decode_code("EF69LP01").descricao == "Ensino Fundamental · 6º ao 9º ano · Língua Portuguesa"
    assert decode_code("XX00") is None


def test_stopwords_de_saudacao_e_pedido_sao_removidas():
    assert tokenize("obrigado! oi, tudo bem?", drop_stopwords=True) == []
    assert tokenize("Crie um plano de aula sobre frações", drop_stopwords=True) == ["fraca"]


# --------------------------------------------------------------- intenção
def test_intencao_ano_e_componente():
    i = parse_intent("plano de matemática para o 5º ano")
    assert (i.etapa, i.anos) == ("EF", [5]) and i.prefixes == ["ef05ma", "ef15ma", "ef35ma"]
    assert parse_intent("sexto ano de história").prefixes == ["ef06hi", "ef67hi", "ef69hi"]
    assert parse_intent("2ª série do ensino médio, física").prefixes == ["em13cnt"]
    assert parse_intent("1º ano do ensino médio").etapa == "EM"  # não é o 1º ano do EF
    assert parse_intent("projeto de vida no ensino médio").prefixes == []  # sem filtro: tema narrativo
    assert parse_intent("crianças pequenas na educação infantil").prefixes == ["ei03"]
    assert not parse_intent("obrigado!").found


# ------------------------------------------------------------- ingestão
def test_blocos_de_tabela_viram_linhas_ordenadas_por_coluna():
    blocks = [  # (x0, y0, x1, y1, texto): célula de eixo centralizada verticalmente
        (365, 91, 560, 185, "(EM13MAT102) habilidade"), (568, 91, 786, 197, "Objetos de conhecimento"),
        (182, 91, 358, 212, "Competência"), (98, 139, 167, 164, "Eixo"),
        (365, 223, 560, 331, "(EM13MAT103) outra"), (568, 222, 783, 340, "Outros objetos"),
    ]
    rows = _band_units(blocks)
    assert len(rows) == 2
    assert rows[0] == "Eixo | Competência | (EM13MAT102) habilidade | Objetos de conhecimento"
    assert rows[1].startswith("(EM13MAT103) outra")


def test_sumario_e_descartado_e_trechos_nao_cruzam_paginas():
    toc = Page(1, 4, ["Capítulo 1 ........ 10\nCapítulo 2 ........ 20 Capítulo 3 ........ 30"])
    assert chunk_page(toc) == []
    assert _is_toc("a ..... 1 b ..... 2") and not _is_toc("Frase normal com pontos...")
    long = Page(2, 5, ["Frase de teste número um. " * 80])
    chunks = chunk_page(long)
    assert len(chunks) > 1 and all(len(c) < 1400 for c in chunks)


# ----------------------------------------------------------------- busca
def test_busca_por_ano_e_componente_acha_a_habilidade(kb):
    r = kb.search("plano de aula sobre frações para o 5º ano de matemática")
    assert r.hits[0].doc == "BNCC" and "EF05MA03" in r.hits[0].text
    assert r.hits[0].page == "p. 295" and r.hits[0].heading == "Ensino Fundamental · 5º ano · Matemática"
    assert "EF03CI05" not in r.context_block()  # outro ano/componente fica de fora


def test_busca_tematica_acha_texto_narrativo_do_rcseero(kb):
    r = kb.search("projeto de vida no ensino médio de Rondônia")
    assert r.hits[0].doc == "RCSEERO" and r.hits[0].page == "p. 797"
    assert r.sources_line() == "RCSEERO (p. 797)"


def test_codigos_desconhecidos(kb):
    assert kb.unknown_codes("use EF05MA03 e EF05MA99, ef05ma04") == ["EF05MA99"]
    assert kb.unknown_codes("sem códigos aqui") == []


def test_consulta_vazia_ou_base_ausente(kb, tmp_path):
    assert not kb.search("oi, tudo bem?")
    missing = KnowledgeBase(tmp_path / "nao-existe.sqlite")
    assert not missing.available and not missing.search("frações") and missing.unknown_codes("EF05MA99") == []


def test_orcamento_de_caracteres_e_respeitado(kb):
    r = kb.search("frações matemática ano estatística", max_chars=300, k=6)
    assert len(r.hits) == 1 or sum(len(h.text) for h in r.hits) <= 300


@pytest.fixture(scope="module")
def real():
    return KnowledgeBase(REAL_KB)


# ---- base REAL que acompanha o projeto (pulado se o arquivo não estiver presente) ----
@pytest.mark.skipif(not REAL_KB.exists(), reason="data/knowledge.sqlite não encontrado")
class TestBaseReal:
    def test_documentos_e_codigos(self, real):
        assert [d["name"] for d in real.docs()] == ["BNCC", "RCSEERO"]
        assert real.stats()["chunks"] > 4000
        assert real.unknown_codes("EF05MA03 EM13MAT102 EF99XX99") == ["EF99XX99"]

    @pytest.mark.parametrize("pergunta, trecho", [
        ("plano de aula sobre frações para o 5º ano de matemática", "EF05MA03"),
        ("aula de história do 8º ano sobre república", "EF08HI"),
        ("aula de inglês para o 7º ano", "EF07LI"),
        ("estatística e gráficos no ensino médio de matemática", "EM13MAT"),
    ])
    def test_perguntas_tipicas_recuperam_a_habilidade_certa(self, real, pergunta, trecho):
        r = real.search(pergunta)
        assert any(trecho in h.text for h in r.hits[:3]), r.context_block()[:300]

    def test_projeto_de_vida_vem_do_rcseero(self, real):
        r = real.search("projeto de vida no ensino médio de Rondônia")
        assert r.hits[0].doc == "RCSEERO"
