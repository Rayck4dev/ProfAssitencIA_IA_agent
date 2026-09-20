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
	<img src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Google Gemini" />
	<img src="https://img.shields.io/badge/Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black" alt="Swagger" />
</p>

## Sobre o projeto

O **ProfAssistenc IA** é uma aplicação desktop desenvolvida para auxiliar professores no planejamento de aulas e atividades por meio de Inteligência Artificial.

A aplicação oferece uma interface de conversa com um assistente virtual, permitindo enviar solicitações, receber sugestões para o planejamento docente e consultar o histórico das conversas realizadas.

O sistema é dividido em:

* **Frontend:** interface desenvolvida com HTML, CSS e JavaScript.
* **Backend:** API REST desenvolvida em C# com ASP.NET Core e .NET 10.
* **Persistência:** SQLite com Entity Framework Core para armazenamento das conversas e mensagens.
* **Inteligência Artificial:** integração com a API do Google Gemini para geração das respostas e títulos das conversas.

## Funcionalidades

* Conversa com o assistente de planejamento docente.
* Geração de respostas utilizando o contexto das mensagens anteriores.
* Geração automática de títulos para novas conversas utilizando IA.
* Histórico de conversas por instalação.
* Renomeação de conversas.
* Exclusão de conversas.
* Persistência local das conversas em banco SQLite.
* Recuperação das conversas após reiniciar a aplicação.
* Indicador visual do status da API.
* Suporte a fórmulas matemáticas nas respostas.
* Documentação dos endpoints através do Swagger.

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
* Google Gemini API

## Arquitetura

A aplicação utiliza uma arquitetura em que o backend ASP.NET Core também é responsável por servir a interface frontend.

```text
ProfAssistencIA.exe
        │
        ▼
ASP.NET Core
        │
        ├── Frontend
        │
        ├── API REST
        │
        ├── Entity Framework Core
        │
        ├── SQLite
        │
        └── Google Gemini API
```

Durante a execução, a aplicação disponibiliza a interface através do endereço:

```text
http://localhost:5000
```

Ao iniciar o executável, o navegador é aberto automaticamente na aplicação.

## Estrutura do projeto

```text
ProfAssitencIA_IA_agent/
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
│       ├── Data/
│       ├── Entities/
│       ├── Migrations/
│       ├── Models/
│       ├── Services/
│       ├── wwwroot/
│       │   ├── index.html
│       │   ├── css/
│       │   └── js/
│       ├── Program.cs
│       ├── appsettings.json
│       └── ProfAssistenc.Api.csproj
│
└── README.md
```

### Principais diretórios do backend

| Diretório     | Responsabilidade                                     |
| ------------- | ---------------------------------------------------- |
| `Controllers` | Define os endpoints da API                           |
| `Data`        | Configuração e acesso ao banco de dados              |
| `Entities`    | Entidades utilizadas para persistência               |
| `Migrations`  | Histórico das alterações do banco de dados           |
| `Models`      | Modelos utilizados nas requisições e respostas       |
| `Services`    | Regras de negócio e integração com serviços externos |
| `wwwroot`     | Arquivos frontend servidos pelo ASP.NET Core         |

## Pré-requisitos

Para executar o projeto em ambiente de desenvolvimento, é necessário ter instalado:

