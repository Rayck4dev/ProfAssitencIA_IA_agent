"""Groq FALSO para desenvolvimento e demonstração (sem chave e sem internet).

Imita /chat/completions e /audio/transcriptions e devolve um plano de aula de
exemplo montado a partir do CONTEXTO CURRICULAR que o backend enviou, então dá
para ver o RAG funcionando sem gastar o limite do plano gratuito.

Uso (em outro terminal, com o ambiente virtual ativo, dentro de backend/):
    python tools/fake_groq.py                  # escuta em 127.0.0.1:9911
    # no .env:  GROQ_API_KEY=qualquer-coisa
    #           GROQ_BASE_URL=http://127.0.0.1:9911/openai/v1

Palavras especiais na mensagem: "devagar" (demora 4 s), "erro429" (simula limite de uso)
e "longo" (simula uma resposta cortada pelo limite de tamanho, para testar o botão Continuar).
Os textos NÃO vêm de um modelo de verdade: servem só para testar a interface.
"""
import json, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PLAN = """## Identificação
**Etapa:** Ensino Fundamental · **Ano:** 5º ano · **Componente:** Matemática · **Duração:** 50 minutos

## Habilidades
- **{code}** — {skill} *(BNCC, {page})*
- **EF05MA99** — habilidade que a IA inventou

## Objetivos de aprendizagem
Representar frações na reta numérica, como \\(\\frac{{3}}{{4}}\\) de uma unidade.

$$\\frac{{a}}{{b}} = \\frac{{a \\cdot k}}{{b \\cdot k}}$$

## Desenvolvimento
| Momento | Tempo | Atividade | Recursos | Avaliação |
|---|---|---|---|---|
| Abertura e contextualização | 10 min | Pizza dividida em partes iguais, a R$ 20 cada, para introduzir a ideia de fração | Imagens, pizza de papel | Observação das respostas orais |
| Desenvolvimento | 30 min | Dobraduras de papel e representação na reta numérica em duplas | Papel sulfite, régua, canetas | Registro individual no caderno |
| Fechamento e sistematização | 10 min | Socialização das descobertas e registro coletivo no quadro | Quadro, giz | Autoavaliação em roda de conversa |

1. Retome o que os alunos sabem sobre **divisão**.
2. Proponha a dobradura.

## Avaliação
Observação formativa dos registros.
"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, status, body, headers=None):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items(): self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path.endswith("/models"):  # teste de chave da tela de configuração
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if token.startswith("invalida"):
                return self._send(401, {"error": {"message": "Invalid API Key"}})
            return self._send(200, {"data": [{"id": "openai/gpt-oss-20b"}]})
        self._send(404, {"error": {"message": "not found"}})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.endswith("/audio/transcriptions"):
            return self._send(200, {"text": "Crie um plano de aula de matemática para o 5º ano sobre frações",
                "segments": [{"text": " Crie um plano de aula de matemática para o 5º ano sobre frações",
                              "no_speech_prob": 0.02, "avg_logprob": -0.2}]})
        body = json.loads(raw)
        msgs = body["messages"]
        user = [m for m in msgs if m["role"] == "user"][-1]["content"]
        if user.startswith("Gere um título curto"):
            return self._send(200, {"choices": [{"message": {"content": "Frações no 5º ano"}, "finish_reason": "stop"}]})
        if "erro429" in user:
            return self._send(429, {"error": {"message": "rate"}}, {"retry-after": "3600"})
        if "devagar" in user: time.sleep(4)
        if user.lower().startswith("continue"):
            return self._send(200, {"choices": [{"message": {"content": "## Continuação\nEste trecho continua o plano de onde ele parou."}, "finish_reason": "stop"}]})
        system = msgs[0]["content"] if msgs[0]["role"] == "system" else ""
        m = re.search(r"\((EF05MA03)\)\s*([^\n]{20,160})", system)
        code, skill = (m.group(1), m.group(2).strip()) if m else ("EF05MA03", "Identificar e representar frações")
        pg = re.search(r"\[1\] BNCC, (p\. \d+)", system)
        text = PLAN.format(code=code, skill=skill, page=pg.group(1) if pg else "p. 295") if "plano" in user.lower() or "aula" in user.lower() else "Claro! Em que posso ajudar?"
        finish = "length" if "longo" in user.lower() else "stop"  # "longo" simula resposta cortada
        self._send(200, {"choices": [{"message": {"content": text}, "finish_reason": finish}]})

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9911
    print(f"Groq falso em http://127.0.0.1:{port}/openai/v1  (Ctrl+C para sair)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
