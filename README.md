# ProfAssistenc IA

<p align="center">
	<strong>Assistente inteligente para planejamento docente</strong>
</p>

<p align="center">
	<img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
	<img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3" />
	<img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript" />
	<img src="https://img.shields.io/badge/C%23-239120?style=for-the-badge&logo=csharp&logoColor=white" alt="C#" />
	<img src="https://img.shields.io/badge/.NET%2010-512BD4?style=for-the-badge&logo=dotnet&logoColor=white" alt=".NET 10" />
	<img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
	<img src="https://img.shields.io/badge/Entity%20Framework%20Core-512BD4?style=for-the-badge&logo=.net&logoColor=white" alt="Entity Framework Core" />
	<img src="https://img.shields.io/badge/Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black" alt="Swagger" />
	<img src="https://img.shields.io/badge/Gemini%20API-8E75B2?style=for-the-badge&logo=google&logoColor=white" alt="Google Gemini API" />
</p>

## Sobre o projeto

O **ProfAssistenc IA** é uma aplicação desktop desenvolvida para apoiar professores no planejamento de aulas e atividades por meio de Inteligência Artificial.

A aplicação oferece uma interface de conversa com um assistente de planejamento docente, permitindo fazer perguntas, gerar sugestões de planejamento, continuar conversas utilizando o contexto anterior e consultar o histórico de interações.

O projeto foi desenvolvido como uma aplicação acadêmica, com foco no aprendizado prático de desenvolvimento de software, integração entre frontend e backend, persistência de dados e consumo de APIs externas.

O sistema é dividido em:

* **Frontend:** interface responsiva desenvolvida com HTML, CSS e JavaScript.
* **Backend:** API REST desenvolvida em C# com ASP.NET Core e .NET 10.
* **Persistência:** SQLite com Entity Framework Core para armazenar conversas e mensagens.
* **Inteligência Artificial:** integração com a API do Google Gemini para geração de respostas e títulos das conversas.

Na versão publicada, o backend também é responsável por servir o frontend, permitindo executar a aplicação através de um único arquivo `.exe`.

---

## Funcionalidades

* Conversa com o assistente de planejamento docente.
* Geração de respostas utilizando o contexto das mensagens anteriores.
* Criação automática de títulos para novas conversas utilizando IA.
* Histórico persistente de conversas.
* Identificação das conversas por instalação da aplicação.
* Renomeação de conversas.
* Exclusão de conversas.
* Persistência local utilizando SQLite.
* Integração com a API do Google Gemini.
* Indicador visual do status da API.
* Interface integrada ao backend ASP.NET Core.
* Documentação dos endpoints utilizando Swagger/OpenAPI.
* Execução como aplicação Windows através de um executável self-contained.
* `Enter` para enviar mensagens.
* `Ctrl + Enter` para inserir quebra de linha.

---

## Tecnologias

### Frontend

* HTML5
* CSS3
* JavaScript
* Tailwind CSS via CDN
* Lucide Icons
* KaTeX para renderização de fórmulas matemáticas

### Backend

* C#
* ASP.NET Core Web API
* .NET 10
* Entity Framework Core
* SQLite
* Swagger/OpenAPI
* HttpClient
* Injeção de Dependência

### Inteligência Artificial

* Google Gemini API
* Modelo configurado atualmente: `gemini-3.6-flash`

### Ferramentas

* Visual Studio
* Visual Studio Code
* Git
* GitHub
* Entity Framework Core CLI

---

## Arquitetura

A aplicação utiliza o ASP.NET Core como backend e também como servidor dos arquivos do frontend.

```text
                         ┌──────────────────────┐
                         │       Frontend       │
                         │    HTML / CSS / JS   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     ASP.NET Core     │
                         │       Backend        │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
             ┌────────────┐ ┌──────────────┐ ┌──────────────┐
             │ Controllers│ │   Services   │ │   EF Core    │
             └────────────┘ └──────┬───────┘ └──────┬───────┘
                                   │                │
                                   ▼                ▼
                           ┌──────────────┐  ┌──────────────┐
                           │ Gemini API   │  │    SQLite    │
                           └──────────────┘  └──────────────┘
```

