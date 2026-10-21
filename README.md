<p align="center">
	<img src="assets/logo.svg" alt="ProfAssistenc — planejamento de aulas" width="340" />
</p>

# ProfAssistencIA

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
	<img src="https://img.shields.io/badge/gpt--oss-000000?style=for-the-badge&logo=openai&logoColor=white" alt="gpt-oss" />
	<img src="https://img.shields.io/badge/Whisper-412991?style=for-the-badge&logoColor=white" alt="Whisper" />
</p>

## Sobre o projeto

O **ProfAssistencIA** ajuda professores a planejar aulas com Inteligência Artificial **sem inventar currículo**: a cada pedido, o sistema consulta a **BNCC** e o **Referencial Curricular para o Ensino Médio de Rondônia (RCSEERO)**, entrega os trechos relevantes à IA e confere se os códigos de habilidade citados na resposta existem de fato nesses documentos.

O sistema é dividido em:

* **Frontend:** HTML, CSS e JavaScript puros, sem frameworks e sem CDN (funciona sem internet, exceto a chamada à IA).
* **Backend:** API REST em Python com FastAPI.
* **IA:** `openai/gpt-oss-20b` (modelo de raciocínio) para texto e Whisper (`whisper-large-v3-turbo`) para voz, ambos pela API da **Groq**. O modelo é configurável em `GROQ_MODEL`.
* **RAG:** busca BM25 (SQLite FTS5) nos PDFs oficiais, com conhecimento do domínio (ano + componente → códigos de habilidade).
* **Persistência:** SQLite com SQLAlchemy para conversas e mensagens.

