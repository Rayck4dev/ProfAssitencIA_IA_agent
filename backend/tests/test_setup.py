"""Configuração da chave pela interface, pasta de dados e inicialização do programa."""

from __future__ import annotations

import http.server
import json
import logging
import socket
import sys
import threading

import httpx
import pytest
from conftest import make_client
from fastapi.testclient import TestClient

from app import config, launcher
from app.envfile import mask_key, set_env_value
from app.main import create_app

KEY = "gsk_chaveValida1234567890abcdef"
HEADERS = {"X-ProfAssistenc": "1"}


def post_key(client, key=KEY, headers=HEADERS):
    return client.post("/api/setup/key", json={"api_key": key}, headers=headers)


@pytest.fixture
def unconfigured(settings, groq):
    settings.groq_api_key = ""
    settings.env_path = settings.database_path.parent / "config" / ".env"
    with make_client(settings, groq) as client:
        yield client, settings


# ------------------------------------------------------------------ tela de configuração
def test_status_sem_chave_e_com_chave(unconfigured):
    client, settings = unconfigured
    assert client.get("/api/setup").json() == {"configured": False, "keyHint": None, "storedIn": str(settings.env_path)}
    assert post_key(client).status_code == 200
    status = client.get("/api/setup").json()
    assert status["configured"] is True and status["keyHint"] == "gsk_…cdef"
    assert KEY not in json.dumps(status)  # a chave completa nunca volta para o navegador


def test_chave_valida_e_testada_gravada_no_env_e_vale_na_hora(unconfigured, groq):
    client, settings = unconfigured
    settings.env_path.parent.mkdir(parents=True)
    settings.env_path.write_text("# comentário\nPORT=5001\nGROQ_API_KEY=antiga\nRAG_TOP_K=4\n", encoding="utf-8")

    response = post_key(client, f'  "{KEY}"  ')  # espaços e aspas são ignorados
    assert response.status_code == 200 and response.json()["configured"] is True

    content = settings.env_path.read_text(encoding="utf-8")
    assert content.splitlines() == ["# comentário", "PORT=5001", f"GROQ_API_KEY={KEY}", "RAG_TOP_K=4"]
    assert groq.requests[0].method == "GET" and groq.requests[0].headers["authorization"] == f"Bearer {KEY}"

    # sem reiniciar: a próxima pergunta já usa a chave nova
    assert client.post("/api/lessonplan", json={"installation_id": "x", "message": "plano de aula"}).status_code == 200
    assert groq.requests[-1].headers["authorization"] == f"Bearer {KEY}"
    assert client.get("/api/health").json()["aiConfigured"] is True


def test_cria_o_env_se_nao_existir(unconfigured):
    client, settings = unconfigured
    assert not settings.env_path.exists()
    post_key(client)
    assert settings.env_path.read_text(encoding="utf-8").splitlines()[-1] == f"GROQ_API_KEY={KEY}"


def test_chave_recusada_pela_groq_nao_e_salva(unconfigured, groq):
    client, settings = unconfigured
    groq.rejected_keys.add(KEY)
    r = post_key(client)
    assert r.status_code == 400 and "recusou essa chave" in r.text
    assert not settings.env_path.exists() and settings.groq_api_key == ""


def test_formato_invalido_nem_chega_a_groq(unconfigured, groq):
    client, _ = unconfigured
    assert post_key(client, "curta").status_code == 400
    assert post_key(client, "chave com espaço no meio 1234567890").status_code == 400
    assert groq.requests == []


def test_sem_internet_ao_testar_a_chave(settings):
    settings.groq_api_key = ""
    settings.env_path = settings.database_path.parent / ".env"

    def boom(request):
        raise httpx.ConnectError("sem internet")

    app = create_app(settings, http_client=httpx.Client(transport=httpx.MockTransport(boom)))
    with TestClient(app) as client:
        r = post_key(client)
    assert r.status_code == 502 and "internet" in r.text and not settings.env_path.exists()


def test_limite_de_uso_ao_testar_ainda_prova_que_a_chave_existe(unconfigured, groq):
    client, _ = unconfigured
    groq.models_status = 429
    assert post_key(client).status_code == 200


def test_so_aceita_pedidos_da_propria_interface(unconfigured):
    client, settings = unconfigured
    assert post_key(client, headers={}).status_code == 403  # sem o cabeçalho personalizado
    foreign = {**HEADERS, "Origin": "https://site-malicioso.example"}
    assert post_key(client, headers=foreign).status_code == 403
    own = {**HEADERS, "Origin": "http://testserver"}
    assert post_key(client, headers=own).status_code == 200
    assert settings.groq_api_key == KEY


def test_erro_de_gravacao_vira_mensagem_clara(unconfigured, monkeypatch):
    client, settings = unconfigured

    def denied(*args, **kwargs):
        raise PermissionError("somente leitura")

    monkeypatch.setattr("app.routers.setup.set_env_value", denied)
    r = post_key(client)
    assert r.status_code == 500 and "sem permissão" in r.text and settings.groq_api_key == ""


