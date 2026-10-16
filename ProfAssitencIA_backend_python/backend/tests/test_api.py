from __future__ import annotations

import sqlite3

from conftest import make_client

INST = "instalacao-1"


def send(client, message="Crie um plano de aula", conversation_id=None, inst=INST):
    body = {"installation_id": inst, "message": message}
    if conversation_id is not None:
        body["conversation_id"] = conversation_id
    return client.post("/api/LessonPlan", json=body)


def conv_list(client, inst=INST):
    return client.get("/api/conversations", params={"installation_id": inst}).json()["conversations"]


# ------------------------------------------------------------------- conversa
def test_nova_conversa_gera_resposta_titulo_e_persiste(client, groq):
    response = send(client)
    assert response.status_code == 200
    data = response.json()
    assert data["response"].startswith("Resposta da IA")
    assert data["conversationId"].isdigit()

    item = conv_list(client)[0]
    assert item["title"] == "Título gerado"
    assert item["updatedAt"].endswith("Z")
    assert str(item["id"]) == data["conversationId"]


def test_continuacao_envia_historico_e_system_primeiro(client, groq):
    first = send(client, "olá, preciso de ajuda").json()
    groq.answer = "segunda resposta"
    second = send(client, "e agora?", conversation_id=first["conversationId"]).json()
    assert second["conversationId"] == first["conversationId"]

    messages = groq.chat_payloads()[-1]["messages"]
    assert messages[0]["role"] == "system"
    assert [(m["role"], m["content"]) for m in messages[1:]] == [
        ("user", "olá, preciso de ajuda"),
        ("assistant", "Resposta da IA"),
        ("user", "e agora?"),
    ]
    detail = client.get(f"/api/conversations/{first['conversationId']}", params={"installation_id": INST}).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]


def test_requisicao_usa_bearer_modelo_e_limite_de_tokens(client, groq):
    send(client)
    request = groq.requests[0]
    assert request.headers["authorization"] == "Bearer chave-de-teste"
    assert "chave-de-teste" not in str(request.url)
    assert request.url.path.endswith("/chat/completions")
    body = groq.chat_payloads()[0]
    assert body["model"] == "llama-3.1-8b-instant"
    assert body["max_tokens"] == 1500


def test_resposta_cortada_pelo_limite_avisa(client, groq):
    groq.finish_reason = "length"
    assert "cortada pelo limite" in send(client).json()["response"]


def test_campos_extras_do_frontend_sao_ignorados(client):
    r = client.post("/api/LessonPlan", json={"installation_id": INST, "conversation_id": None,
                                             "message": "oi", "messages": [{"role": "user", "content": "oi"}]})
    assert r.status_code == 200


def test_conversation_id_numerico_tambem_e_aceito(client):
    first = send(client).json()
    assert send(client, conversation_id=int(first["conversationId"])).status_code == 200


# ----------------------------------------------------------------------- RAG
def test_rag_injeta_contexto_no_system_e_cita_documentos(client, groq):
    answer = send(client, "Crie um plano de aula sobre frações para o 5º ano de Matemática").json()["response"]

    system = groq.chat_payloads()[0]["messages"][0]["content"]
    assert "CONTEXTO CURRICULAR" in system
    assert "(EF05MA03)" in system and "BNCC, p. 295" in system
    assert "DOCUMENTOS DISPONÍVEIS" in system and "RCSEERO" in system
    assert "NUNCA invente códigos" in system
    assert "**Documentos consultados:** BNCC (p. 295)" in answer


def test_codigo_inexistente_gera_alerta_e_existente_nao(client, groq):
    groq.answer = "Trabalhe EF05MA03 e também EF05MA99."
    answer = send(client, "plano de matemática do 5º ano sobre frações").json()["response"]
    assert "⚠️ **Confira:** o código `EF05MA99`" in answer
    assert "`EF05MA03`" not in answer.split("Confira")[1]


def test_historico_nao_reenvia_rodape_de_fontes(client, groq):
    first = send(client, "plano de matemática do 5º ano sobre frações").json()
    send(client, "deixe mais curto", conversation_id=first["conversationId"])
    for message in groq.chat_payloads()[-1]["messages"][1:]:
        assert "Documentos consultados" not in message["content"]


def test_saudacao_nao_recupera_nada_e_nao_acrescenta_rodape(client, groq):
    answer = send(client, "obrigado!").json()["response"]
    assert "Documentos consultados" not in answer
    assert "nenhum trecho dos documentos foi recuperado" in groq.chat_payloads()[0]["messages"][0]["content"]


def test_pergunta_curta_herda_o_tema_da_anterior(settings, groq):
    with make_client(settings, groq) as client:
        first = send(client, "quero trabalhar frações em matemática").json()
        send(client, "e para o 5º ano?", conversation_id=first["conversationId"])
    system = groq.chat_payloads()[-1]["messages"][0]["content"]
    assert "(EF05MA03)" in system


