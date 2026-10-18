# Documentação técnica — ProfAssistenc IA

Referência do projeto. Para instalar e executar, veja o [Guia de instalação](INSTALACAO.md).

## Sumário

1. [Visão geral](#visão-geral)
2. [Arquitetura em camadas](#arquitetura-em-camadas)
3. [Fluxo de uma mensagem](#fluxo-de-uma-mensagem)
4. [RAG: consulta aos documentos oficiais](#rag-consulta-aos-documentos-oficiais)
5. [Integração com a Groq (modelo de texto)](#integração-com-a-groq-modelo-de-texto)
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

O sistema recebe o pedido do professor (digitado ou falado), consulta a **BNCC** e o **Referencial Curricular para o Ensino Médio de Rondônia (RCSEERO)**, pede ao **modelo de texto** (`openai/gpt-oss-20b`, via Groq) um plano fundamentado nesses trechos, **confere os códigos de habilidade** citados e grava a conversa em SQLite. O backend também serve o frontend, então uma única execução entrega tudo em `http://localhost:5000`.

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
│   ai_service                 │  chat, raciocínio e espaço da resposta
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
| `run.py`                         | Ponto de entrada: checa se já está aberto / porta ocupada, sobe o Uvicorn e abre o navegador. |
| `build_exe.py` · `construir_windows.bat` | Geram o executável e o `.zip` de distribuição (veja o [Guia de distribuição](DISTRIBUICAO.md)). |
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
| `app/routers/setup.py` · `app/envfile.py` | Configuração da chave pela interface e gravação segura do `.env`.                 |
| `app/launcher.py`                | Inicialização: detecta programa já aberto e porta ocupada, log em arquivo, pausa em erros. |
| `app/titles.py`                  | Título automático local das conversas.                                                    |

As rotas são funções síncronas (`def`): o FastAPI as executa em um pool de threads, então uma chamada demorada à IA não bloqueia as demais.

## Fluxo de uma mensagem

`POST /api/lessonplan`:

```text
1. Valida o corpo (mensagem vazia → 400).
2. Se veio conversation_id: busca a conversa DA INSTALAÇÃO (não achou → 404) e carrega o histórico.
3. RAG: lê ano/componente do pedido e busca os trechos nos documentos.
     Pedido curto ("e para o 6º ano?") herda o tema das perguntas anteriores.
4. Monta as mensagens: [sistema = regras + trechos] + [histórico recente] + [pedido].
5. Chama o modelo com o máximo de espaço de resposta que couber no limite por minuto. Falha → erro tratado (429/413/502) e NADA é gravado.
6. Confere os códigos de habilidade da resposta contra os dos documentos.
7. Acrescenta "Documentos consultados" (e alerta, se houver código inexistente).
8. Se a conversa é nova: gera o título localmente (instantâneo, sem chamar a IA).
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

### Liberdade para perguntar (modo livre) e tolerância a erros

* **Modo livre (padrão):** o prompt manda entender pedidos informais, incompletos ou com erros de digitação, **nunca responder "não entendi"**, assumir o que faltar (dizendo o que assumiu), usar os documentos como **referência** e, quando eles não cobrirem o pedido, responder mesmo assim com boas práticas e avisar que o alinhamento à BNCC deve ser conferido. **Nunca inventar códigos** continua valendo. O **modo rígido** (`RAG_STRICT=true`) restaura a regra de responder só com base nos documentos.
* **Erros de digitação na busca:** termos que não existem no índice são trocados pelo termo parecido mais frequente (`matematca → matemática`, `fotosintese → fotossíntese`, `escrta → escrita`, `istoria → história`), usando o vocabulário do próprio índice (`fts5vocab`, sem reconstruir a base). A leitura de componentes ("matematca", "ingles") também aceita erros. Se nada casar, há uma última tentativa por prefixo.
* **A busca nunca derruba a conversa:** qualquer falha ao consultar os documentos vira "sem contexto" e a resposta segue.
* **Campos `[entre colchetes]`** dos modelos de pedido avisam uma vez e **não bloqueiam**: enviar de novo manda assim mesmo.

### Barreiras contra erro

* **Conferência de códigos:** todo código citado na resposta é procurado na tabela `codes`. Os inexistentes geram, no fim da resposta, `⚠️ Confira: o código X não aparece nos documentos carregados — a IA pode tê-lo inventado.`
* **Documentos consultados:** a resposta termina com `Documentos consultados: BNCC (p. 295, 297) · RCSEERO (p. 275)`. Ela indica **o que foi entregue à IA**, não garante que a IA usou cada trecho.

Essas barreiras reduzem, **não eliminam**, o risco: a IA ainda pode errar a descrição de uma habilidade real ou escrever um plano pedagogicamente fraco. O professor precisa conferir.

## Integração com a Groq (modelo de texto)

* **Cliente:** `groq_client.py`, API compatível com a da OpenAI (`{GROQ_BASE_URL}/chat/completions`), `Authorization: Bearer`. A chave nunca vai na URL nem nos logs.
* **Modelo:** `openai/gpt-oss-20b` (padrão), configurável em `GROQ_MODEL`. É um modelo de **raciocínio**; qualquer outro modelo da Groq também funciona.
* **Repetição e limites:** erros 500/502/503/504 são repetidos até `GROQ_MAX_ATTEMPTS` vezes. No **429** o cliente respeita `Retry-After`: se a espera couber em `GROQ_MAX_RETRY_WAIT_SECONDS` (20 s), espera e tenta de novo; senão avisa o usuário (`Limite de uso da IA atingido. Tente novamente em N minutos.`). `401/403` → "chave recusada".

### Modelos de raciocínio (o que explica "respostas curtas", "título vazio" e "não respondeu")

Nos modelos de raciocínio (gpt-oss, qwen3), os tokens que o modelo "pensa" **contam dentro de `max_completion_tokens`**. Com um limite apertado, ele gasta tudo raciocinando e devolve **texto vazio**, e pedidos confusos fazem o modelo raciocinar mais. Antes dessa correção isso aparecia como: título que não era salvo (limite de 32 tokens), respostas cortadas cedo (1.500 tokens) e "não foi possível obter uma resposta" em perguntas com erro de digitação. O `ai_service.py` agora:

* usa `max_completion_tokens` folgado (teto `GROQ_MAX_TOKENS` = 4.096) e **esforço de raciocínio baixo** (`GROQ_REASONING_EFFORT=low`);
* envia só os parâmetros que o modelo aceita (`reasoning_params`). No **gpt-oss** usa `include_reasoning: false` + `reasoning_effort` e **nunca** `reasoning_format` (a documentação da Groq informa que ele não é suportado nesses modelos, e que os dois são mutuamente exclusivos); no **qwen3** usa `reasoning_format: hidden`; em modelos comuns não envia nada;
* se a resposta vier **vazia por falta de espaço** (`finish_reason=length`), refaz o pedido com mais espaço e, esgotadas as tentativas, devolve um erro claro ("A IA gastou o limite pensando…"), nunca uma resposta vazia;
* se a Groq recusar um parâmetro de raciocínio (400 citando `reasoning`), repete sem eles;
* se a Groq recusar por passar do limite por minuto (413 "Limit X, Requested Y"), reduz a resposta pelo excedente e tenta de novo;
* registra no log o uso real (entrada, saída e tokens de raciocínio).

### Orçamento de tokens (respostas maiores)

O limite por minuto soma entrada e saída (plano gratuito do `gpt-oss-20b`: **8.000**). A cada pedido, `lesson_plan_service.py`:

1. estima a entrada (≈ 3 caracteres por token, conservador para português);
2. decide quanto **histórico** reenviar: o que sobrar depois de reservar `GROQ_MIN_OUTPUT_TOKENS` (2.500) para a resposta, limitado por `HISTORY_MAX_CHARS` (7.000);
3. pede de saída **o máximo que couber**: `min(GROQ_MAX_TOKENS, GROQ_TPM_LIMIT − entrada − margem)`.

| Situação                                  | Espaço para a resposta (tokens, raciocínio incluído) |
| ----------------------------------------- | ---------------------------------------------------- |
| Primeiro pedido (sem histórico)           | até 4.096 (o teto)                                   |
| Conversa com histórico cheio              | ≈ 3.000                                              |
| Antes da correção                         | 1.500 fixos                                          |

`GROQ_TPM_LIMIT=0` desliga o cálculo e usa só `GROQ_MAX_TOKENS`. O histórico é cortado dos mais antigos para os mais recentes; a **última resposta é sempre mantida** (e, se ela foi cortada, mantém-se o **fim**, para o "Continuar" saber onde retomar).

**Resposta cortada → Continuar.** Se mesmo assim o modelo parar por tamanho, o backend acrescenta um aviso (`TRUNCATED_NOTE`); o frontend o troca pelo botão **Continuar a resposta**, que envia "Continue exatamente de onde parou…". O pedido de continuação herda o tema da pergunta anterior na busca nos documentos, e o aviso é retirado do histórico reenviado.

### Título da conversa

O título é gerado **localmente** (`app/titles.py`), sem chamar a IA: tipo do pedido (plano de aula, sequência didática, atividade…) + componente e ano lidos do texto + tema depois de "sobre". Ex.: `Plano de aula · Matemática · 5º ano · frações`. Isso é instantâneo, não gasta cota e funciona mesmo com erros de digitação. Com `TITLE_WITH_AI=true`, a IA é consultada primeiro, e o título local é o plano B. Ao iniciar, o servidor também dá título às conversas antigas que ficaram "Nova conversa".

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

### `GET /api/setup` e `POST /api/setup/key`: chave da IA pela interface

Substituem a edição manual do `.env`: é o que a janela **Chave da IA** usa.

* `GET /api/setup` → `{ "configured": true, "keyHint": "gsk_…abcd", "storedIn": "<caminho do .env>" }`. A chave completa **nunca** volta ao navegador.
* `POST /api/setup/key` com `{ "api_key": "gsk_…" }`: remove espaços/aspas, rejeita formato obviamente inválido (`400`), **testa a chave** na Groq (`GET /models`; `400` se recusada, `502` se não houve conexão, e `429` conta como válida), grava `GROQ_API_KEY` no `.env` (troca atômica, permissão `600`, preservando as demais linhas) e **aplica na hora**, sem reiniciar.
* **Proteção:** o pedido precisa do cabeçalho `X-ProfAssistenc: 1` e, se houver `Origin`, ele deve ser o do próprio servidor (`403` caso contrário). Um site qualquer aberto no navegador não consegue enviar o cabeçalho personalizado (exigiria CORS, que não é concedido) nem falsificar a origem. O servidor também escuta só em `127.0.0.1`.
* A chave não é registrada em log.

### `GET /api/health`

```json
{ "status": "ok", "aiConfigured": true, "version": "2.1.0", "model": "openai/gpt-oss-20b",
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
* **Logo e identidade:** a marca é uma folha de plano de aula com uma linha destacada a marca-texto (`assets/logo-mark.svg`, versão horizontal em `assets/logo.svg`, favicons `svg`/`png` e ícone de app), embutida no `index.html` como símbolo SVG.
* **Espaço:** a coluna da conversa usa até 1.180 px (padrão) ou 1.760 px (**Ampliar**), e o **menu lateral recolhe**; as duas escolhas ficam salvas. O texto corrido mantém uma largura confortável de leitura (~84 caracteres), enquanto **tabelas e código usam toda a largura**.
* **Tabelas:** colunas com largura mínima (~9,5 rem), palavras nunca quebradas no meio (a regra de quebra só atua em palavras maiores que a célula), linhas zebradas e rolagem horizontal dentro da folha quando há muitas colunas. Na impressão a tabela vira texto corrido a 10,5 pt.
* **Tela inicial:** dica "Do seu jeito", exemplos de **um clique** que já enviam, modelos de pedido e os 3 passos do funcionamento.
* **Segurança:** o HTML gerado a partir do Markdown passa por **DOMPurify** antes de entrar na página; texto digitado pelo usuário é inserido com `textContent`. Links abrem em nova aba com `rel="noopener noreferrer"`.
* **Matemática:** `$$…$$`, `\[…\]` e `\(…\)` são renderizados com KaTeX. O `$…$` simples fica **desligado** de propósito (senão "R$ 10 e R$ 20" viraria fórmula). A matemática é guardada antes do Markdown rodar, porque o Markdown "come" as barras de `\(`.
* **Modelos de pedido:** campos `[entre colchetes]` selecionados e percorridos com `Tab`; pedidos com campos sem preencher não são enviados.
* **Impressão:** o botão **Imprimir** de uma resposta imprime só aquele plano (cabeçalho com título e data, sem menus).
* **Acessibilidade:** `aria-label` nos controles de ícone, regiões `role="status"`/`alert`, foco visível, diálogos nativos, `prefers-reduced-motion`, link "ir para a mensagem".
* **Armazenamento local:** `profassistenc_installation_id` (mesma chave das versões anteriores), `profassistenc_theme`, `profassistenc_voice_mode`.
* **Compatibilidade:** `window.PROFASSISTENC_API_URL` continua definindo a base da API quando o front roda separado.

## Programa empacotado (.exe) e pasta de dados

O executável (PyInstaller, modo pasta) leva dentro o backend, a interface, os `assets` e a base `knowledge.sqlite`. Os dados do usuário ficam **ao lado do programa**: `.env`, `profassistenc.db` e `profassistenc.log`. Se a pasta do programa não for gravável, usa a pasta de dados do usuário (`%LOCALAPPDATA%\ProfAssistenc` no Windows). Quem decide é `config._app_dir()` (testado com a pasta simulada como protegida).

`run.py` e `launcher.py` cuidam da experiência de quem não é técnico: abrir de novo com o programa já aberto só reabre o navegador; porta ocupada por outro programa → mensagem em português; falha ao iniciar → o erro aparece e a janela espera Enter; e o log em arquivo (rotativo, 1 MB × 2) registra o funcionamento do programa (inicialização, avisos, erros e os endereços acessados), **nunca** o conteúdo das conversas nem a chave. A detecção de porta ocupada usa `SO_REUSEADDR` em Linux/macOS para não confundir uma porta recém-liberada (`TIME_WAIT`) com uma porta em uso, o que impediria reabrir o programa logo após fechá-lo.

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
| `GROQ_MODEL`                    | `openai/gpt-oss-20b`                    | Modelo de texto                                                      |
| `GROQ_WHISPER_MODEL`            | `whisper-large-v3-turbo`                | Modelo de voz                                                        |
| `GROQ_BASE_URL`                 | `https://api.groq.com/openai/v1`        | URL base (útil para o Groq simulado)                                 |
| `GROQ_MAX_TOKENS`               | `4096`                                  | Teto da resposta (inclui o raciocínio, nos modelos que raciocinam)   |
| `GROQ_REASONING_EFFORT`         | `low`                                   | Esforço de raciocínio (`low`/`medium`/`high`; qwen3 também `none`)   |
| `GROQ_TPM_LIMIT`                | `8000`                                  | Tokens por minuto do seu plano; usado para calcular o espaço da resposta (`0` desliga) |
| `GROQ_MIN_OUTPUT_TOKENS`        | `2500`                                  | Espaço reservado para a resposta ao decidir quanto histórico reenviar |
| `TEMPERATURE`                   | `0.5`                                   | Criatividade (menor = mais fiel ao contexto)                         |
| `GROQ_TIMEOUT_SECONDS`          | `90`                                    | Espera máxima por chamada                                            |
| `GROQ_MAX_ATTEMPTS`             | `3`                                     | Tentativas em erros temporários                                      |
| `GROQ_RETRY_DELAY_SECONDS`      | `1`                                     | Espera base entre tentativas                                         |
| `GROQ_MAX_RETRY_WAIT_SECONDS`   | `20`                                    | Maior espera aceita por limite de taxa antes de avisar o usuário     |
| `SYSTEM_PROMPT`                 | *(vazio = padrão de `prompts.py`)*      | Substitui as regras de sistema (o contexto continua sendo anexado)   |
| `RAG_STRICT`                    | `false`                                 | `true` = só responde com base nos documentos; `false` = modo livre   |
| `TITLE_WITH_AI`                 | `false`                                 | `true` = pede o título à IA (gasta cota); `false` = título local     |
| `HISTORY_MAX_CHARS`             | `7000`                                  | Máximo de histórico reenviado a cada pedido                          |
| `RAG_ENABLED`                   | `true`                                  | Liga/desliga a consulta aos documentos                               |
| `RAG_TOP_K`                     | `6`                                     | Máximo de trechos por pedido                                         |
| `RAG_MAX_CHARS`                 | `5000`                                  | Máximo de caracteres de trechos por pedido                           |
| `KNOWLEDGE_DB_PATH`             | `backend/data/knowledge.sqlite`         | Base de documentos                                                   |
| `TRANSCRIPTION_LANGUAGE`        | `pt`                                    | Idioma do Whisper                                                    |
| `MAX_AUDIO_MB`                  | `20`                                    | Tamanho máximo do áudio                                              |
| `HOST` / `PORT`                 | `127.0.0.1` / `5000`                    | Endereço de escuta                                                   |
| `OPEN_BROWSER`                  | `true`                                  | Abre o navegador ao iniciar com `run.py`                             |
| `ENABLE_DOCS`                   | `true`                                  | Swagger em `/docs`                                                   |
| `LOG_LEVEL`                     | `INFO`                                  | `DEBUG`, `INFO`, `WARNING`, `ERROR`                                  |
| `CORS_ORIGINS`                  | `http://127.0.0.1:5500,http://localhost:5500` | Origens permitidas (separadas por vírgula)                     |
| `DATABASE_PATH`                 | `backend/profassistenc.db`              | Banco de conversas                                                   |
| `ENV_PATH`                      | `.env` da pasta de dados                | Arquivo onde a janela **Chave da IA** grava a chave                  |
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

* **A chamada real à Groq não foi exercitada** nos testes automatizados (ambiente sem acesso à Groq). O formato segue a API compatível com a da OpenAI e a documentação oficial de raciocínio da Groq, mas valide com a sua chave. Nomes de modelos e limites mudam com o tempo: se um modelo for descontinuado, troque `GROQ_MODEL` e ajuste `GROQ_TPM_LIMIT`.
* **Plano gratuito:** 8 mil tokens/minuto (`gpt-oss-20b`) permitem ~1 plano longo por minuto; o sistema espera ou avisa, mas não elimina o limite.
* **Qualidade:** um modelo de 20B pode escrever descrições genéricas ou errar detalhes. As barreiras (contexto oficial, conferência de códigos) ajudam, mas o professor precisa conferir. Modelos maiores (`openai/gpt-oss-120b`) tendem a ser melhores, com limites diferentes.
* **Correção de digitação é aproximada:** troca por termos parecidos do índice e pode errar em palavras raras (ex.: um termo sem sentido pode virar outro termo real). O modo livre compensa, pois a IA recebe também o pedido original.
* **BM25 é lexical:** sinônimos e pedidos muito vagos recuperam pior. Informar ano, componente e tema melhora os resultados.
* **Cobertura:** Educação Infantil e Fundamental só têm a BNCC; o RCSEERO é só Ensino Médio.
* **Sem modelo oficial de plano de aula** nos documentos (veja acima).
* **Extração dos PDFs:** tabelas muito irregulares podem ter células fora de ordem; o texto continua contíguo por célula.
* **Leitura em voz alta** depende das vozes do sistema; a gravação exige `localhost` ou HTTPS.
* **Tabelas com muitas colunas** (mais de ~5 em tela comum) rolam na horizontal dentro da folha; use **Ampliar** e recolha o menu para ganhar espaço.

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

**v2.1 (esta versão):**

| Item                         | Antes                                                         | Agora                                                                 |
| ---------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------- |
| Modelo padrão                | `llama-3.1-8b-instant`                                        | `openai/gpt-oss-20b` (modelo de raciocínio)                           |
| Parâmetro de limite          | `max_tokens` fixo em 1.500                                    | `max_completion_tokens` calculado (até 4.096), com repetição se vier vazio |
| Parâmetros de raciocínio     | `reasoning_format: hidden` (inválido no gpt-oss)              | `include_reasoning: false` + `reasoning_effort` só em modelos que aceitam |
| Título automático            | 2ª chamada à IA com limite de 32 tokens (falhava em silêncio) | Local e instantâneo; IA opcional; conversas antigas são corrigidas ao iniciar |
| Perguntas com erros          | Prompt rígido + busca exata                                   | Prompt livre, correção de digitação na busca e no reconhecimento de componentes |
| Respostas cortadas           | Aviso em texto                                                | Botão **Continuar a resposta**; o histórico preserva o fim da resposta cortada |
| Largura / tabelas            | Coluna de 780 px; palavras quebradas no meio                  | 1.180 px (ou 1.760 px), menu recolhível, tabelas com colunas legíveis |
| Identidade visual            | Favicon provisório                                            | Logo própria (marca + versão horizontal) e favicons                   |
| Chave da IA                  | Editar o `.env` à mão                                         | Janela na interface: testa a chave, grava e aplica na hora            |
| Distribuição                 | Comandos do PyInstaller escritos à mão                        | `build_exe.py`, `construir_windows.bat`, instalador Inno Setup, pacote `.zip` com SHA-256 |
| Reabrir o programa           | Erro de porta ocupada                                         | Reabre o navegador; mensagem clara se a porta for de outro programa   |
