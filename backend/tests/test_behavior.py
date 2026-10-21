"""Comportamentos ligados a modelos de raciocínio, orçamento de tokens, texto livre e títulos."""

from __future__ import annotations

import sqlite3

import pytest
from conftest import make_client

from app.titles import make_title
from test_api import EF_SCHEMA, INST, conv_list, send


def system_of(groq, index=-1) -> str:
    return groq.chat_payloads()[index]["messages"][0]["content"]


# ------------------------------------------------- parâmetros de raciocínio por modelo
def test_gpt_oss_usa_include_reasoning_e_nunca_reasoning_format(client, groq):
    send(client)
    body = groq.chat_payloads()[0]
    assert body["include_reasoning"] is False and body["reasoning_effort"] == "low"
    assert "reasoning_format" not in body  # a Groq não suporta isso no gpt-oss


def test_modelo_comum_nao_recebe_parametros_de_raciocinio(settings, groq):
    settings.groq_model = "llama-3.3-70b-versatile"
    with make_client(settings, groq) as client:
        send(client)
    body = groq.chat_payloads()[0]
    assert not any(k.startswith("reasoning") or k == "include_reasoning" for k in body)


def test_qwen_esconde_o_raciocinio_com_reasoning_format(settings, groq):
    settings.groq_model = "qwen/qwen3.8-27b"
    with make_client(settings, groq) as client:
        send(client)
    body = groq.chat_payloads()[0]
    assert body["reasoning_format"] == "hidden" and "include_reasoning" not in body


def test_parametro_de_raciocinio_recusado_e_repetido_sem_ele(client, groq):
    groq.reject_reasoning = True
    assert send(client).status_code == 200
    first, second = groq.chat_payloads()
    assert "reasoning_effort" in first and "reasoning_effort" not in second


# ----------------------------------- texto vazio porque o raciocínio gastou o limite
def test_resposta_vazia_por_falta_de_espaco_e_refeita_com_mais_espaco(client, groq):
    groq.empty_calls = 1
    r = send(client, "uma pergunta confusa")
    assert r.status_code == 200 and r.json()["response"].startswith("Resposta da IA")
    first, second = groq.chat_payloads()
    assert second["max_completion_tokens"] > first["max_completion_tokens"]


def test_sempre_vazio_devolve_erro_claro_e_nao_grava(client, groq):
    groq.empty_calls = 99
    r = send(client)
    assert r.status_code == 502 and "gastou o limite pensando" in r.text
    assert len(groq.chat_payloads()) == 4
    assert conv_list(client) == []


def test_413_por_limite_por_minuto_reduz_a_resposta_e_tenta_de_novo(client, groq):
    groq.overflow_413 = 600
    assert send(client).status_code == 200
    first, second = groq.chat_payloads()
    assert second["max_completion_tokens"] == first["max_completion_tokens"] - 600 - 64


# ------------------------------------------------------------ respostas maiores
def test_resposta_usa_o_espaco_que_sobra_no_limite_por_minuto(client, groq):
    send(client, "plano de aula de matemática para o 5º ano sobre frações")
    body = groq.chat_payloads()[0]
    used = sum(len(m["content"]) / 3.0 + 8 for m in body["messages"])
    assert 3000 <= body["max_completion_tokens"] <= 4096  # antes era fixo em 1500
    assert used + body["max_completion_tokens"] < 8000  # e nunca passa do limite por minuto


def test_sem_limite_por_minuto_usa_o_teto_configurado(settings, groq):
    settings.groq_tpm_limit = 0
    settings.groq_max_tokens = 1234
    with make_client(settings, groq) as client:
        send(client)
    assert groq.chat_payloads()[0]["max_completion_tokens"] == 1234


def test_historico_encolhe_para_proteger_o_espaco_da_resposta(settings, groq):
    settings.groq_tpm_limit = 4500
    settings.groq_min_output_tokens = 2000
    with make_client(settings, groq) as client:
        groq.answer = "palavra " * 700  # ~5.600 caracteres por resposta
        first = send(client, "plano de matemática do 5º ano sobre frações").json()
        for _ in range(2):
            send(client, "mais um pedido", conversation_id=first["conversationId"])
    body = groq.chat_payloads()[-1]
    used = sum(len(m["content"]) / 3.0 + 8 for m in body["messages"])
    assert body["max_completion_tokens"] >= 600 and used + body["max_completion_tokens"] < 4500