def test_rag_desligado_usa_prompt_generico_sem_rodape(settings, groq):
    settings.rag_enabled = False
    with make_client(settings, groq) as client:
        answer = send(client, "plano de matemática do 5º ano sobre frações").json()["response"]
    assert "Documentos consultados" not in answer
    assert "CONTEXTO CURRICULAR" not in groq.chat_payloads()[0]["messages"][0]["content"]


def test_system_prompt_personalizado_substitui_o_padrao(settings, groq):
    settings.system_prompt = "Responda sempre em verso."
    with make_client(settings, groq) as client:
        send(client, "plano de matemática do 5º ano sobre frações")
    system = groq.chat_payloads()[0]["messages"][0]["content"]
    assert system.startswith("Responda sempre em verso.")
    assert "CONTEXTO CURRICULAR" in system  # o contexto continua sendo anexado


def test_historico_respeita_o_limite_e_mantem_a_ultima_resposta(settings, groq):
    settings.history_max_chars = 300
    with make_client(settings, groq) as client:
        groq.answer = "A" * 1000
        first = send(client, "primeira").json()
        send(client, "segunda", conversation_id=first["conversationId"])
    past = groq.chat_payloads()[-1]["messages"][1:-1]
    assert [m["role"] for m in past] == ["assistant"]  # a pergunta antiga foi descartada
    assert past[0]["content"].endswith("[…]") and len(past[0]["content"]) < 400


# ---------------------------------------------------------------- validações
def test_mensagem_vazia_retorna_400_em_texto_puro(client):
    response = send(client, "   ")
    assert (response.status_code, response.text) == (400, "Mensagem vazia")


def test_conversation_id_invalido_e_inexistente(client):
    assert send(client, conversation_id="abc").text == "Erro de conversao"
    r = send(client, conversation_id="999")
    assert (r.status_code, r.text) == (404, "Conversa nao encontrada")


def test_campos_obrigatorios_ausentes_retornam_400(client):
    assert client.post("/api/LessonPlan", json={"message": "oi"}).status_code == 400
    assert client.get("/api/conversations").status_code == 400


def test_instalacoes_sao_isoladas(client):
    cid = send(client, inst="A").json()["conversationId"]
    assert send(client, conversation_id=cid, inst="B").status_code == 404
    assert client.get(f"/api/conversations/{cid}", params={"installation_id": "B"}).status_code == 404
    assert client.delete(f"/api/conversations/{cid}", params={"installation_id": "B"}).status_code == 404
    assert client.patch(f"/api/conversations/{cid}", json={"installation_id": "B", "title": "x"}).status_code == 404
    assert conv_list(client, "B") == []


# --------------------------------------------------------------- falhas do Groq
def test_falha_do_groq_retorna_502_e_nao_grava_nada(client, groq):
    groq.fail_with = 400
    r = send(client)
    assert (r.status_code, r.text) == (502, "Não foi possível obter uma resposta da IA.")
    assert conv_list(client) == []


def test_5xx_e_repetido_ate_funcionar(client, groq):
    groq.transient = [(503, {}), (500, {})]
    assert send(client).status_code == 200
    assert len(groq.chat_payloads()) == 3


def test_5xx_persistente_esgota_as_tentativas(client, groq):
    groq.fail_with = 503
    assert send(client).status_code == 502
    assert len(groq.requests) == 3


def test_429_curto_espera_e_tenta_de_novo(client, groq):
    groq.transient = [(429, {"retry-after": "0"})]
    assert send(client).status_code == 200


def test_429_longo_avisa_o_usuario_sem_esperar(client, groq):
    groq.fail_with, groq.fail_headers = 429, {"retry-after": "3600"}
    r = send(client)
    assert r.status_code == 429
    assert "Limite de uso da IA atingido" in r.text and "60 minutos" in r.text
    assert len(groq.requests) == 1
    assert conv_list(client) == []


def test_chave_recusada_e_conversa_grande_demais(client, groq):
    groq.fail_with = 401
    assert "recusou a chave" in send(client).text
    groq.fail_with = 413
    r = send(client)
    assert r.status_code == 413 and "nova conversa" in r.text


def test_erro_de_rede_retorna_502(settings):
    import httpx
    from fastapi.testclient import TestClient
    from app.main import create_app

    def boom(request):
        raise httpx.ConnectError("sem internet")

    http = httpx.Client(transport=httpx.MockTransport(boom))
    with TestClient(create_app(settings, http_client=http)) as client:
        assert send(client).status_code == 502


def test_sem_chave_configurada_nao_chama_o_groq(settings, groq):
    settings.groq_api_key = ""
    with make_client(settings, groq) as client:
        r = send(client)
        assert r.status_code == 502 and "GROQ_API_KEY" in r.text
        assert client.get("/api/health").json()["aiConfigured"] is False
    assert groq.requests == []


