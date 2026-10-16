# ProfAssistenc IA

<p align="center">
	<strong>Assistente de planejamento de aulas alinhado à BNCC e ao Referencial Curricular de Rondônia</strong>
</p>

<p align="center">
	<img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
	<img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3" />
	<img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript" />
	<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
	<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
	<img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
	<img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logoColor=white" alt="Groq" />
	<img src="https://img.shields.io/badge/Llama-0467DF?style=for-the-badge&logo=meta&logoColor=white" alt="Llama" />
	<img src="https://img.shields.io/badge/Whisper-412991?style=for-the-badge&logoColor=white" alt="Whisper" />
</p>

## Sobre o projeto

O **ProfAssistenc IA** ajuda professores a planejar aulas com Inteligência Artificial **sem inventar currículo**: a cada pedido, o sistema consulta a **BNCC** e o **Referencial Curricular para o Ensino Médio de Rondônia (RCSEERO)**, entrega os trechos relevantes à IA e confere se os códigos de habilidade citados na resposta existem de fato nesses documentos.

O sistema é dividido em:

* **Frontend:** HTML, CSS e JavaScript puros, sem frameworks e sem CDN (funciona sem internet, exceto a chamada à IA).
* **Backend:** API REST em Python com FastAPI.
* **IA:** Llama (`llama-3.1-8b-instant`) para texto e Whisper (`whisper-large-v3-turbo`) para voz, ambos pela API da **Groq**.
* **RAG:** busca BM25 (SQLite FTS5) nos PDFs oficiais, com conhecimento do domínio (ano + componente → códigos de habilidade).
* **Persistência:** SQLite com SQLAlchemy para conversas e mensagens.

> **Histórico:** o backend nasceu em C# (ASP.NET Core), foi reescrito em Python e passou do Gemini para a Groq por instabilidade. O contrato da API e o banco de conversas se mantiveram compatíveis em todas as etapas. Veja [Diferenças em relação às versões anteriores](docs/DOCUMENTACAO.md#diferenças-em-relação-às-versões-anteriores).

## Funcionalidades

* Conversa com o assistente, usando o histórico da conversa.
* **Planos de aula que seguem os documentos oficiais:** habilidades com código, objetos de conhecimento e página de origem.
* **Trava anti-invenção:** códigos de habilidade que não existem na BNCC/RCSEERO geram um alerta na própria resposta.
* **Voz:** gravar a pergunta (Whisper), "conversa por voz" (envia sozinho e lê a resposta) e botão **Ouvir** em cada resposta.
* Modelos de pedido (plano de aula, sequência didática, atividade avaliativa, aula de revisão) com campos `[entre colchetes]` navegáveis por `Tab`.
* **Imprimir** só o plano gerado e **copiar** a resposta ou a conversa.
* Fórmulas matemáticas (KaTeX) e tabelas nas respostas.
* Histórico de conversas por instalação: renomear, excluir, reabrir.
* Tema claro e escuro, layout para celular.
* Documentação interativa dos endpoints (Swagger).

## Tecnologias

### Frontend