def test_mensagens_de_erro_orientam_a_configurar_a_chave(unconfigured):
    client, _ = unconfigured
    r = client.post("/api/lessonplan", json={"installation_id": "x", "message": "oi"})
    assert r.status_code == 502 and "Chave da IA" in r.text


# ------------------------------------------------------------------------- envfile
def test_set_env_value_substitui_acrescenta_e_preserva(tmp_path):
    path = tmp_path / ".env"
    set_env_value(path, "GROQ_API_KEY", "um")
    assert path.read_text(encoding="utf-8").splitlines()[0].startswith("# Configurações")
    set_env_value(path, "PORT", "5001")
    set_env_value(path, "GROQ_API_KEY", "dois")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines.count("GROQ_API_KEY=dois") == 1 and "GROQ_API_KEY=um" not in lines and "PORT=5001" in lines
    assert not list(tmp_path.glob("*.tmp"))  # sem arquivo temporário sobrando


def test_mask_key():
    assert mask_key("gsk_abcdefghijklmnop1234") == "gsk_…1234" and mask_key("curta") == "…"


# ------------------------------------------------------------ pasta de dados no executável
def test_executavel_grava_ao_lado_do_programa_quando_possivel(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ProfAssistenc.exe"))
    assert config._app_dir() == tmp_path.resolve()


def test_executavel_em_pasta_protegida_usa_a_pasta_do_usuario(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Program Files" / "ProfAssistenc.exe"))
    monkeypatch.setattr(config, "_writable", lambda folder: False)  # como em "Program Files"
    monkeypatch.setattr(config, "user_data_dir", lambda: tmp_path / "AppData" / "ProfAssistenc")
    folder = config._app_dir()
    assert folder == tmp_path / "AppData" / "ProfAssistenc" and folder.is_dir()


def test_pasta_do_usuario_por_sistema(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    assert config.user_data_dir() == tmp_path / "Local" / "ProfAssistenc"
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    assert config.user_data_dir() == tmp_path / "share" / "ProfAssistenc"


# ------------------------------------------------------------------------- inicialização
class _Health(http.server.BaseHTTPRequestHandler):
    body = {"status": "ok", "knowledgeBase": {}}

    def do_GET(self):
        data = json.dumps(self.body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def _serve(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def test_detecta_programa_ja_aberto_e_ignora_outros_servidores():
    server, port = _serve(_Health)
    try:
        assert launcher.already_running(port) is True
    finally:
        server.shutdown()

    class Outro(_Health):
        body = {"hello": "world"}

    server, port = _serve(Outro)
    try:
        assert launcher.already_running(port) is False  # há um servidor, mas não é o ProfAssistenc
    finally:
        server.shutdown()
    assert launcher.already_running(port) is False  # nada escutando


def test_detecta_porta_ocupada():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        port = s.getsockname()[1]
        assert launcher.port_in_use(port) is True
    assert launcher.port_in_use(port) is False  # liberada ao fechar


@pytest.mark.skipif(sys.platform == "win32", reason="TIME_WAIT bloqueando bind é comportamento de Linux/macOS")
def test_porta_recem_usada_em_time_wait_nao_conta_como_ocupada():
    """O professor fecha o programa e reabre em seguida: a porta está livre, só em TIME_WAIT."""
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen()
    port = server.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port))
    connection, _ = server.accept()
    connection.close()  # o lado do servidor fecha primeiro: a porta fica em TIME_WAIT
    client.close()
    server.close()

    with socket.socket() as plain:  # prova de que o teste é válido: um bind simples falha mesmo sem ninguém usando
        with pytest.raises(OSError):
            plain.bind(("127.0.0.1", port))
    assert launcher.port_in_use(port) is False


def test_log_em_arquivo_registra_avisos_sem_conteudo_de_conversa(tmp_path):
    root = logging.getLogger()
    before = list(root.handlers)
    # Como o uvicorn configura em produção: "uvicorn" e "uvicorn.access" não propagam ao root.
    saved = {n: logging.getLogger(n).propagate for n in ("uvicorn", "uvicorn.access")}
    for name in saved:
        logging.getLogger(name).propagate = False
    try:
        path = launcher.configure_file_logging(tmp_path)
        logging.getLogger("app.teste").warning("aviso de teste")
        logging.getLogger("uvicorn.error").warning("linha do servidor")
        for handler in root.handlers:
            handler.flush()
        content = path.read_text(encoding="utf-8")
        assert path == tmp_path / "profassistenc.log" and "aviso de teste" in content
        assert content.count("linha do servidor") == 1  # sem linhas duplicadas
    finally:
        for name, value in saved.items():
            logging.getLogger(name).propagate = value
        for name in ("", "uvicorn", "uvicorn.access"):
            lg = logging.getLogger(name)
            for h in list(lg.handlers):
                if h not in before:
                    lg.removeHandler(h)
                    h.close()