* [.NET SDK 10](https://dotnet.microsoft.com/download/dotnet/10.0)
* Navegador atualizado
* Chave da API do [Google Gemini](https://ai.google.dev/)

## Configuração da API Gemini

A aplicação utiliza uma chave da API do Google Gemini para gerar as respostas e os títulos das conversas.

Na pasta:

```text
backend/ProfAssistenc.Api/
```

deve existir o arquivo:

```text
appsettings.Local.json
```

Com a seguinte estrutura:

```json
{
  "Gemini": {
    "ApiKey": "SUA_CHAVE_DA_API_GEMINI"
  }
}
```

A aplicação carrega essa configuração automaticamente durante a inicialização.

## Como executar em desenvolvimento

Entre na pasta do backend:

```powershell
cd backend\ProfAssistenc.Api
```

Restaure as dependências:

```powershell
dotnet restore
```

Aplique as migrações do banco:

```powershell
dotnet ef database update
```

Execute a aplicação:

```powershell
dotnet run
```

O backend será iniciado e a aplicação ficará disponível em:

```text
http://localhost:5096
```

O Swagger pode ser acessado em:

```text
http://localhost:5096/swagger
```

Durante o desenvolvimento, o frontend também pode ser executado separadamente utilizando uma extensão como o **Live Server**.

## Executável

O projeto também pode ser publicado como uma aplicação executável para Windows.

Com o projeto configurado, execute:

```powershell
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true /p:IncludeNativeLibrariesForSelfExtract=true
```

O executável será gerado na pasta:

```text
backend\ProfAssistenc.Api\bin\Release\net10.0\win-x64\publish\
```

Ao executar:

```text
ProfAssistenc.Api.exe
```

o servidor ASP.NET Core será iniciado e o navegador será aberto automaticamente na aplicação:

```text
http://localhost:5000
```

## Endpoints principais

| Método   | Endpoint                  | Descrição                                    |
| -------- | ------------------------- | -------------------------------------------- |
| `POST`   | `/api/LessonPlan`         | Envia uma mensagem e gera uma resposta da IA |
| `GET`    | `/api/Conversations`      | Lista as conversas da instalação             |
| `GET`    | `/api/Conversations/{id}` | Consulta uma conversa e suas mensagens       |
| `PATCH`  | `/api/Conversations/{id}` | Atualiza o título de uma conversa            |
| `DELETE` | `/api/Conversations/{id}` | Exclui uma conversa                          |

Os parâmetros das requisições e as respostas dos endpoints podem ser consultados através do Swagger.

## Persistência das conversas

As conversas são armazenadas localmente utilizando **SQLite**.

Cada conversa possui:

* Identificador;
* Título;
* Identificação da instalação;
* Data da última atualização;
* Lista de mensagens.

As mensagens armazenadas possuem:

* Identificador;
* Conversa relacionada;
* Papel da mensagem, como `user` ou `assistant`;
* Conteúdo da mensagem.

Dessa forma, o histórico permanece disponível mesmo após fechar e iniciar novamente a aplicação.

## Fluxo de uma conversa

O funcionamento básico de uma mensagem segue o fluxo:

```text
Professor envia uma mensagem
        ↓
Frontend envia requisição para a API
        ↓
LessonPlanController recebe a requisição
        ↓
ConversationService recupera o histórico
        ↓
LessonPlanService prepara a solicitação
        ↓
AIService envia os dados para o Gemini
        ↓
Gemini gera a resposta
        ↓
Resposta é armazenada no SQLite
        ↓
Frontend exibe a resposta
```

Quando uma nova conversa é criada, o sistema também solicita ao Gemini a geração de um título curto baseado na primeira mensagem.

## Atalhos de teclado

Na interface de conversa:

* `Enter` envia a mensagem.
* `Ctrl + Enter` insere uma nova linha.

## Colaboradores

| Integrante        | Responsabilidade                                                                    | GitHub                                              |
| ----------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Raycka Castro** | Desenvolvimento do frontend com HTML, CSS e JavaScript                              | [Rayck4dev](https://github.com/Rayck4dev)           |
| **Victor Macedo** | Desenvolvimento do backend com C#, ASP.NET Core, banco de dados e integração com IA | [VictorMacedoCB](https://github.com/VictorMacedoCB) |

## Objetivo acadêmico

O **ProfAssistenc IA** foi desenvolvido como projeto acadêmico com o objetivo de aplicar conhecimentos de desenvolvimento de software, desenvolvimento de APIs, persistência de dados e integração com Inteligência Artificial em uma aplicação prática voltada à área da educação.

Além da construção da aplicação, o projeto possibilitou o estudo e aplicação de conceitos como:

* APIs REST;
* Injeção de Dependência;
* Entity Framework Core;
* Banco de dados relacional;
* Persistência de dados;
* Arquitetura de aplicações;
* Integração com APIs externas;
* Processamento de conversas com Inteligência Artificial.

## Licença

Este projeto foi desenvolvido para fins acadêmicos e de extensão.
