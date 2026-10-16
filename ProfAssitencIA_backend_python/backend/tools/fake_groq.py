"""Groq FALSO para desenvolvimento e demonstração (sem chave e sem internet).

Imita /chat/completions e /audio/transcriptions e devolve um plano de aula de
exemplo montado a partir do CONTEXTO CURRICULAR que o backend enviou, então dá
para ver o RAG funcionando sem gastar o limite do plano gratuito.

Uso (em outro terminal, com o ambiente virtual ativo, dentro de backend/):
    python tools/fake_groq.py                  # escuta em 127.0.0.1:9911
    # no .env:  GROQ_API_KEY=qualquer-coisa
    #           GROQ_BASE_URL=http://127.0.0.1:9911/openai/v1

Palavras especiais na mensagem: "devagar" (demora 4 s) e "erro429" (simula limite de uso).
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
| Momento | Tempo | Atividade |
|---|---|---|
| Abertura | 10 min | Pizza dividida em partes iguais, a R$ 20 cada |
| Prática | 30 min | Dobraduras de papel e reta numérica |
| Fechamento | 10 min | Registro no caderno |

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
        system = msgs[0]["content"] if msgs[0]["role"] == "system" else ""
        m = re.search(r"\((EF05MA03)\)\s*([^\n]{20,160})", system)
        code, skill = (m.group(1), m.group(2).strip()) if m else ("EF05MA03", "Identificar e representar frações")
        pg = re.search(r"\[1\] BNCC, (p\. \d+)", system)
        text = PLAN.format(code=code, skill=skill, page=pg.group(1) if pg else "p. 295") if "plano" in user.lower() or "aula" in user.lower() else "Claro! Em que posso ajudar?"
        self._send(200, {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]})

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9911
    print(f"Groq falso em http://127.0.0.1:{port}/openai/v1  (Ctrl+C para sair)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
