# Guia de instalação — ProfAssistenc IA

Este guia leva você do zero até a aplicação rodando no navegador, com IA, voz e consulta aos documentos oficiais. Os comandos aparecem para **Windows (PowerShell)** e **Linux/macOS**.

## Sumário

1. [Pré-requisitos](#1-pré-requisitos)
2. [Baixar o projeto](#2-baixar-o-projeto)
3. [Ambiente virtual e dependências](#3-ambiente-virtual-e-dependências)
4. [Chave da Groq e arquivo `.env`](#4-chave-da-groq-e-arquivo-env)
5. [Executar](#5-executar)
6. [Verificar se está tudo certo](#6-verificar-se-está-tudo-certo)
7. [Usar a voz](#7-usar-a-voz)
8. [Limites do plano gratuito](#8-limites-do-plano-gratuito)
9. [Rodar os testes](#9-rodar-os-testes)
10. [Modo desenvolvimento e Groq simulado](#10-modo-desenvolvimento-e-groq-simulado)
11. [Atualizar ou trocar os documentos (RAG)](#11-atualizar-ou-trocar-os-documentos-rag)
12. [Gerar um executável](#12-gerar-um-executável)
13. [Migrando de versões anteriores](#13-migrando-de-versões-anteriores)
14. [Solução de problemas](#14-solução-de-problemas)

---

## 1. Pré-requisitos

| Item                 | Observação                                                                              |
| -------------------- | --------------------------------------------------------------------------------------- |
| **Python 3.11+**     | Testado com 3.12                                                                        |
| **Git**              | Opcional (dá para baixar o ZIP)                                                         |
| **Chave da Groq**    | Gratuita; veja o [passo 4](#4-chave-da-groq-e-arquivo-env)                              |
| **Internet**         | Só para o backend falar com a Groq. A interface em si funciona sem internet             |
| **Microfone**        | Opcional, para a voz                                                                    |
| **Navegador**        | Chrome, Edge, Firefox ou Safari atuais                                                  |

```powershell
py --version        # Windows
```
```bash
python3 --version   # Linux / macOS
```

Se for menor que 3.11, instale em [python.org/downloads](https://www.python.org/downloads/) (no Windows, marque **Add python.exe to PATH**). No Debian/Ubuntu, instale também o módulo de ambientes virtuais: `sudo apt install python3-venv`.

## 2. Baixar o projeto

```bash
git clone https://github.com/Rayck4dev/ProfAssitencIA_IA_agent.git
cd ProfAssitencIA_IA_agent
git checkout backend-profassistenc    # ajuste para a branch onde esta versão estiver
cd backend
```

Todos os comandos seguintes são executados dentro de `backend/`.

## 3. Ambiente virtual e dependências

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o PowerShell bloquear o script, rode antes (só vale para a janela atual):
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O terminal passa a mostrar `(.venv)`. **Ative o ambiente de novo sempre que abrir um terminal novo.**

## 4. Chave da Groq e arquivo `.env`

### 4.1 Gerar a chave

1. Acesse **[console.groq.com/keys](https://console.groq.com/keys)** e entre (conta Google ou e-mail).
2. Clique em **Create API Key**, dê um nome (ex.: `profassistenc`) e copie a chave. Ela só aparece uma vez.

### 4.2 Criar o `.env`

```powershell
copy .env.example .env      # Windows
```
```bash
cp .env.example .env        # Linux / macOS
```

Abra o `.env` e cole a chave:

```env
GROQ_API_KEY=cole_sua_chave_aqui
```

As demais opções são opcionais (tabela completa em [DOCUMENTACAO.md](DOCUMENTACAO.md#configurações)).

> ⚠️ **Nunca envie o `.env` ao GitHub** (ele já está no `.gitignore`). Se a chave vazar, apague-a no console da Groq e gere outra.

## 5. Executar

```bash
python run.py
```

O navegador abre em **http://localhost:5000**. Para encerrar, volte ao terminal e use `Ctrl + C`.

Na primeira execução o banco de conversas (`backend/profassistenc.db`) é criado sozinho. A base de documentos (BNCC e RCSEERO) já acompanha o projeto em `backend/data/knowledge.sqlite`: **não é preciso baixar PDFs nem indexar nada** para usar.

## 6. Verificar se está tudo certo

| O que testar                                                | Resultado esperado                                                                           |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Abrir http://localhost:5000                                 | Tela "O que vamos planejar hoje?"                                                            |
| Canto inferior esquerdo da tela                             | **IA conectada · llama-3.1-8b-instant** e **Documentos oficiais ativos: BNCC · RCSEERO**     |
| http://localhost:5000/api/health                            | `aiConfigured: true` e `knowledgeBase.available: true` (2 documentos, 4342 trechos)          |
| http://localhost:5000/docs                                  | Swagger com os endpoints                                                                     |
| Pedir "plano de aula de matemática do 5º ano sobre frações" | Plano com habilidades `EF05MA…` e, no fim, a linha **Documentos consultados: BNCC (p. …)**   |

Se o status disser **IA sem chave**, a `GROQ_API_KEY` não foi lida (confira o `.env`, sem aspas nem espaços). Se disser **Servidor offline**, o `python run.py` não está rodando.

## 7. Usar a voz

* Clique em **Falar**, permita o microfone quando o navegador pedir, fale e clique em **Parar**. O texto transcrito aparece na caixa de mensagem para você revisar e enviar. `Esc` cancela a gravação.
* **Conversa por voz** (chave ao lado do botão): a fala é enviada automaticamente e a resposta é lida em voz alta.
* **Ouvir**, embaixo de cada resposta, lê aquela resposta (clique de novo para parar).

Requisitos e observações:

* O navegador só libera o microfone em **`http://localhost`** (ou HTTPS). Acessar por um IP da rede (`http://192.168...`) **não funciona** sem HTTPS.
* A leitura em voz alta usa as vozes do seu sistema. No Windows (Edge e Chrome) costuma haver voz em português; no Linux pode ser preciso instalar uma voz pt-BR.
* A transcrição usa o Whisper da Groq e tem limite próprio no plano gratuito (veja o console da Groq).

## 8. Limites do plano gratuito

Na data de escrita, o plano gratuito da Groq para o `llama-3.1-8b-instant` permite **6.000 tokens por minuto**, 30 pedidos por minuto e 500 mil tokens por dia (confira os valores atuais em [console.groq.com/docs/rate-limits](https://console.groq.com/docs/rate-limits)).

Na prática: cada plano de aula usa **de 3 a 5 mil tokens** (pergunta + trechos dos documentos + histórico + resposta). Por isso:

* Dois planos seguidos em menos de um minuto podem esbarrar no limite. O sistema espera alguns segundos e tenta de novo; se a espera for longa, mostra **"Limite de uso da IA atingido. Tente novamente em N minutos."**
* O sistema já limita o contexto enviado (`RAG_MAX_CHARS`, `HISTORY_MAX_CHARS` e `GROQ_MAX_TOKENS`). **Não aumente esses valores no plano gratuito.** Com plano pago (ou um modelo com limite maior) pode aumentar para planos mais completos.
* Se a conversa ficar muito longa e o modelo recusar por tamanho, inicie uma **Nova conversa**.

Quer respostas melhores em português? Experimente `GROQ_MODEL=llama-3.3-70b-versatile` no `.env` (modelo maior; os limites são outros, veja o console).

## 9. Rodar os testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Os testes **não usam internet nem chave** (a Groq é simulada). Resultado esperado: a última linha mostra apenas `passed`.

## 10. Modo desenvolvimento e Groq simulado

Recarregar o servidor ao editar o código:

```bash
uvicorn app.main:app --reload --port 5000
```

**Rodar sem chave e sem gastar o limite (Groq simulado)** — útil para mexer na interface ou fazer demonstração. Em um segundo terminal (com o ambiente ativo, em `backend/`):

```bash
python tools/fake_groq.py
```

e no `.env`:

```env
GROQ_API_KEY=qualquer-coisa
GROQ_BASE_URL=http://127.0.0.1:9911/openai/v1
```

As respostas desse modo são **de exemplo** (montadas a partir dos trechos recuperados); servem para ver o RAG, a voz e a interface funcionando. Volte o `.env` ao normal para usar a IA de verdade.

**Frontend separado (Live Server):** o caminho recomendado é usar o frontend servido pelo backend. Se abrir `frontend/` no Live Server (porta 5500), adicione em `frontend/index.html`, **antes** da tag de `./js/app.js`:

```html
<script>window.PROFASSISTENC_API_URL = "http://localhost:5000";</script>
```

O backend já aceita requisições de `localhost:5500` (CORS). O microfone funciona em `localhost` em qualquer porta.

## 11. Atualizar ou trocar os documentos (RAG)

O projeto acompanha `backend/data/knowledge.sqlite`, já com a **BNCC** (600 páginas) e o **RCSEERO** (860 páginas) indexados. Só refaça o índice se quiser **adicionar outros PDFs** (por exemplo, um referencial curricular de Educação Infantil/Fundamental de Rondônia) ou **trocar os existentes**.

1. Coloque os PDFs em `backend/knowledge/` (crie a pasta).
2. Instale a dependência de leitura de PDF:
   ```bash
   pip install -r requirements-ingest.txt
   ```
3. Gere a base:
   ```bash
   python -m app.rag.ingest knowledge/
   ```
   Isso recria `data/knowledge.sqlite` **do zero** com todos os PDFs da pasta (leva alguns segundos). Para manter os atuais, coloque-os na pasta junto com os novos.
4. Reinicie o servidor. O status na tela mostra os nomes dos documentos ativos.

Observações:

* O nome curto de cada documento vem do nome do arquivo (ex.: `PCRO_EF.pdf` → `PCRO`). `BNCC` e `RCSEERO` são reconhecidos e recebem título e etapas corretos (ajustáveis em `KNOWN_DOCS`, no arquivo `app/rag/ingest.py`).
* O PDF precisa ter **texto selecionável**. PDFs escaneados (só imagem) não funcionam sem OCR prévio.
* PDFs com estrutura interna danificada (era o caso do arquivo da BNCC fornecido) são lidos normalmente: o leitor usado repara o arquivo sozinho.
* Para o RAG reconhecer códigos de habilidade de um documento novo, eles precisam seguir o padrão da BNCC (ex.: `EF05MA03`, `EM13MAT102`). Outros formatos de código ainda são buscados como texto comum, mas não entram na conferência anti-invenção.

## 12. Gerar um executável

Empacota backend, frontend, assets e a base de documentos em **um único arquivo**, para computadores sem Python. O executável só roda no sistema em que foi gerado (para obter um `.exe`, gere no Windows).

Dentro de `backend/`, com o ambiente ativo:

**Windows (PowerShell):**

```powershell
pip install -r requirements-build.txt
pyinstaller --onefile --name ProfAssistenc --collect-submodules uvicorn `
  --add-data "..\frontend;frontend" --add-data "..\assets;assets" --add-data "data\knowledge.sqlite;data" run.py
```

**Linux / macOS:**

```bash
pip install -r requirements-build.txt
pyinstaller --onefile --name ProfAssistenc --collect-submodules uvicorn \
  --add-data "../frontend:frontend" --add-data "../assets:assets" --add-data "data/knowledge.sqlite:data" run.py
```

O arquivo sai em `backend/dist/`. Para distribuir, copie-o para uma pasta e crie ao lado um `.env` com a chave:

```text
MinhaPasta/
├── ProfAssistenc.exe
└── .env          ← GROQ_API_KEY=...
```

O banco de conversas (`profassistenc.db`) é criado ao lado do executável. Mantenha a janela do terminal aberta enquanto usa; fechá-la encerra o servidor. As pastas `build/`, `dist/` e o arquivo `.spec` não devem ir para o GitHub.

> O executável foi validado em Linux (frontend, base de documentos, RAG e transcrição). O comando do Windows segue o mesmo formato, mas não foi executado em Windows.

## 13. Migrando de versões anteriores

* **Do Gemini para a Groq:** troque `GEMINI_API_KEY` por `GROQ_API_KEY` no `.env`. As variáveis `GEMINI_*` deixam de ter efeito.
* **Do backend em C#:** copie o `profassistenc.db` antigo para `backend/` (ou para ao lado do executável); as tabelas são as mesmas e nada precisa ser migrado.
* **Histórico não aparece?** O navegador identifica a instalação por um código guardado **por endereço** (`localhost:5000` ≠ `localhost:5096`). Abra a aplicação pelo mesmo endereço que usava antes (o padrão é a porta 5000; para outra porta, defina `PORT` no `.env`).

## 14. Solução de problemas

| Sintoma                                                              | Causa provável e solução                                                                                                                                                  |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python` / `py` não é reconhecido                                    | Python fora do PATH. Reinstale marcando **Add python.exe to PATH**.                                                                                                       |
| `No module named 'fastapi'` (ou outro)                               | Ambiente virtual inativo ou dependências não instaladas: ative o `.venv` e rode `pip install -r requirements.txt`.                                                        |
| Erro de tipo logo ao iniciar (`unsupported operand type(s) for \|`)   | Python mais antigo que 3.11. Atualize.                                                                                                                                    |
| Status **IA sem chave**                                              | `GROQ_API_KEY` ausente no `.env` (ou `.env` fora da pasta `backend/`). Reinicie depois de salvar.                                                                         |
| Erro **"O Groq recusou a chave"**                                    | Chave incorreta ou apagada. Gere outra em console.groq.com/keys.                                                                                                          |
| **"Limite de uso da IA atingido…"**                                  | Limite por minuto ou por dia do plano gratuito. Aguarde o tempo indicado (veja o [passo 8](#8-limites-do-plano-gratuito)).                                                |
| **"A conversa ficou grande demais…"**                                | Histórico + contexto passaram do limite do modelo. Clique em **Nova conversa**.                                                                                           |
| Erro genérico "Não foi possível obter uma resposta da IA."           | Veja o terminal: o log mostra o motivo. Causas: sem internet; **modelo inexistente ou descontinuado** (log com `HTTP 404`/`model_decommissioned`: troque `GROQ_MODEL`).   |
| O plano cita códigos que "não aparecem nos documentos"               | Comportamento esperado da trava anti-invenção: o modelo errou um código. Use só os códigos confirmados e confira na BNCC/RCSEERO.                                         |
| A IA diz que o documento não traz o ano/componente pedido            | O pedido está fora do que os PDFs cobrem (ex.: Fundamental no RCSEERO) ou faltou informar ano e componente. Informe-os (ex.: "5º ano de Matemática").                      |
| Botão **Falar** não grava                                            | Acesse por `http://localhost` (não por IP). Permita o microfone no cadeado ao lado do endereço. Veja o [passo 7](#7-usar-a-voz).                                          |
| "Não consegui entender o áudio"                                      | Gravação muda ou muito baixa. Fale mais perto do microfone e grave ao menos 1 segundo.                                                                                    |
| Resposta não é lida em voz alta                                      | O sistema não tem voz em português instalada (comum no Linux). Instale uma voz pt-BR.                                                                                     |
| `address already in use`                                             | Porta 5000 ocupada. Defina outra no `.env` (`PORT=5001`). No **macOS**, o "Receptor AirPlay" usa a 5000: mude a porta ou desative-o.                                      |
| Mudei o `.env` e nada mudou                                          | O `.env` só é lido ao iniciar. Pare (`Ctrl + C`) e rode `python run.py` de novo.                                                                                          |
| Status mostra **Sem base de documentos**                             | `backend/data/knowledge.sqlite` ausente. Restaure o arquivo ou gere-o (passo 11). Sem a base o sistema funciona, mas sem consultar a BNCC/RCSEERO.                        |
| Antivírus/SmartScreen bloqueia o `.exe`                              | Falso positivo comum em executáveis do PyInstaller `--onefile`. Libere o arquivo ou rode com `python run.py`.                                                              |
| Quero apagar todas as conversas                                      | Pare o servidor e apague `profassistenc.db`; ele é recriado vazio.                                                                                                        |
