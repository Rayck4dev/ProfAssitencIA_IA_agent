from __future__ import annotations

AUDIO = b"\x1aE\xdf\xa3" + b"\x00" * 3000  # cabeçalho webm + enchimento


def post(client, data=AUDIO, content_type="audio/webm;codecs=opus", name="gravacao.webm"):
    return client.post("/api/transcribe", files={"audio": (name, data, content_type)})


def test_transcricao_envia_whisper_em_portugues_e_devolve_o_texto(client, groq):
    groq.transcript = {"text": "plano de aula", "segments": [{"text": " plano de aula", "no_speech_prob": 0.01, "avg_logprob": -0.2}]}
    r = post(client)
    assert r.status_code == 200 and r.json() == {"text": "plano de aula"}

    request = groq.requests[0]
    assert request.url.path.endswith("/audio/transcriptions")
    assert request.headers["authorization"] == "Bearer chave-de-teste"
    body = request.content
    assert b"whisper-large-v3-turbo" in body and b'name="language"' in body and b"\r\n\r\npt\r\n" in body
    assert b'filename="audio.webm"' in body


def test_segmentos_de_silencio_sao_descartados(client, groq):
    groq.transcript = {"text": "x", "segments": [
        {"text": " crie uma aula", "no_speech_prob": 0.05, "avg_logprob": -0.3},
        {"text": " Obrigado por assistir!", "no_speech_prob": 0.9, "avg_logprob": -1.4},
    ]}
    assert post(client).json()["text"] == "crie uma aula"


def test_so_silencio_devolve_texto_vazio(client, groq):
    groq.transcript = {"text": "Obrigado.", "segments": [{"text": " Obrigado.", "no_speech_prob": 0.95, "avg_logprob": -1.8}]}
    assert post(client).json()["text"] == ""


def test_formatos_do_safari_e_firefox_sao_aceitos(client, groq):
    assert post(client, content_type="audio/mp4").status_code == 200
    assert b'filename="audio.mp4"' in groq.requests[-1].content
    assert post(client, content_type="audio/ogg;codecs=opus").status_code == 200
    assert b'filename="audio.ogg"' in groq.requests[-1].content


def test_validacoes_de_audio(client, groq, settings):
    assert post(client, content_type="text/plain").status_code == 415
    assert post(client, data=b"x" * 10).status_code == 400
    settings.max_audio_mb = 0
    assert post(client).status_code == 413
    assert groq.requests == []  # nada foi enviado ao Groq


def test_falha_do_groq_na_transcricao(client, groq):
    groq.fail_with = 500
    assert post(client).status_code == 502
    groq.fail_with, groq.fail_headers = 429, {"retry-after": "600"}
    assert post(client).status_code == 429
