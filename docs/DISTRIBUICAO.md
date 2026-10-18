# Guia de distribuição: gerar o `.exe` e entregar aos professores

Para **quem prepara o programa** (equipe técnica, coordenação de tecnologia). O professor não precisa ler isto: ele usa o [passo a passo de instalação](INSTALACAO_PROFESSORES.md).

## Sumário

1. [O que será entregue](#1-o-que-será-entregue)
2. [O que você precisa para gerar](#2-o-que-você-precisa-para-gerar)
3. [Gerar o programa (.exe e .zip)](#3-gerar-o-programa-exe-e-zip)
4. [Gerar o instalador (Setup.exe)](#4-gerar-o-instalador-setupexe)
5. [Testar em um computador limpo](#5-testar-em-um-computador-limpo)
6. [Publicar e entregar aos professores](#6-publicar-e-entregar-aos-professores)
7. [SmartScreen e antivírus](#7-smartscreen-e-antivírus)
8. [Chaves da IA: como organizar na escola](#8-chaves-da-ia-como-organizar-na-escola)
9. [Rede da escola e computadores compartilhados](#9-rede-da-escola-e-computadores-compartilhados)
10. [Atualizar para uma versão nova](#10-atualizar-para-uma-versão-nova)
11. [Linux e macOS](#11-linux-e-macos)
12. [Problemas ao gerar](#12-problemas-ao-gerar)
13. [Referência dos arquivos](#13-referência-dos-arquivos)

---

## 1. O que será entregue

| Entrega | Arquivo | Para quem |
| --- | --- | --- |
| **Pacote zip** (portátil) | `ProfAssistenc-2.1.0-windows.zip` | Qualquer professor. Funciona até sem permissão para instalar programas |
| **Instalador** | `ProfAssistenc-Setup-2.1.0.exe` | Quando a escola prefere atalhos automáticos (menu Iniciar e Área de Trabalho) |
| **Manual em PDF** | `docs/Manual-ProfAssistenc.pdf` | Anexar à entrega (instalação + uso) |

O programa **não leva a chave da IA nem conversas**. Cada professor informa a sua chave **uma vez**, em uma janela do próprio programa, e as conversas ficam no computador dele.

> **Por que a chave não vai dentro do programa?** Uma chave embutida pode ser extraída por qualquer pessoa, usada por terceiros e consumiria a cota de todos. Veja o [item 8](#8-chaves-da-ia-como-organizar-na-escola).

## 2. O que você precisa para gerar

O `.exe` **só pode ser gerado no Windows** (cada sistema gera o seu programa).

| Item | Observação |
| --- | --- |
| Windows 10 ou 11 (64 bits) | Onde o `.exe` será gerado |
| **Python 3.11 ou mais novo** | [python.org/downloads](https://www.python.org/downloads/). No instalador, marque **Add python.exe to PATH** |
| O código do projeto | `git clone` do repositório ou o zip dele extraído |
| Internet | Para baixar as dependências na primeira vez |
| *(Opcional)* **Inno Setup 6.3+** | Gratuito, em [jrsoftware.org](https://jrsoftware.org/isinfo.php). Só para o instalador (item 4) |

## 3. Gerar o programa (.exe e .zip)

### Jeito fácil: dois cliques

1. Abra a pasta `backend` do projeto.
2. Dê dois cliques em **`construir_windows.bat`**.
3. Espere alguns minutos (na primeira vez ele baixa as dependências, então depende da sua internet).

O arquivo cria um ambiente próprio (`.venv-build`), instala o necessário, gera o programa e compacta tudo. No fim aparece "Pronto!".

### Resultado (na pasta `backend\dist\`)

```text
dist\
├── ProfAssistenc\                          ← o programa pronto (pasta)
│   ├── ProfAssistenc.exe
│   ├── _internal\                          ← bibliotecas, interface e base da BNCC/RCSEERO
│   └── LEIA-ME.txt
├── ProfAssistenc-2.1.0-windows.zip         ← entregar aos professores
└── ProfAssistenc-2.1.0-windows.zip.sha256  ← "impressão digital" para conferir o arquivo
```

### Pelo terminal (alternativa)

Dentro de `backend\`:

```powershell
py -m venv .venv-build
.venv-build\Scripts\Activate.ps1
pip install -r requirements-build.txt
python build_exe.py
```

Opções do `build_exe.py`:

| Opção | O que faz |
| --- | --- |
| *(nenhuma)* | Gera uma **pasta** com o programa e o `.zip`. **Recomendado**: abre mais rápido e é menos marcado por antivírus |
| `--onefile` | Gera **um único arquivo** `.exe`. Abre mais devagar (descompacta a cada vez) |
| `--sem-zip` | Só gera o programa, sem compactar |

> O programa **inclui a base da BNCC e do RCSEERO** (`backend\data\knowledge.sqlite`). Para trocar ou acrescentar documentos, refaça a base **antes** de gerar o `.exe` (veja o [Guia técnico](INSTALACAO.md#11-atualizar-ou-trocar-os-documentos-rag)).

## 4. Gerar o instalador (Setup.exe)

Opcional. O instalador cria os atalhos e permite desinstalar pelo Windows.

1. Gere o programa (item 3). A pasta `backend\dist\ProfAssistenc` precisa existir.
2. Instale o **Inno Setup 6.3+**.
3. Abra o arquivo **`installer\ProfAssistenc.iss`** no Inno Setup.
4. Clique em **Build → Compile** (ou `Ctrl+F9`).
5. O instalador sai em **`installer\output\ProfAssistenc-Setup-2.1.0.exe`**.

O que o instalador faz:

* instala na pasta do usuário (`%LOCALAPPDATA%\Programs\ProfAssistenc`): **não pede senha de administrador** e o programa consegue gravar o banco e a chave;
* cria atalho no menu Iniciar e (opcional) na Área de Trabalho;
* ao **atualizar por cima, não apaga** conversas nem chave;
* ao **desinstalar, pergunta** se as conversas e a chave devem ser apagadas.

**Instalar para todos os usuários do computador** (laboratório): no `.iss`, troque `PrivilegesRequired=lowest` por `admin` e `DefaultDirName={localappdata}\Programs\{#MyAppName}` por `{autopf}\{#MyAppName}`. Nesse caso o programa percebe que a pasta é protegida e guarda o banco e a chave de **cada usuário do Windows** em `%LOCALAPPDATA%\ProfAssistenc`, de modo que cada professor tem as suas conversas e a sua chave.

> ⚠️ **Não foi possível testar a geração do `.exe` nem o Inno Setup em Windows** durante a elaboração deste guia: a construção e os testes do programa foram feitos em Linux, e o `.bat` e o `.iss` seguem o formato documentado dessas ferramentas. **Faça o teste do item 5 antes de distribuir** e, se algo falhar, veja o [item 12](#12-problemas-ao-gerar).

## 5. Testar em um computador limpo

Nunca distribua sem testar em um computador **que não tenha Python nem o projeto**, para simular o professor.

**Jeito mais fácil: Windows Sandbox** (Windows 10/11 Pro, Enterprise ou Education). Ative em *Ativar ou desativar recursos do Windows → Windows Sandbox*, reinicie e abra o **Windows Sandbox**: é um Windows novo e descartável. Arraste o `.zip` (ou o `Setup.exe`) para dentro dele.
Outras opções: uma máquina virtual, ou o computador de um colega.

**Roteiro do teste** (siga o [guia do professor](INSTALACAO_PROFESSORES.md) como se fosse um):

- [ ] Extrair o zip (ou instalar) e abrir o programa. A janela preta mostra "ProfAssistenc 2.1.0" e o navegador abre.
- [ ] Aparece a janela **Chave da IA**. Colar uma chave **inválida** → mensagem de erro, nada salvo.
- [ ] Colar uma chave **válida** → "Chave salva", status "IA conectada".
- [ ] Pedir *"plano de aula de frações para o 5º ano"* → resposta com habilidades `EF05MA…` e "Documentos consultados: BNCC".
- [ ] Pedir com erros de digitação: *"aula de matematca pro 5 ano"* → responde.
- [ ] **Falar**: gravar uma frase → vira texto (o navegador pede permissão do microfone).
- [ ] **Imprimir** uma resposta → mostra só o plano.
- [ ] Fechar a janela preta e **abrir de novo logo em seguida** → abre normalmente, a chave e a conversa continuam lá.
- [ ] Dar dois cliques **duas vezes seguidas** no programa → não dá erro (só reabre o navegador).
- [ ] Os arquivos `.env`, `profassistenc.db` e `profassistenc.log` aparecem **ao lado do programa**.
- [ ] Atualizar: extrair/instalar a versão seguinte por cima → conversas e chave continuam.

Confira também a **impressão digital** do arquivo que será entregue (para garantir que não foi alterado):

```powershell
Get-FileHash .\ProfAssistenc-2.1.0-windows.zip -Algorithm SHA256
```

O resultado deve ser igual ao do arquivo `.sha256` gerado junto.

## 6. Publicar e entregar aos professores

**Pelo GitHub (recomendado):**

1. No repositório, vá em **Releases → Draft a new release**.
2. Crie a etiqueta (*tag*) `v2.1.0`, título "ProfAssistenc 2.1.0".
3. Anexe: o `.zip`, o `Setup.exe` (se tiver), o `.sha256` e o `Manual-ProfAssistenc.pdf`.
4. No texto, diga em poucas linhas o que mudou e coloque o **link do manual**.
5. Publique e envie aos professores o **link da página da release**.

> **Repositório privado?** Só quem tem acesso baixa. Para distribuir a todos, torne-o público ou use outro meio (Google Drive/OneDrive da escola, rede interna).

**Outros meios:** Google Drive/OneDrive da escola, pendrive, pasta de rede. Sempre envie junto o **Manual (PDF)**.

**Mensagem sugerida aos professores:**

> Pessoal, segue o ProfAssistenc, um assistente que ajuda a planejar aulas com base na BNCC e no Referencial de Rondônia. Baixe o arquivo, siga o manual em PDF (instalação leva uns 10 minutos) e, na primeira vez, o programa pede uma chave gratuita da Groq, que o manual ensina a criar. Se aparecer um aviso azul do Windows, clique em *Mais informações → Executar assim mesmo*.

## 7. SmartScreen e antivírus

O programa **não é assinado digitalmente**, então:

* o **Windows SmartScreen** mostra "O Windows protegeu o computador" na primeira execução. O professor deve clicar em **Mais informações → Executar assim mesmo** (isso está no manual);
* alguns **antivírus** podem marcar programas feitos com PyInstaller como suspeitos (falso positivo comum).

O que ajuda, da opção mais simples à mais completa:

1. **Orientar os professores** (já está no manual). É suficiente para a maioria dos casos.
2. **Distribuir pelo Setup.exe** ou pela pasta (`--onedir`, o padrão): costuma ser **menos marcado** que o arquivo único (`--onefile`).
3. **Pedir ao suporte da escola** para liberar a pasta/arquivo no antivírus.
4. **Enviar o arquivo como falso positivo** à Microsoft pelo portal *Microsoft Security Intelligence → Submit a file* (microsoft.com/wdsi/filesubmission), e ao fabricante do antivírus usado.
5. **Assinar o programa** com um certificado de assinatura de código (pago). Reduz muito os avisos, mas custa e exige ferramentas próprias.

## 8. Chaves da IA: como organizar na escola

**Recomendado: cada professor cria a sua própria chave gratuita** (o manual explica, leva 2 minutos). O plano gratuito da Groq tem limites **por conta** (por minuto e por dia). Se várias pessoas dividirem **uma** chave, o limite é dividido entre todas: a IA passa a responder "Limite de uso atingido" com frequência.

| Opção | Vantagem | Cuidado |
| --- | --- | --- |
| **Chave individual** (recomendado) | Cada um tem o seu limite; nada para gerenciar | Cada professor precisa de uma conta Groq |
| **Uma chave da escola** | Um cadastro só; é possível usar plano pago | Todos dividem o limite; quem tiver a chave pode usá-la fora do programa; revogue-a se vazar. Informe-a em **cada** computador, pela janela do programa |

Nunca coloque uma chave dentro do código, do `.zip` ou do `.env.example`. Se uma chave vazar, **exclua-a** em console.groq.com/keys e gere outra.

## 9. Rede da escola e computadores compartilhados

**Rede.** O programa só precisa de acesso à internet (porta 443) para:

| Endereço | Para quê |
| --- | --- |
| `api.groq.com` | Respostas da IA, voz e teste da chave |
| `console.groq.com` | O professor criar a chave (no navegador) |

Se a escola usa filtro ou *proxy*, peça a liberação desses endereços. Teste: no navegador do computador, abra `https://console.groq.com`; se carregar, a rede está liberada. Sem acesso, o programa mostra *"Não consegui falar com a Groq"*.

**Não é necessário** abrir portas no *firewall*: o programa só responde ao próprio computador (`localhost`).

**Computadores compartilhados (laboratório).** As conversas e a chave ficam na pasta do programa (ou, na instalação para todos, na pasta de cada usuário do Windows). Se vários professores usam **o mesmo usuário do Windows**, eles compartilham a chave e as conversas. Recomendações: um usuário do Windows por professor; **não** instalar o programa em um pendrive compartilhado com a chave de alguém; e orientar a **não usar dados pessoais de estudantes** nos pedidos.

**Uso em rede (servidor da escola):** não é recomendado nesta versão. Não há login por usuário, e o navegador só libera o microfone em `localhost` ou HTTPS.

## 10. Atualizar para uma versão nova

**Para quem prepara:**

1. Atualize o código e, se mudou a versão, edite o número em **dois** lugares: `backend\app\__init__.py` (`__version__`) e `installer\ProfAssistenc.iss` (`#define MyAppVersion`).
2. Gere de novo (item 3 e, se quiser, 4) e **teste** (item 5).
3. Publique a nova release (item 6) e avise os professores.

**Para o professor** (já explicado no manual):

* **Instalador:** executar o novo `Setup.exe`: atualiza sem apagar conversas nem chave.
* **Zip:** fechar o programa e extrair o novo zip **na mesma pasta**, escolhendo "Substituir os arquivos": conversas e chave ficam, pois não estão dentro do zip.

O banco de conversas é compatível entre versões (as versões anteriores do projeto usam as mesmas tabelas).

## 11. Linux e macOS

O `build_exe.py` funciona nesses sistemas, mas gera o programa **do sistema em que for executado**:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-build.txt
python build_exe.py
```

* **Linux:** gera `ProfAssistenc-2.1.0-linux.zip` (validado nos testes deste projeto). Também dá para rodar direto pelo Python (`python run.py`).
* **macOS:** gera o programa para macOS (não testado). O macOS pode bloquear o aplicativo de "desenvolvedor não identificado": é preciso **clicar com o botão direito → Abrir** na primeira vez. Rodar por `python run.py` é mais simples.

## 12. Problemas ao gerar

| Sintoma | Solução |
| --- | --- |
| `construir_windows.bat`: "Python nao encontrado" | Instale o Python 3.11+ marcando **Add python.exe to PATH** e abra o arquivo de novo |
| Erro ao instalar dependências | Confira a internet e se há *proxy*; rode de novo |
| `ERRO: arquivo necessário não encontrado … knowledge.sqlite` | Faltou a base. Restaure `backend\data\knowledge.sqlite` (ou gere-a: veja o Guia técnico) |
| `ERRO: PyInstaller não está instalado` | `pip install -r requirements-build.txt` com o ambiente ativo |
| O antivírus apagou arquivos de `dist\` durante a geração | Adicione a pasta do projeto às exceções e gere de novo |
| Erro de caminho muito longo | Mova o projeto para uma pasta curta (ex.: `C:\profassistenc`) |
| O `.exe` abre e fecha na hora | Abra pelo terminal (`.\ProfAssistenc.exe`) para ver a mensagem, e veja o `profassistenc.log` |
| Inno Setup: erro de idioma `BrazilianPortuguese.isl` | Use o Inno Setup 6.3+ completo, que inclui o idioma, ou remova a seção `[Languages]` |
| Inno Setup: erro no ícone | Confirme que `assets\favicon.ico` existe |

## 13. Referência dos arquivos

| Arquivo | Para quê |
| --- | --- |
| `backend/construir_windows.bat` | Gera o programa no Windows com dois cliques |
| `backend/build_exe.py` | O script que faz a geração (PyInstaller + `.zip` + SHA-256) |
| `backend/requirements-build.txt` | Dependências para gerar (inclui o PyInstaller) |
| `installer/ProfAssistenc.iss` | Script do instalador (Inno Setup) |
| `installer/LEIA-ME.txt` | Texto curto que vai dentro do pacote |
| `assets/favicon.ico` | Ícone do programa e do instalador |
| `docs/Manual-ProfAssistenc.pdf` | Manual do professor (instalação + uso) |
| `docs/INSTALACAO_PROFESSORES.md` · `docs/GUIA_DO_PROFESSOR.md` | Texto-fonte do manual |

**Onde o programa guarda os dados do professor**, ao lado do executável (ou em `%LOCALAPPDATA%\ProfAssistenc` quando a pasta do programa não permite gravar):

| Arquivo | Conteúdo |
| --- | --- |
| `.env` | Chave da IA e configurações (permissão restrita; não compartilhar) |
| `profassistenc.db` | Conversas e mensagens |
| `profassistenc.log` | Funcionamento do programa e erros, para o suporte (**sem** o texto das conversas e **sem** a chave) |