def test_titulo_padrao_quando_a_geracao_falha_e_titulo_limpo(client, groq):
    groq.title = '"Plano de aula de frações"\nExplicação extra'
    send(client)
    assert conv_list(client)[0]["title"] == "Plano de aula de frações"
    groq.title = "   "
    send(client, "outra conversa")
    assert {c["title"] for c in conv_list(client)} == {"Plano de aula de frações", "Nova conversa"}


# ------------------------------------------------------ renomear / excluir / lista
def test_renomear_e_excluir(client):
    cid = send(client).json()["conversationId"]
    r = client.patch(f"/api/conversations/{cid}", json={"installation_id": INST, "title": "  Meu título  "})
    assert r.json()["title"] == "Meu título"
    assert client.patch(f"/api/conversations/{cid}", json={"installation_id": INST, "title": " "}).status_code == 400
    assert client.delete(f"/api/conversations/{cid}", params={"installation_id": INST}).status_code == 200
    assert client.get(f"/api/conversations/{cid}", params={"installation_id": INST}).status_code == 404


def test_lista_da_mais_recente_para_a_mais_antiga(client):
    old = send(client, "antiga").json()["conversationId"]
    new = send(client, "nova").json()["conversationId"]
    assert [c["id"] for c in conv_list(client)] == [int(new), int(old)]
    send(client, "de novo", conversation_id=old)
    assert [c["id"] for c in conv_list(client)] == [int(old), int(new)]


def test_rotas_ignoram_maiusculas_e_cors(client):
    assert client.get("/api/CONVERSATIONS", params={"installation_id": INST}).status_code == 200
    assert client.post("/api/lessonplan", json={"installation_id": INST, "message": "oi"}).status_code == 200
    r = client.options("/api/conversations", headers={"Origin": "http://localhost:5500",
                                                      "Access-Control-Request-Method": "GET"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5500"


def test_health_mostra_ia_e_base_de_conhecimento(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok" and data["aiConfigured"] is True
    assert data["model"] == "llama-3.1-8b-instant"
    assert data["knowledgeBase"]["available"] is True and data["knowledgeBase"]["documents"] == 2
    assert data["knowledgeBase"]["names"] == ["BNCC", "RCSEERO"]


def test_sem_base_de_conhecimento_o_app_funciona(settings, groq, tmp_path):
    settings.knowledge_db_path = tmp_path / "nao-existe.sqlite"
    with make_client(settings, groq) as client:
        assert send(client).status_code == 200
        assert client.get("/api/health").json()["knowledgeBase"]["available"] is False


# --------------------------------------------- compatibilidade com banco antigo (EF)
EF_SCHEMA = """
CREATE TABLE "Conversations" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Conversations" PRIMARY KEY AUTOINCREMENT,
    "Title" TEXT NULL, "InstallationId" TEXT NOT NULL, "UpdatedAt" TEXT NOT NULL);
CREATE TABLE "MessageEntities" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_MessageEntities" PRIMARY KEY AUTOINCREMENT,
    "ConversationId" INTEGER NOT NULL, "Role" TEXT NOT NULL, "Content" TEXT NOT NULL,
    CONSTRAINT "FK_M_C" FOREIGN KEY ("ConversationId") REFERENCES "Conversations" ("Id") ON DELETE CASCADE);
CREATE INDEX "IX_MessageEntities_ConversationId" ON "MessageEntities" ("ConversationId");
CREATE TABLE "__EFMigrationsHistory" ("MigrationId" TEXT PRIMARY KEY, "ProductVersion" TEXT NOT NULL);
"""


def test_banco_criado_pela_versao_csharp_continua_funcionando(settings, groq):
    with sqlite3.connect(settings.database_path) as db:
        db.executescript(EF_SCHEMA)
        db.execute('INSERT INTO "Conversations" ("Title","InstallationId","UpdatedAt") VALUES (?,?,?)',
                   ("Conversa antiga", INST, "2026-09-20 02:13:21.1234567"))
        db.executemany('INSERT INTO "MessageEntities" ("ConversationId","Role","Content") VALUES (1,?,?)',
                       [("user", "pergunta antiga"), ("assistant", "resposta antiga")])
    with make_client(settings, groq) as client:
        item = conv_list(client)[0]
        assert item["title"] == "Conversa antiga" and item["updatedAt"].startswith("2026-09-20T02:13:21")
        assert send(client, "e agora?", conversation_id="1").status_code == 200
        roles = [m["role"] for m in groq.chat_payloads()[-1]["messages"]]
        assert roles == ["system", "user", "assistant", "user"]
        assert client.delete("/api/conversations/1", params={"installation_id": INST}).status_code == 200
    with sqlite3.connect(settings.database_path) as db:
        assert db.execute('SELECT COUNT(*) FROM "MessageEntities"').fetchone() == (0,)