Na versão publicada:

```text
ProfAssistenc.Api.exe
        │
        ▼
   ASP.NET Core
        │
        ├── Frontend
        │
        └── API
             │
             ├── SQLite
             │
             └── Gemini API
```

---

## Estrutura do projeto

```text
ProfAssitencIA_IA_agent/
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── backend/
│   └── ProfAssistenc.Api/
│       ├── Controllers/
│       │   ├── ConversationsController.cs
│       │   └── LessonPlanController.cs
│       │
│       ├── Data/
│       │   └── AppDbContext.cs
│       │
│       ├── Entities/
│       │   ├── Conversation.cs
│       │   └── MessageEntity.cs
│       │
│       ├── Migrations/
│       │
│       ├── Models/
│       │
│       ├── Services/
│       │   ├── AIService.cs
│       │   ├── ConversationService.cs
│       │   └── LessonPlanService.cs
│       │
│       ├── wwwroot/
│       │   ├── index.html
│       │   ├── css/
│       │   └── js/
│       │
│       ├── appsettings.json
│       ├── Program.cs
│       └── ProfAssistenc.Api.csproj
│
├── .gitignore
└── README.md
```

A pasta `wwwroot` contém a versão do frontend que é servida diretamente pelo ASP.NET Core na aplicação integrada.

---

# Pré-requisitos

Para executar o projeto a partir do código-fonte:

* Windows 10 ou superior
* [.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0)
* Git
* Um navegador atualizado
* Uma chave da API do [Google Gemini](https://ai.google.dev/)

Para executar somente a versão `.exe`, não é necessário instalar o .NET, pois a aplicação é publicada como **self-contained**.

---

# Executando pelo código-fonte

## 1. Clonar o repositório

```powershell
git clone https://github.com/VictorMacedoCB/ProfAssitencIA_IA_agent.git
```

Entre na pasta:

```powershell
cd ProfAssitencIA_IA_agent
```

A branch que contém o desenvolvimento atual do backend é:

```powershell
git checkout backend-profassistenc
```

---

## 2. Configurar a API do Gemini

O projeto precisa de uma chave própria da API do Gemini para gerar as respostas da IA.

Na pasta:

```text
backend/ProfAssistenc.Api/
```

crie o arquivo:

```text
appsettings.Local.json
```

Com:

```json
{
  "Gemini": {
    "ApiKey": "SUA_CHAVE_DA_API_GEMINI"
  }
}
```

Substitua `SUA_CHAVE_DA_API_GEMINI` pela sua chave real.

### Importante

O arquivo `appsettings.Local.json` está no `.gitignore` e **não deve ser enviado para o GitHub**.

Nunca coloque uma API Key diretamente no código ou em arquivos versionados publicamente.

---

## 3. Restaurar as dependências

Entre na pasta do backend:

```powershell
cd backend\ProfAssistenc.Api
```

Execute:

```powershell
dotnet restore
```

---

## 4. Configurar o banco de dados

O projeto utiliza SQLite através do Entity Framework Core.

O banco é criado como:

```text
profassistenc.db
```

As migrations existentes ficam em:

```text
backend/ProfAssistenc.Api/Migrations/
```

Para atualizar manualmente o banco utilizando as migrations:

```powershell
dotnet ef database update
```

Caso o comando `dotnet ef` não esteja instalado:

```powershell
dotnet tool install --global dotnet-ef
```

> Durante a inicialização da aplicação, o backend também aplica automaticamente as migrations existentes através do `Database.Migrate()`.

---

## 5. Executar o backend

Ainda na pasta:

```text
backend\ProfAssistenc.Api
```

execute:

```powershell
dotnet run
```

O ASP.NET Core iniciará o servidor local.

Durante o desenvolvimento, a porta pode ser:

```text
http://localhost:5096
```

Acesse no navegador:

```text
http://localhost:5096
```

Como o backend serve os arquivos presentes em `wwwroot`, o frontend será carregado automaticamente.

### Swagger

Durante o ambiente de desenvolvimento, a documentação da API pode ser acessada em:

```text
http://localhost:5096/swagger
```

---

# Executando o frontend separadamente

Durante as primeiras etapas de desenvolvimento, o frontend também pode ser executado separadamente utilizando uma ferramenta como o **Live Server** do VS Code.

O endereço padrão utilizado durante esse desenvolvimento foi:

```text
http://127.0.0.1:5500
```

O backend possui uma política de CORS permitindo:

```text
http://127.0.0.1:5500
http://localhost:5500
```

Na versão integrada e publicada, essa etapa não é necessária, pois o ASP.NET Core serve o frontend diretamente.

---

# Executando a versão `.exe`

O projeto pode ser publicado como uma aplicação Windows x64 independente.

Para gerar o executável:

```powershell
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true /p:IncludeNativeLibrariesForSelfExtract=true
```

O resultado será gerado em:

```text
backend\ProfAssistenc.Api\bin\Release\net10.0\win-x64\publish\
```

O arquivo principal será:

```text
ProfAssistenc.Api.exe
```

---

## Configuração da versão `.exe`

O executável precisa de uma API Key própria do Gemini.

Na mesma pasta do `.exe`, mantenha:

```text
publish/
├── ProfAssistenc.Api.exe
├── appsettings.json
├── appsettings.Local.json
└── wwwroot/
```

O `appsettings.Local.json` deve conter:

```json
{
  "Gemini": {
    "ApiKey": "SUA_CHAVE_DA_API_GEMINI"
  }
}
```

**Não compartilhe esse arquivo publicamente**, pois ele contém sua chave de API.

---

## Executar o `.exe`

Abra o PowerShell na pasta do executável:

```powershell
cd caminho\para\publish
```

Execute:

```powershell
.\ProfAssistenc.Api.exe
```

A aplicação será disponibilizada em:

```text
http://localhost:5000
```

Abra esse endereço no navegador.

---

# GitHub Releases

Os executáveis podem ser distribuídos através da seção **Releases** do GitHub.

Uma Release pode conter:

```text
ProfAssistenc.Api.exe
```

O código-fonte permanece no repositório enquanto o executável fica disponível como artefato da versão publicada.

### Arquivos que NÃO devem ser publicados

Não envie:

```text
appsettings.Local.json
profassistenc.db
```

O banco local contém dados da execução da aplicação e o arquivo de configuração contém a API Key.

Cada usuário deve configurar sua própria chave do Gemini.

---

# Funcionamento

## Nova conversa

Ao enviar a primeira mensagem:

```text
Frontend
   ↓
POST /api/LessonPlan
   ↓
LessonPlanController
   ↓
LessonPlanService
   ↓
AIService
   ↓
Gemini API
```

Após receber a resposta:

1. Uma nova conversa é criada.
2. A mensagem do usuário é armazenada.
3. A resposta da IA é armazenada.
4. O Gemini gera automaticamente um título.
5. O título é salvo no banco.
6. O ID da conversa é retornado ao frontend.

---

## Continuação de conversa

Quando uma mensagem é enviada para uma conversa existente:

```text
Frontend
   ↓
conversation_id
   ↓
LessonPlanController
   ↓
ConversationService
   ↓
SQLite
   ↓
Histórico da conversa
   ↓
AIService
   ↓
Gemini API
```

O histórico armazenado é recuperado e enviado para o Gemini junto com a nova mensagem.

Isso permite que a IA mantenha o contexto da conversa.

---

# Persistência

As conversas e mensagens são armazenadas localmente no SQLite.

### Conversation

Representa uma conversa e possui informações como:

* ID
* título
* identificação da instalação
* data de atualização
* mensagens associadas

### MessageEntity

Representa uma mensagem armazenada no banco.

Possui:

* ID
* ID da conversa
* papel da mensagem
* conteúdo

Os papéis utilizados são:

```text
user
assistant
```

---

# Endpoints principais

| Método   | Endpoint                  | Descrição                                    |
| -------- | ------------------------- | -------------------------------------------- |
| `POST`   | `/api/LessonPlan`         | Envia uma mensagem e gera uma resposta da IA |
| `GET`    | `/api/Conversations`      | Lista as conversas da instalação             |
| `GET`    | `/api/Conversations/{id}` | Consulta uma conversa e suas mensagens       |
| `PATCH`  | `/api/Conversations/{id}` | Atualiza o título de uma conversa            |
| `DELETE` | `/api/Conversations/{id}` | Exclui uma conversa                          |

Os parâmetros e modelos de requisição podem ser consultados através do Swagger.

---

# Atalhos

| Tecla          | Ação                       |
| -------------- | -------------------------- |
| `Enter`        | Envia a mensagem           |
| `Ctrl + Enter` | Insere uma quebra de linha |

---

# Migrations

As migrations do Entity Framework Core são utilizadas para controlar alterações estruturais no banco de dados.

Para criar uma nova migration após alterar os modelos:

```powershell
dotnet ef migrations add NomeDaMigration
```

Para aplicar a migration:

```powershell
dotnet ef database update
```

### Quando uma migration é necessária?

Alterações na estrutura do banco, como:

* criação de uma nova entidade;
* criação de uma nova propriedade persistida;
* alteração de uma coluna;
* alteração de relacionamento entre entidades.

Alterações somente na lógica do programa, como Controllers, Services ou frontend, **não exigem uma nova migration** quando não alteram o modelo do banco.

---

# Limitações

A versão atual possui algumas limitações:

* A aplicação depende da disponibilidade da API do Google Gemini.
* A API está sujeita aos limites de uso e cotas do projeto configurado.
* O banco de dados é local e utiliza SQLite.
* A aplicação foi projetada principalmente para execução local.
* Não há sistema de autenticação de usuários na versão atual.
* A aplicação não possui infraestrutura de produção ou hospedagem em nuvem.
* Cada usuário precisa configurar sua própria API Key do Gemini.

Caso a cota da API seja excedida, o Gemini poderá retornar:

```text
HTTP 429 - Too Many Requests
```

Esse erro indica que o limite de utilização da API foi atingido e não necessariamente representa uma falha do backend.

---

# Desenvolvimento

Para verificar o estado do repositório:

```powershell
git status
```

Para adicionar alterações:

```powershell
git add .
```

Para criar um commit:

```powershell
git commit -m "Descrição da alteração"
```

Para enviar alterações:

```powershell
git push origin backend-profassistenc
```

---

# Colaboradores

| Integrante        | Responsabilidade                                                                    | GitHub                                              |
| ----------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Raycka Castro** | Desenvolvimento do frontend com HTML, CSS e JavaScript                              | [Rayck4dev](https://github.com/Rayck4dev)           |
| **Victor Macedo** | Desenvolvimento do backend com C#, ASP.NET Core, banco de dados e integração com IA | [VictorMacedoCB](https://github.com/VictorMacedoCB) |

---

# Status do projeto

**Versão 1.0.0**

Projeto acadêmico em desenvolvimento.

A versão atual possui:

* Backend ASP.NET Core funcional
* Frontend integrado ao backend
* Persistência de dados com SQLite
* Histórico de conversas
* Criação, edição e exclusão de conversas
* Geração automática de títulos por IA
* Integração com Google Gemini
* Swagger/OpenAPI
* Execução através de `.exe` para Windows x64

---

# Objetivo acadêmico

O projeto foi desenvolvido com o objetivo de aplicar conhecimentos práticos em:

* Desenvolvimento de APIs REST
* C#
* ASP.NET Core
* Entity Framework Core
* Bancos de dados
* SQLite
* Injeção de dependência
* Comunicação HTTP
* Integração com APIs externas
* Inteligência Artificial
* Persistência de dados
* Desenvolvimento frontend
* Integração frontend/backend
* Git e GitHub

Além da construção da aplicação, o projeto busca proporcionar experiência prática no desenvolvimento de uma solução completa, desde a interface do usuário até a comunicação com serviços externos e armazenamento persistente de dados.

---

# Licença

Este projeto foi desenvolvido para fins acadêmicos e de extensão.
