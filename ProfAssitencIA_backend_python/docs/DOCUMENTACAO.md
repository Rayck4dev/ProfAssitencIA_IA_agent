# Documentação técnica — ProfAssistenc IA

Referência do projeto. Para instalar e executar, veja o [Guia de instalação](INSTALACAO.md).

## Sumário

1. [Visão geral](#visão-geral)
2. [Arquitetura em camadas](#arquitetura-em-camadas)
3. [Fluxo de uma mensagem](#fluxo-de-uma-mensagem)
4. [RAG: consulta aos documentos oficiais](#rag-consulta-aos-documentos-oficiais)
5. [Integração com a Groq (Llama)](#integração-com-a-groq-llama)
6. [Voz (Whisper e leitura em voz alta)](#voz-whisper-e-leitura-em-voz-alta)
7. [Referência da API](#referência-da-api)
8. [Frontend](#frontend)
9. [Banco de dados](#banco-de-dados)
10. [Configurações](#configurações)
11. [Tratamento de erros](#tratamento-de-erros)
12. [Segurança e privacidade](#segurança-e-privacidade)
13. [Testes](#testes)
14. [Limitações conhecidas](#limitações-conhecidas)
15. [Como estender](#como-estender)
16. [Diferenças em relação às versões anteriores](#diferenças-em-relação-às-versões-anteriores)

---

## Visão geral

O sistema recebe o pedido do professor (digitado ou falado), consulta a **BNCC** e o **Referencial Curricular para o Ensino Médio de Rondônia (RCSEERO)**, pede ao **Llama** (via Groq) um plano fundamentado nesses trechos, **confere os códigos de habilidade** citados e grava a conversa em SQLite. O backend também serve o frontend, então uma única execução entrega tudo em `http://localhost:5000`.

Não há autenticação de usuários: cada navegador gera um `installation_id` (no `localStorage`) e as consultas são filtradas por ele.

## Arquitetura em camadas

```text
 HTTP
  │
  ▼
┌──────────────────────────────┐
│ routers/                     │  Recebem, validam e respondem. Sem regra de negócio.
│   lesson_plan · conversations│
│   transcribe                 │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ services/                    │
│   lesson_plan_service        │  RAG + histórico + prompt + conferência de códigos
│   ai_service                 │  chat e títulos (Llama)
│   transcription_service      │  voz → texto (Whisper)
│   groq_client                │  HTTP, repetição, limite de taxa, erros
│   conversation_service       │  SQLAlchemy
└───────┬──────────────┬───────┘
        ▼              ▼
   rag/ (FTS5)      SQLAlchemy
   knowledge.sqlite  profassistenc.db
```

| Arquivo                          | Responsabilidade                                                                          |
| -------------------------------- | ----------------------------------------------------------------------------------------- |
| `run.py`                         | Sobe o Uvicorn e abre o navegador quando o servidor está pronto.                          |
| `app/main.py`                    | `create_app()`: CORS, erros, rotas, arquivos estáticos.                                   |
| `app/config.py`                  | `Settings` (`.env`/ambiente) e resolução de caminhos (desenvolvimento × executável).      |
| `app/prompts.py`                 | Instruções de sistema (com e sem RAG).                                                    |
| `app/rag/text.py`                | Normalização, stemmer leve de português, stopwords, regex e decodificação de códigos.     |
| `app/rag/intent.py`              | Lê ano, etapa e componente da pergunta e os converte em prefixos de código.               |
| `app/rag/store.py`               | `KnowledgeBase`: busca BM25, fusão de rankings, orçamento de contexto, códigos conhecidos.|
| `app/rag/ingest.py`              | Gera `knowledge.sqlite` a partir dos PDFs (único ponto que usa PyMuPDF).                  |
| `app/models.py` · `database.py`  | Entidades e conexão do SQLite de conversas.                                               |
| `app/schemas.py`                 | Modelos Pydantic de entrada e saída.                                                      |
| `app/dependencies.py`            | Injeção de dependências (`Depends`).                                                      |

As rotas são funções síncronas (`def`): o FastAPI as executa em um pool de threads, então uma chamada demorada à IA não bloqueia as demais.

## Fluxo de uma mensagem

`POST /api/lessonplan`:

```text
1. Valida o corpo (mensagem vazia → 400).
2. Se veio conversation_id: busca a conversa DA INSTALAÇÃO (não achou → 404) e carrega o histórico.
3. RAG: lê ano/componente do pedido e busca os trechos nos documentos.
     Pedido curto ("e para o 6º ano?") herda o tema das perguntas anteriores.
4. Monta as mensagens: [sistema = regras + trechos] + [histórico recente] + [pedido].
5. Chama o Llama. Falha → erro tratado (429/413/502) e NADA é gravado.
6. Confere os códigos de habilidade da resposta contra os dos documentos.
7. Acrescenta "Documentos consultados" (e alerta, se houver código inexistente).
8. Se a conversa é nova: pede um título curto à IA (se falhar, "Nova conversa").
9. Grava, numa única transação: conversa (se nova), pergunta e resposta.
10. Responde { "response": "...", "conversationId": "<id>" }.
```

O histórico enviado à IA vem **sempre do banco** (o campo `messages` enviado por clientes antigos é ignorado) e **sem** a linha "Documentos consultados" das respostas anteriores.

## RAG: consulta aos documentos oficiais

### Por que busca lexical (BM25) e não embeddings

* Os documentos são cheios de **códigos exatos** (`EF05MA03`, `EM13MAT102`) e termos técnicos, onde busca lexical é forte.
* Roda **offline**, em um único arquivo SQLite, sem PyTorch e sem baixar modelos (o computador do professor pode ser modesto).
* A Groq não oferece embeddings; usar outro serviço consumiria o mesmo limite de tokens.

Contrapartida: BM25 não entende **sinônimos** ("repartir" ≠ "dividir"). Isso é compensado, em parte, pelo stemmer e pela leitura de ano/componente (abaixo).

### Os documentos

| Documento | Páginas | Cobre                                      | Observações                                                                            |
| --------- | ------- | ------------------------------------------ | -------------------------------------------------------------------------------------- |
| BNCC      | 600     | Educação Infantil, Ensino Fundamental e **Ensino Médio** | O arquivo `BNCC_EI_EF_…` traz também o Ensino Médio (competências e habilidades `EM13…`). |
| RCSEERO   | 860     | **Ensino Médio** de Rondônia               | Quadros organizadores com habilidades, objetos de conhecimento e objetivos; seção "Projeto de Vida". |

Índice gerado: **4.342 trechos** e **1.664 códigos de habilidade distintos**, em ~5,5 MB. Não há referencial estadual de Rondônia para Educação Infantil/Fundamental nos documentos carregados.

### Ingestão (`python -m app.rag.ingest`)

1. **Leitura** com PyMuPDF por *blocos* de texto (cada célula de tabela é um bloco). O PyMuPDF também repara PDFs com estrutura danificada.
2. **Linhas de tabela:** blocos com intervalos verticais sobrepostos formam uma "faixa" (uma linha da tabela) e são ordenados por coluna. Assim a habilidade fica junto dos seus objetos de conhecimento, em vez de espalhada.
3. **Limpeza:** remove o número da página (cabeçalho/rodapé), junta hifenização, descarta **páginas de sumário** (linhas pontilhadas), que só poluem a busca.
4. **Trechos** de ~900 caracteres, sem cruzar páginas, quebrando por frase quando um bloco é grande.
5. **Metadados:** número **impresso** da página (a BNCC e o RCSEERO têm deslocamentos de 2 e 1 em relação ao PDF; é o número impresso que o professor encontra no livro), caminho de seção a partir do *outline* do PDF (RCSEERO), e decodificação de cada código (ex.: `EF05MA03` → "Ensino Fundamental · 5º ano · Matemática"), que também é indexada.
6. **Índice FTS5** (`unicode61`, sem acentos) sobre o texto já normalizado e com stemming, mais a tabela `codes` com todos os códigos existentes.

### Busca (`KnowledgeBase.search`)

1. **Intenção** (`intent.py`): reconhece "5º ano", "quinto ano", "2ª série", "ensino médio", "educação infantil", "crianças pequenas" e o componente (matemática, português, ciências, história…). O resultado vira **prefixos de código**: "5º ano de matemática" → `ef05ma`, `ef15ma`, `ef35ma` (códigos de ano único e de blocos de anos). Um BM25 puro nunca faria essa ligação, porque o texto do pedido não contém "EF05MA".
2. **Duas consultas** com BM25: uma **restrita** (`(tema) AND (prefixos)`, peso 1,0) e uma **só por tema** (peso 0,6), combinadas por **fusão de rankings recíprocos** (RRF, k = 60). A restrita só é usada quando há ano ou componente; para temas narrativos ("projeto de vida") ela não filtra, porque esses trechos não têm código.
3. **Orçamento:** no máximo `RAG_TOP_K` trechos e `RAG_MAX_CHARS` caracteres.
4. **Saudações e agradecimentos** ("obrigado!") não recuperam nada: as stopwords os removem e o sistema não faz busca sem termos.
5. **Perguntas curtas** (menos de 3 termos úteis) herdam o tema das duas últimas perguntas do professor. O ano/etapa citado na mensagem atual prevalece.

### Como a IA é instruída (`app/prompts.py`)

O prompt de sistema manda: seguir os documentos; usar **somente** habilidades e códigos que estejam no contexto, copiados como estão; **nunca inventar códigos**; avisar quando o contexto não cobre o pedido e pedir ano/componente; no Ensino Médio priorizar o RCSEERO; e entregar o plano com as seções *Identificação, Habilidades, Objetos de conhecimento, Objetivos de aprendizagem, Desenvolvimento, Recursos, Avaliação, Adaptações*. Depois vêm os documentos disponíveis e os trechos recuperados, com fonte e página.

> **Importante:** os PDFs carregados **não trazem um modelo oficial de plano de aula** (não há ocorrência de "plano de aula" neles). As seções acima são uma estrutura razoável a partir dos conceitos dos documentos (habilidades, objetos de conhecimento, objetivos, metodologias ativas, avaliação formativa). Se a SEDUC-RO ou a escola exigir um modelo próprio, ajuste `DEFAULT_SYSTEM_PROMPT` (ou defina `SYSTEM_PROMPT` no `.env`).

### Barreiras contra erro

* **Conferência de códigos:** todo código citado na resposta é procurado na tabela `codes`. Os inexistentes geram, no fim da resposta, `⚠️ Confira: o código X não aparece nos documentos carregados — a IA pode tê-lo inventado.`
* **Documentos consultados:** a resposta termina com `Documentos consultados: BNCC (p. 295, 297) · RCSEERO (p. 275)`. Ela indica **o que foi entregue à IA**, não garante que a IA usou cada trecho.

Essas barreiras reduzem, **não eliminam**, o risco: a IA ainda pode errar a descrição de uma habilidade real ou escrever um plano pedagogicamente fraco. O professor precisa conferir.

## Integração com a Groq (Llama)

* **Cliente:** `groq_client.py`, API compatível com a da OpenAI (`{GROQ_BASE_URL}/chat/completions`), autenticação `Authorization: Bearer`. A chave nunca vai na URL nem nos logs.
* **Modelo:** `llama-3.1-8b-instant` (padrão, o mais leve), configurável em `GROQ_MODEL`.
* **Repetição e limites:** erros 500/502/503/504 são repetidos até `GROQ_MAX_ATTEMPTS` vezes com espera crescente. No **429** (limite de taxa) o cliente respeita o cabeçalho `Retry-After`: se a espera couber em `GROQ_MAX_RETRY_WAIT_SECONDS` (20 s), espera e tenta de novo; senão devolve ao usuário `Limite de uso da IA atingido. Tente novamente em N minutos.` (HTTP 429). `401/403` → "chave recusada"; `413` → "conversa grande demais".
* **Resposta cortada:** se o modelo parar por `max_tokens` (`finish_reason = length`), a resposta recebe o aviso "foi cortada pelo limite de tamanho. Peça para continuar."
* **Título:** um segundo pedido curto (≤ 32 tokens, sem o prompt de sistema); a resposta é limpa (primeira linha, sem aspas, ≤ 80 caracteres). Falha → "Nova conversa".

### Orçamento de tokens

O plano gratuito do modelo 8B limita **6.000 tokens por minuto somando entrada e saída**. Estimativa por pedido (≈ 3,3 caracteres por token; valores conferidos com a base real em pedidos típicos de plano de aula):

| Parte                                   | Limite padrão                      | ≈ tokens   |
| --------------------------------------- | ---------------------------------- | ---------- |
| Regras do prompt de sistema (+ lista de documentos) | ~1.400 (+ ~250) caracteres | ~500   |
| Trechos dos documentos                  | `RAG_MAX_CHARS` = 4.500            | até 1.400  |
| Histórico                               | `HISTORY_MAX_CHARS` = 4.500        | até 1.400  |
| Pedido                                  | —                                  | ~100       |
| Resposta                                | `GROQ_MAX_TOKENS` = 1.500          | até 1.500  |
| **Total**                               |                                    | **≈ 3,5 mil (1º pedido) a 4,9 mil (histórico cheio)** |

O histórico é cortado dos mais antigos para os mais recentes; a **última resposta é sempre mantida** (truncada pelo início se for enorme), porque pedidos como "deixe mais curto" dependem dela. Cada pedido registra no log o tamanho estimado da entrada.

## Voz (Whisper e leitura em voz alta)

**Entrada (voz → texto):** o navegador grava com `MediaRecorder` (webm/opus no Chrome/Edge/Firefox-ogg, mp4 no Safari), envia para `POST /api/transcribe`, e o backend repassa ao Whisper da Groq (`whisper-large-v3-turbo`, idioma `pt`, temperatura 0, `verbose_json`).

* **Filtro de silêncio:** segmentos com `no_speech_prob > 0,6` **e** `avg_logprob < -1,0` (critério do próprio Whisper) são descartados. Isso evita que gravações mudas virem frases inventadas como "Obrigado por assistir!". Se tudo for descartado, o texto vem vazio e a interface avisa.
* **Limites:** áudio com menos de ~1 KB é rejeitado (gravação vazia); máximo `MAX_AUDIO_MB` (20 MB; o limite da Groq no plano gratuito é 25 MB). A interface para sozinha aos 5 minutos.

**Saída (texto → voz):** feita no **navegador** com `speechSynthesis` (sem custo e sem enviar a resposta a nenhum serviço). O texto é limpo de Markdown e da linha de documentos consultados, e dividido em frases para evitar o corte de falas longas do Chrome. A qualidade depende das vozes instaladas no sistema.

## Referência da API

Swagger interativo em `http://localhost:5000/docs`. Requisições em `snake_case`, respostas em `camelCase`. Rotas `/api/...` **não diferenciam maiúsculas** (`/api/LessonPlan` = `/api/lessonplan`). Datas em UTC com sufixo `Z`.

### `POST /api/lessonplan`

| Campo             | Tipo              | Obrigatório | Descrição                                                    |
| ----------------- | ----------------- | ----------- | ------------------------------------------------------------ |
| `installation_id` | string            | sim         | Identificador da instalação (gerado pelo frontend)           |
| `message`         | string            | sim         | Pedido do professor (não pode ser vazio)                     |
| `conversation_id` | string \| inteiro | não         | Omitir ou `null` inicia uma nova conversa                    |

```json
{ "response": "## Identificação\n...\n\n---\n**Documentos consultados:** BNCC (p. 295, 297)", "conversationId": "1" }
```

A resposta pode terminar com a linha `---` + `**Documentos consultados:** …` e, se houver, um bloco `> ⚠️ **Confira:** …`. O frontend separa e estiliza essas partes.

Erros: `400` mensagem vazia / `conversation_id` inválido · `404` conversa inexistente (ou de outra instalação) · `413` conversa grande demais · `429` limite de uso da IA · `502` falha da IA.

### `POST /api/transcribe`

`multipart/form-data` com o campo `audio` (webm, ogg, mp4/m4a, mp3, wav ou flac). Resposta: `{ "text": "…" }` (vazio se só houve silêncio).
Erros: `400` áudio vazio/curto · `413` áudio grande · `415` formato não suportado · `429` · `502`.

### `GET /api/conversations?installation_id=…`

Da **mais recente para a mais antiga**: `{ "conversations": [{ "id", "title", "installationId", "updatedAt" }] }`.

### `GET /api/conversations/{id}?installation_id=…`

A conversa com `messages` em ordem cronológica (`id`, `conversationId`, `role`, `content`). `404` se não existir.

### `PATCH /api/conversations/{id}`

`{ "installation_id": "…", "title": "…" }` (título até 200 caracteres, sem espaços nas pontas). `400` título vazio · `404`.

### `DELETE /api/conversations/{id}?installation_id=…`

Apaga a conversa e suas mensagens. Devolve a conversa excluída. `404`.

### `GET /api/health`

```json
{ "status": "ok", "aiConfigured": true, "version": "2.0.0", "model": "llama-3.1-8b-instant",
  "knowledgeBase": { "available": true, "documents": 2, "chunks": 4342, "names": ["BNCC", "RCSEERO"] } }
```

`aiConfigured` indica apenas que há uma chave, não que ela é válida.

## Frontend

Sem frameworks e **sem CDN**: tudo que a interface precisa está em `frontend/` (bibliotecas em `frontend/vendor/`, ícones em um sprite SVG dentro do `index.html`). A única chamada externa é a do backend à Groq.

| Arquivo                | Papel                                                                                         |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| `index.html`           | Estrutura, diálogos nativos (`<dialog>`) e sprite de ícones                                   |
| `css/style.css`        | Tema claro/escuro por variáveis, tipografia do documento, impressão, responsivo               |
| `js/app.js`            | Estado, API, Markdown seguro, voz, histórico                                                  |
| `vendor/`              | marked, DOMPurify, KaTeX (só `woff2`); licenças em `vendor/README.md`                         |

Pontos de projeto:

* **Visual:** "caderno de planejamento": papel quente, tinta azul-marinho, verde como único acento, amarelo só como marca-texto, serifa nos documentos, sem gradientes/brilho/blur. A resposta aparece como uma **folha de documento** (títulos de seção em versalete, tabelas, fórmulas).
* **Segurança:** o HTML gerado a partir do Markdown passa por **DOMPurify** antes de entrar na página; texto digitado pelo usuário é inserido com `textContent`. Links abrem em nova aba com `rel="noopener noreferrer"`.
* **Matemática:** `$$…$$`, `\[…\]` e `\(…\)` são renderizados com KaTeX. O `$…$` simples fica **desligado** de propósito (senão "R$ 10 e R$ 20" viraria fórmula). A matemática é guardada antes do Markdown rodar, porque o Markdown "come" as barras de `\(`.
* **Modelos de pedido:** campos `[entre colchetes]` selecionados e percorridos com `Tab`; pedidos com campos sem preencher não são enviados.
* **Impressão:** o botão **Imprimir** de uma resposta imprime só aquele plano (cabeçalho com título e data, sem menus).
* **Acessibilidade:** `aria-label` nos controles de ícone, regiões `role="status"`/`alert`, foco visível, diálogos nativos, `prefers-reduced-motion`, link "ir para a mensagem".
* **Armazenamento local:** `profassistenc_installation_id` (mesma chave das versões anteriores), `profassistenc_theme`, `profassistenc_voice_mode`.
* **Compatibilidade:** `window.PROFASSISTENC_API_URL` continua definindo a base da API quando o front roda separado.

## Banco de dados

**Conversas:** SQLite `backend/profassistenc.db` (ao lado do executável quando empacotado), tabelas criadas automaticamente. **Esquema inalterado desde a versão em C#** (por isso bancos antigos continuam funcionando).

`Conversations` — `Id` (PK), `Title`, `InstallationId`, `UpdatedAt` (UTC).
`MessageEntities` — `Id` (PK), `ConversationId` (FK, `ON DELETE CASCADE`, indexada), `Role` (`user`/`assistant`), `Content`.

O backend ativa `PRAGMA foreign_keys=ON` para a exclusão em cascata funcionar. Como o projeto usa `create_all`, que só cria tabelas ausentes, uma mudança futura de esquema exigiria adotar o [Alembic](https://alembic.sqlalchemy.org/).

**Documentos:** `backend/data/knowledge.sqlite`, aberto **somente leitura**. Tabelas `docs`, `chunks` (texto original, página, seção), `chunks_fts` (índice FTS5 sem conteúdo duplicado), `codes` e `meta`. É um arquivo versionado junto com o código e regenerável com `python -m app.rag.ingest`.

## Configurações

Lidas de variáveis de ambiente ou do `.env` (em `backend/`, ou ao lado do executável); o ambiente tem prioridade. Modelo em [`backend/.env.example`](../backend/.env.example).

| Variável                        | Padrão                                  | Descrição                                                            |
| ------------------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| `GROQ_API_KEY`                  | *(vazio — obrigatório)*                 | Chave da Groq                                                        |
| `GROQ_MODEL`                    | `llama-3.1-8b-instant`                  | Modelo de texto                                                      |
| `GROQ_WHISPER_MODEL`            | `whisper-large-v3-turbo`                | Modelo de voz                                                        |
| `GROQ_BASE_URL`                 | `https://api.groq.com/openai/v1`        | URL base (útil para o Groq simulado)                                 |
| `GROQ_MAX_TOKENS`               | `1500`                                  | Tamanho máximo da resposta                                           |
| `TEMPERATURE`                   | `0.4`                                   | Criatividade (menor = mais fiel ao contexto)                         |
| `GROQ_TIMEOUT_SECONDS`          | `60`                                    | Espera máxima por chamada                                            |
| `GROQ_MAX_ATTEMPTS`             | `3`                                     | Tentativas em erros temporários                                      |
| `GROQ_RETRY_DELAY_SECONDS`      | `1`                                     | Espera base entre tentativas                                         |
| `GROQ_MAX_RETRY_WAIT_SECONDS`   | `20`                                    | Maior espera aceita por limite de taxa antes de avisar o usuário     |
| `SYSTEM_PROMPT`                 | *(vazio = padrão de `prompts.py`)*      | Substitui as regras de sistema (o contexto continua sendo anexado)   |
| `HISTORY_MAX_CHARS`             | `4500`                                  | Histórico reenviado a cada pedido                                    |
| `RAG_ENABLED`                   | `true`                                  | Liga/desliga a consulta aos documentos                               |
| `RAG_TOP_K`                     | `6`                                     | Máximo de trechos por pedido                                         |
| `RAG_MAX_CHARS`                 | `4500`                                  | Máximo de caracteres de trechos por pedido                           |
| `KNOWLEDGE_DB_PATH`             | `backend/data/knowledge.sqlite`         | Base de documentos                                                   |
| `TRANSCRIPTION_LANGUAGE`        | `pt`                                    | Idioma do Whisper                                                    |
| `MAX_AUDIO_MB`                  | `20`                                    | Tamanho máximo do áudio                                              |
| `HOST` / `PORT`                 | `127.0.0.1` / `5000`                    | Endereço de escuta                                                   |
| `OPEN_BROWSER`                  | `true`                                  | Abre o navegador ao iniciar com `run.py`                             |
| `ENABLE_DOCS`                   | `true`                                  | Swagger em `/docs`                                                   |
| `LOG_LEVEL`                     | `INFO`                                  | `DEBUG`, `INFO`, `WARNING`, `ERROR`                                  |
| `CORS_ORIGINS`                  | `http://127.0.0.1:5500,http://localhost:5500` | Origens permitidas (separadas por vírgula)                     |
| `DATABASE_PATH`                 | `backend/profassistenc.db`              | Banco de conversas                                                   |
| `FRONTEND_DIR` / `ASSETS_DIR`   | `frontend/` e `assets/` do repositório  | Pastas estáticas                                                     |

## Tratamento de erros

Erros voltam em **texto puro** (o frontend exibe o corpo da resposta).

| Código | Quando                                                              | Corpo                                                    |
| ------ | ------------------------------------------------------------------- | -------------------------------------------------------- |
| `400`  | Mensagem vazia; `conversation_id` não numérico; título vazio; campo ausente | `Mensagem vazia` · `Erro de conversao` · `Titulo vazio` · `Requisição inválida (campo): …` |
| `404`  | Conversa inexistente ou de outra instalação                         | `Conversa nao encontrada`                                |
| `413`  | Contexto grande demais para o modelo / áudio grande demais          | texto explicativo                                        |
| `415`  | Formato de áudio não suportado                                      | `Formato de áudio não suportado: …`                      |
| `429`  | Limite de uso da Groq                                               | `Limite de uso da IA atingido. Tente novamente em N …`   |
| `502`  | Falha da IA (chave ausente/recusada, rede, erro do modelo)          | `Não foi possível obter uma resposta da IA.` (ou, para chave, texto específico) |

A causa detalhada vai para o log do servidor.

## Segurança e privacidade

* A chave da Groq fica só no `.env`/ambiente, vai em cabeçalho e **nunca é registrada**. O `.env` está no `.gitignore`.
* O log **não registra o conteúdo das conversas**, só contagens e erros.
* **O texto das conversas e o áudio são enviados à Groq** (serviço de terceiros) para gerar a resposta e a transcrição. **Não inclua dados pessoais de estudantes** (nomes, laudos, etc.) nos pedidos. A leitura em voz alta é local, no navegador.
* O servidor escuta apenas em `127.0.0.1` por padrão. Ao usar `HOST=0.0.0.0`, qualquer pessoa da rede acessa a aplicação **e gasta sua cota da Groq** (não há autenticação).
* O `installation_id` isola conversas entre navegadores, mas **não é uma credencial**. Adequado para uso local.
* Respostas passam por DOMPurify antes de serem exibidas.

## Testes

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest
```

A suíte roda sem internet e sem chave, com banco temporário e Groq simulado (`httpx.MockTransport`). Cobre:

* **API:** conversa nova e continuação, histórico enviado e limite de tamanho, isolamento entre instalações, validações, renomear/excluir, ordenação, CORS, rotas sem diferenciação de maiúsculas e **compatibilidade com um banco criado pela versão em C#**;
* **Groq:** cabeçalho de autenticação, repetição em 5xx, espera e aviso em 429, chave recusada, 413, erro de rede, chave ausente, resposta cortada, títulos;
* **RAG:** stemmer, decodificação de códigos, leitura de ano/componente, reconstrução de linhas de tabela, descarte de sumário, busca por habilidade e por tema, orçamento de caracteres, conferência de códigos, perguntas curtas que herdam tema, saudações sem busca;
* **Voz:** formatos aceitos, idioma e modelo enviados, filtro de silêncio, validações e falhas;
* **Base real** (se `data/knowledge.sqlite` existir): perguntas típicas recuperam as habilidades certas (`EF05MA03`, `EF08HI…`, `EF07LI…`, `EM13MAT…`) e "projeto de vida" vem do RCSEERO.

Além dos testes automatizados, a interface foi exercitada de ponta a ponta em um navegador Chromium headless contra o backend real e um Groq simulado: modelos e `Tab`, envio, fórmula/tabela/alerta, tema escuro, gravação com microfone falso, modo voz, cancelamento, erro 429, renomear/excluir, recarga, impressão e celular.

## Limitações conhecidas

* **A chamada real ao Llama/Whisper da Groq não foi exercitada** nos testes (ambiente sem acesso à Groq). O formato segue a API compatível com a da OpenAI; valide com a sua chave antes de usar. O nome do modelo pode mudar com o tempo (se a Groq descontinuar um modelo, troque `GROQ_MODEL`).
* **Qualidade do modelo leve:** o Llama 8B segue instruções e escreve em português pior do que modelos maiores. As barreiras (contexto oficial, conferência de códigos) ajudam, mas planos podem ficar genéricos ou errar descrições. Para melhorar, teste `llama-3.3-70b-versatile`.
* **Plano gratuito:** o limite de 6 mil tokens/minuto restringe o tamanho do contexto e a frequência (veja o [guia](INSTALACAO.md#8-limites-do-plano-gratuito)).
* **BM25 é lexical:** sinônimos e perguntas muito vagas ("uma aula legal de ciências") recuperam pior. Informar ano, componente e tema melhora muito os resultados.
* **Cobertura:** Educação Infantil e Fundamental só têm a BNCC; o RCSEERO é só Ensino Médio. A IA é instruída a dizer quando o contexto não cobre o pedido.
* **Sem modelo oficial de plano de aula** nos documentos (veja acima).
* **Extração dos PDFs:** tabelas muito irregulares podem ter células fora de ordem; o texto continua contíguo por célula.
* **Leitura em voz alta** depende das vozes do sistema; a gravação exige `localhost` ou HTTPS.

## Como estender

* **Novos documentos** (ex.: referencial estadual de EI/EF): coloque os PDFs em `backend/knowledge/` e rode `python -m app.rag.ingest knowledge/` (veja o [guia](INSTALACAO.md#11-atualizar-ou-trocar-os-documentos-rag)). Para nome/título/etapas corretos, inclua o arquivo em `KNOWN_DOCS`.
* **Mudar a estrutura do plano ou o tom:** edite `DEFAULT_SYSTEM_PROMPT` em `app/prompts.py` (ou use `SYSTEM_PROMPT`).
* **Outro modelo:** `GROQ_MODEL`. **Outro provedor compatível com a API da OpenAI:** `GROQ_BASE_URL` + chave (o nome das variáveis é histórico).
* **Novos componentes na leitura de intenção:** `app/rag/intent.py` (tabelas `_EF_KEYWORDS`, `_EM_KEYWORDS`).
* **Novo endpoint:** crie um arquivo em `app/routers/`, registre em `app/main.py` e ponha a regra em um serviço.
* **Embeddings no futuro:** `KnowledgeBase.search` é o único ponto a trocar; a fusão por RRF já suporta combinar a busca lexical com uma vetorial.

## Diferenças em relação às versões anteriores

**C# → Python (v2.0):** mesma API e mesmo banco; `Controllers/`→`routers/`, `Services/`→`services/`, EF Core→SQLAlchemy, `appsettings.Local.json`→`.env`, `dotnet publish`→PyInstaller. Também: lista de conversas da mais recente para a mais antiga; datas com `Z`; gravação em transação única; logs sem o conteúdo das conversas.

**Gemini → Groq (Llama + Whisper):**

| Item                    | Gemini                                  | Groq                                                          |
| ----------------------- | --------------------------------------- | ------------------------------------------------------------- |
| Autenticação            | `x-goog-api-key`                        | `Authorization: Bearer`                                       |
| Formato                 | `contents` / `parts`, papel `model`     | `messages`, papéis `system`/`user`/`assistant`                |
| Instrução de sistema    | opcional (`systemInstruction`)          | sempre enviada (regras + trechos dos documentos)              |
| Limite de taxa (429)    | tratado como falha genérica             | espera `Retry-After` curto ou avisa o usuário                 |
| Variáveis               | `GEMINI_*`                              | `GROQ_*` (as antigas deixam de ter efeito)                    |

**Novidades desta versão:** RAG na BNCC e no RCSEERO; conferência de códigos; voz (Whisper e leitura); `POST /api/transcribe`; `/api/health` com modelo e base de documentos; respostas com a linha "Documentos consultados"; frontend refeito, sem CDN; `tools/fake_groq.py`.