def test_resposta_cortada_vira_aviso_e_continuar_envia_o_fim(client, groq):
    groq.finish_reason = "length"
    groq.answer = "ABCDEFGH" * 400  # 3.200 caracteres, cortada pelo limite
    first = send(client, "plano de aula de matemática do 5º ano sobre frações").json()
    assert "Resposta cortada pelo limite de tamanho" in first["response"]

    groq.finish_reason, groq.answer = "stop", "…continuação"
    send(client, "Continue exatamente de onde parou", conversation_id=first["conversationId"])
    payload = groq.chat_payloads()[-1]
    history = payload["messages"][1:-1]
    assert history[-1]["role"] == "assistant" and history[-1]["content"].startswith("ABCDEFGH")
    assert all("Resposta cortada" not in m["content"] for m in payload["messages"])
    assert "(EF05MA03)" in payload["messages"][0]["content"]  # "continue" herda o tema para a busca


# ------------------------------------------------------- liberdade para perguntar
def test_pedido_com_erros_de_digitacao_ainda_recupera_a_habilidade_certa(client, groq):
    r = send(client, "plano de aula de matematca pro 5 ano sobre fraçoes")
    assert r.status_code == 200
    assert "(EF05MA03)" in system_of(groq)


def test_pedido_sem_relacao_com_os_documentos_e_respondido_mesmo_assim(client, groq):
    r = send(client, "xkzqw blablabla qualquer coisa")
    assert r.status_code == 200 and r.json()["response"].startswith("Resposta da IA")


def test_prompt_livre_e_o_padrao_e_nunca_manda_recusar(client, groq):
    send(client, "plano de aula")
    system = system_of(groq)
    assert "NUNCA responda" in system and "assuma o mais provável" in system
    assert "somente habilidades" not in system  # trecho do modo rígido


def test_sem_trechos_o_modo_livre_manda_responder_mesmo_assim(client, groq):
    send(client, "obrigado!")
    assert "Responda mesmo assim" in system_of(groq)


def test_modo_rigido_continua_disponivel(settings, groq):
    settings.rag_strict = True
    with make_client(settings, groq) as client:
        send(client, "obrigado!")
    system = system_of(groq)
    assert "somente habilidades" in system and "Responda mesmo assim" not in system


def test_falha_na_busca_nos_documentos_nao_impede_a_resposta(settings, groq, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("índice corrompido")

    monkeypatch.setattr("app.rag.store.KnowledgeBase.search", boom)
    with make_client(settings, groq) as client:
        r = send(client, "plano de matemática do 5º ano")
    assert r.status_code == 200
    assert "nenhum trecho dos documentos foi recuperado" in system_of(groq)


# ----------------------------------------------------------------------- títulos
def test_titulo_ja_aparece_na_conversa_aberta(client):
    cid = send(client, "plano de ciências para o 4º ano sobre plantas").json()["conversationId"]
    detail = client.get(f"/api/conversations/{cid}", params={"installation_id": INST}).json()
    assert detail["title"] == "Plano de aula · Ciências · 4º ano · plantas"


def test_conversas_antigas_sem_titulo_ganham_titulo_ao_iniciar(settings, groq):
    with sqlite3.connect(settings.database_path) as db:
        db.executescript(EF_SCHEMA)
        db.executemany('INSERT INTO "Conversations" ("Title","InstallationId","UpdatedAt") VALUES (?,?,?)',
                       [("Nova conversa", INST, "2026-09-20 02:13:21.1"), (None, INST, "2026-09-21 02:13:21.1"),
                        ("Título que o usuário escolheu", INST, "2026-09-22 02:13:21.1")])
        db.executemany('INSERT INTO "MessageEntities" ("ConversationId","Role","Content") VALUES (?,?,?)',
                       [(1, "user", "plano de aula de história do 8º ano sobre a república"), (1, "assistant", "ok"),
                        (2, "user", "atividade de geografia para o 6º ano sobre clima"), (3, "user", "qualquer")])
    with make_client(settings, groq) as client:
        titles = {c["id"]: c["title"] for c in conv_list(client)}
    assert titles[1] == "Plano de aula · História · 8º ano · república"
    assert titles[2] == "Atividade · Geografia · 6º ano · clima"
    assert titles[3] == "Título que o usuário escolheu"  # o que o usuário escolheu não é tocado