> **Histórico:** o backend nasceu em C# (ASP.NET Core), foi reescrito em Python e passou do Gemini para a Groq por instabilidade. O contrato da API e o banco de conversas se mantiveram compatíveis em todas as etapas. 
Veja [Diferenças em relação às versões anteriores](docs/DOCUMENTACAO.md#diferenças-em-relação-às-versões-anteriores).
---

## Funcionalidades

* Conversa com o assistente, usando o histórico da conversa.
* **Pergunte do seu jeito:** pedidos informais, incompletos ou com erros de digitação ("matematca", "5 ano") são entendidos; o assistente assume o que faltar e avisa o que assumiu, em vez de recusar.
* **Respostas longas:** o espaço da resposta é calculado a cada pedido; se ainda assim for cortada, o botão **Continuar a resposta** segue de onde parou.
* **Título automático** de cada conversa, gerado na hora (sem gastar cota da IA).
* **Planos de aula que seguem os documentos oficiais:** habilidades com código, objetos de conhecimento e página de origem.
* **Trava anti-invenção:** códigos de habilidade que não existem na BNCC/RCSEERO geram um alerta na própria resposta.
* **Voz:** gravar a pergunta (Whisper), "conversa por voz" (envia sozinho e lê a resposta) e botão **Ouvir** em cada resposta.
* Modelos de pedido (plano de aula, sequência didática, atividade avaliativa, aula de revisão) com campos `[entre colchetes]` navegáveis por `Tab`.
* **Imprimir** só o plano gerado e **copiar** a resposta ou a conversa.
* Fórmulas matemáticas (KaTeX) e tabelas nas respostas.
* Histórico de conversas por instalação: renomear, excluir, reabrir.
* **Configuração pela interface:** a chave da IA é informada em uma janela (sem editar arquivos), testada e salva na hora.
* **Programa pronto para Windows** (`.exe`) e instalador, para usar sem Python.
* Tabelas largas e legíveis, **Ampliar** a largura e **recolher o menu** para ganhar espaço.
* Tema claro e escuro, layout para celular.
* Documentação interativa dos endpoints (Swagger).
---

## Tecnologias

### Frontend

* HTML5, CSS3 e JavaScript (sem framework)
* [Marked](https://github.com/markedjs/marked), [DOMPurify](https://github.com/cure53/DOMPurify), [KaTeX](https://katex.org) e [Lucide](https://lucide.dev), embutidos em `frontend/vendor/`

### Backend

* Python 3.11+
* FastAPI + Uvicorn
* SQLAlchemy 2 + SQLite (conversas) e SQLite FTS5 (busca nos documentos)
* Pydantic, HTTPX
* Groq API (gpt-oss e Whisper)
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
        │             ├── Groq · modelo de texto (respostas)
        │             └── Groq · Whisper (voz → texto)
        └── SQLAlchemy ── SQLite (conversas)
```

A interface fica em `http://localhost:5000`. Com `python run.py` (ou o executável) o navegador abre sozinho.

---
## Estrutura do projeto

```text
ProfAssitencIA_IA_agent/
├── assets/                     logo (logo.svg, logo-mark.svg) e favicons
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
│   │   ├── prompts.py          instruções de sistema (modo livre e rígido)
│   │   ├── titles.py           título automático da conversa
│   │   ├── config.py · database.py · models.py · schemas.py
│   │   ├── dependencies.py · domain.py · main.py
│   ├── data/knowledge.sqlite   base de conhecimento (BNCC + RCSEERO já indexados)
│   ├── tests/                  testes automatizados
│   ├── tools/fake_groq.py      Groq falso para desenvolvimento
│   ├── run.py · build_exe.py · construir_windows.bat
│   ├── requirements*.txt
│   └── .env.example
├── installer/                  instalador (Inno Setup) e LEIA-ME do pacote
├── docs/
│   ├── INSTALACAO_PROFESSORES.md · GUIA_DO_PROFESSOR.md · Manual-ProfAssistenc.pdf
│   ├── DISTRIBUICAO.md
│   ├── INSTALACAO.md           (guia técnico)
│   └── DOCUMENTACAO.md
└── README.md
```
---
## Para professores

O caminho mais simples é o programa pronto para Windows (**`.exe`**), **sem instalar Python**:

1. Baixe o **`ProfAssistenc-...-windows.zip`** (ou o instalador **`Setup.exe`**) e extraia.
2. Dê dois cliques em **ProfAssistencIA**.
3. Na primeira vez, cole a sua chave gratuita da Groq na janela que aparece (ela explica como criar).

Passo a passo ilustrado: 

* **[Guia de Instalação para Professores](docs/INSTALACAO_PROFESSORES.md)** 

· Como usar: 

* **[Guia do Professor](docs/GUIA_DO_PROFESSOR.md)** 

· Manual em PDF: 

* **[Manual ProfAssitencIA](docs/Manual-ProfAssistenc.pdf)**

Para gerar o `.exe`: 

* **[Guia de Distribuição](docs/DISTRIBUICAO.md)**

---
## Instalação rápida (desenvolvedores)

Pré-requisitos: 
* **Python 3.11+** 
* Uma **chave gratuita da [Groq](https://console.groq.com/keys)**.

```bash
cd backend

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Linux/macOS:           source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env 
# Windows: copy .env.example .env  — depois preencha GROQ_API_KEY

python run.py
```

Acesse o guia técnico completo (voz, limites do plano gratuito, base de documentos, testes, solução de problemas) em **[Guia de Instalação](docs/INSTALACAO.md)**.

---
## Documentação

| Documento                                    | Conteúdo                                                                    |
| -------------------------------------------- | --------------------------------------------------------------------------- |
| [Instalação para Professores](docs/INSTALACAO_PROFESSORES.md) | **Para professores:** instalar o programa (`.exe`) passo a passo |
| [Guia do Professor](docs/GUIA_DO_PROFESSOR.md) | **Para professores:** como usar, dicas e perguntas frequentes |
| [Guia de Distribuição](docs/DISTRIBUICAO.md) | **Para a equipe:** gerar o `.exe`/instalador, testar, publicar e atualizar |
| [Guia de Instalação](docs/INSTALACAO.md)     | **Guia técnico:** instalação pelo Python, configuração, voz, base de conhecimento, problemas |
| [Documentação](docs/DOCUMENTACAO.md) | Arquitetura, RAG, API, Groq, voz, frontend, configurações, testes, limites  |

Com o servidor rodando, a documentação interativa da API fica em **`http://localhost:5000/docs`**.

---
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

---
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
O modelo (Groq) escreve o plano, com espaço calculado para uma resposta longa
        ↓
Backend confere os códigos de habilidade e acrescenta os documentos consultados
        ↓
Pergunta e resposta são gravadas no SQLite → frontend exibe
```
---
## Atalhos de teclado

* **`Enter`** envia · **`Shift + Enter`** quebra a linha.
* **`Tab`** (em um modelo de pedido) pula para o próximo campo **`[entre colchetes]`**.
* **`Esc`** cancela uma gravação de voz em andamento.

---
## Limites que você precisa conhecer

* A IA pode errar. O projeto reduz o risco (documentos oficiais + conferência de códigos), mas **não o elimina**: o professor deve conferir o plano.
* **BNCC** cobre Educação Infantil, Ensino Fundamental e Ensino Médio. O **RCSEERO** cobre só o **Ensino Médio**. Para Educação Infantil e Fundamental não há referencial estadual nos documentos carregados.
* Os documentos definem habilidades, objetos de conhecimento e princípios pedagógicos, mas **não trazem um modelo oficial de plano de aula**. A estrutura do plano é definida em `backend/app/prompts.py` e pode ser ajustada.
* O texto das conversas e o áudio são enviados à Groq. Não inclua dados pessoais de estudantes.

---
## Colaboradores

| Integrante        | Responsabilidade                                                                   | GitHub                                              |
| ----------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Raycka Castro** | Desenvolvimento do frontend com HTML, CSS e JavaScript                             | [Rayck4dev](https://github.com/Rayck4dev)           |
| **Victor Macedo** | Desenvolvimento do backend com Python, FastAPI, banco de dados e integração com IA | [VictorMacedoCB](https://github.com/VictorMacedoCB) |

---
## Objetivo acadêmico

O **ProfAssistencIA** foi desenvolvido como projeto acadêmico com o objetivo de aplicar conhecimentos de desenvolvimento de software, APIs, persistência de dados e integração com Inteligência Artificial em uma aplicação prática voltada à educação.

Além da construção da aplicação, o projeto possibilitou o estudo e aplicação de conceitos como:

* APIs REST;
* Injeção de Dependência;
* ORM (SQLAlchemy) e banco de dados relacional;
* Recuperação de informação (BM25) e RAG;
* Integração com APIs externas (LLM e reconhecimento de voz);
* Arquitetura de aplicações em camadas;
* Testes automatizados;
* Interface acessível e responsiva.

---
## Licença

Este projeto foi desenvolvido para fins acadêmicos e de extensão. As bibliotecas em `frontend/vendor/` mantêm as licenças originais (veja `frontend/vendor/README.md`). 
A BNCC e o Referencial Curricular de Rondônia são documentos oficiais de seus respectivos órgãos.

---