* HTML5, CSS3 e JavaScript (sem framework)
* [marked](https://github.com/markedjs/marked), [DOMPurify](https://github.com/cure53/DOMPurify), [KaTeX](https://katex.org) e [Lucide](https://lucide.dev), embutidos em `frontend/vendor/`

### Backend

* Python 3.11+
* FastAPI + Uvicorn
* SQLAlchemy 2 + SQLite (conversas) e SQLite FTS5 (busca nos documentos)
* Pydantic, HTTPX
* Groq API (Llama e Whisper)
* PyMuPDF (apenas para gerar a base de conhecimento a partir dos PDFs)
* Pytest

## Arquitetura

```text
python run.py
        │
        ▼
FastAPI (Uvicorn)
        │
        ├── Frontend (arquivos estáticos)
        ├── API REST (routers)
        ├── Serviços ─┬── RAG: busca nos PDFs oficiais (SQLite FTS5)
        │             ├── Groq · Llama (respostas e títulos)
        │             └── Groq · Whisper (voz → texto)
        └── SQLAlchemy ── SQLite (conversas)
```

A interface fica em `http://localhost:5000`. Com `python run.py` (ou o executável) o navegador abre sozinho.

## Estrutura do projeto

```text
ProfAssitencIA_IA_agent/
├── assets/                     favicon (svg e png)
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   └── vendor/                 marked, DOMPurify, KaTeX (+ fontes)
├── backend/
│   ├── app/
│   │   ├── routers/            lesson_plan, conversations, transcribe
│   │   ├── services/           groq_client, ai_service, lesson_plan_service,
│   │   │                       transcription_service, conversation_service
│   │   ├── rag/                text (stemmer/códigos), intent, store (busca), ingest (PDFs)
│   │   ├── prompts.py          instruções de sistema
│   │   ├── config.py · database.py · models.py · schemas.py
│   │   ├── dependencies.py · domain.py · main.py
│   ├── data/knowledge.sqlite   base de conhecimento (BNCC + RCSEERO já indexados)
│   ├── tests/                  testes automatizados
│   ├── tools/fake_groq.py      Groq falso para desenvolvimento
│   ├── run.py
│   ├── requirements*.txt
│   └── .env.example
├── docs/
│   ├── INSTALACAO.md
│   └── DOCUMENTACAO.md
└── README.md
```

## Instalação rápida

Pré-requisitos: **Python 3.11+** e uma **chave gratuita da [Groq](https://console.groq.com/keys)**.

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Linux/macOS:           source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env  — depois preencha GROQ_API_KEY
python run.py
```

Passo a passo completo (voz, limites do plano gratuito, executável, solução de problemas): **[docs/INSTALACAO.md](docs/INSTALACAO.md)**.

## Documentação

| Documento                                    | Conteúdo                                                                    |
| -------------------------------------------- | --------------------------------------------------------------------------- |
| [docs/INSTALACAO.md](docs/INSTALACAO.md)     | Instalação, configuração, voz, base de conhecimento, executável, problemas  |
| [docs/DOCUMENTACAO.md](docs/DOCUMENTACAO.md) | Arquitetura, RAG, API, Groq, voz, frontend, configurações, testes, limites  |

Com o servidor rodando, a documentação interativa da API fica em `http://localhost:5000/docs`.

## Endpoints principais

| Método   | Endpoint                  | Descrição                                           |
| -------- | ------------------------- | --------------------------------------------------- |
| `POST`   | `/api/lessonplan`         | Envia uma mensagem e gera a resposta (com RAG)      |
| `POST`   | `/api/transcribe`         | Transcreve um áudio para texto (Whisper)            |
| `GET`    | `/api/conversations`      | Lista as conversas da instalação                    |
| `GET`    | `/api/conversations/{id}` | Consulta uma conversa e suas mensagens              |
| `PATCH`  | `/api/conversations/{id}` | Atualiza o título                                   |
| `DELETE` | `/api/conversations/{id}` | Exclui uma conversa                                 |
| `GET`    | `/api/health`             | Status da API, da IA e da base de documentos        |

## Fluxo de uma conversa

```text
Professor escreve (ou fala) o pedido
        ↓
[voz] áudio → /api/transcribe → Whisper → texto
        ↓
/api/lessonplan recebe a mensagem
        ↓
RAG: lê ano/componente do pedido e busca os trechos na BNCC e no RCSEERO
        ↓
Prompt = regras + trechos oficiais + histórico recente + pedido
        ↓
Llama (Groq) escreve o plano
        ↓
Backend confere os códigos de habilidade e acrescenta os documentos consultados
        ↓
Pergunta e resposta são gravadas no SQLite → frontend exibe
```

## Atalhos de teclado

* `Enter` envia · `Shift + Enter` quebra a linha.
* `Tab` (em um modelo de pedido) pula para o próximo campo `[entre colchetes]`.
* `Esc` cancela uma gravação de voz em andamento.

## Limites que você precisa conhecer

* A IA pode errar. O projeto reduz o risco (documentos oficiais + conferência de códigos), mas **não o elimina**: o professor deve conferir o plano.
* **BNCC** cobre Educação Infantil, Ensino Fundamental e Ensino Médio. O **RCSEERO** cobre só o **Ensino Médio**. Para Educação Infantil e Fundamental não há referencial estadual nos documentos carregados.
* Os documentos definem habilidades, objetos de conhecimento e princípios pedagógicos, mas **não trazem um modelo oficial de plano de aula**. A estrutura do plano é definida em `backend/app/prompts.py` e pode ser ajustada.
* O texto das conversas e o áudio são enviados à Groq. Não inclua dados pessoais de estudantes.

## Colaboradores

| Integrante        | Responsabilidade                                                                   | GitHub                                              |
| ----------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Raycka Castro** | Desenvolvimento do frontend com HTML, CSS e JavaScript                             | [Rayck4dev](https://github.com/Rayck4dev)           |
| **Victor Macedo** | Desenvolvimento do backend com Python, FastAPI, banco de dados e integração com IA | [VictorMacedoCB](https://github.com/VictorMacedoCB) |

## Objetivo acadêmico

O **ProfAssistenc IA** foi desenvolvido como projeto acadêmico com o objetivo de aplicar conhecimentos de desenvolvimento de software, APIs, persistência de dados e integração com Inteligência Artificial em uma aplicação prática voltada à educação.

Além da construção da aplicação, o projeto possibilitou o estudo e aplicação de conceitos como:

* APIs REST;
* Injeção de Dependência;
* ORM (SQLAlchemy) e banco de dados relacional;
* Recuperação de informação (BM25) e RAG;
* Integração com APIs externas (LLM e reconhecimento de voz);
* Arquitetura de aplicações em camadas;
* Testes automatizados;
* Interface acessível e responsiva.

## Licença

Este projeto foi desenvolvido para fins acadêmicos e de extensão. As bibliotecas em `frontend/vendor/` mantêm as licenças originais (veja `frontend/vendor/README.md`). A BNCC e o Referencial Curricular de Rondônia são documentos oficiais de seus respectivos órgãos.
