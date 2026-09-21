
# ProfAssistenc IA
 <p align="center">
  <img src=./assets/graduation-hat-logo.png>
</p>

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
</p>

## Sobre o projeto

O **ProfAssistenc IA** é uma aplicação desktop criada para apoiar professores no planejamento de aulas e atividades. A plataforma oferece uma interface de conversa com inteligência artificial, permitindo fazer perguntas, gerar sugestões de planejamento e consultar o histórico de conversas.

O sistema é dividido em:

- **Frontend:** interface responsiva desenvolvida com HTML, CSS e JavaScript.
- **Backend:** API REST desenvolvida em C# com ASP.NET Core e .NET 10.
- **Persistência:** SQLite com Entity Framework Core para armazenar conversas e mensagens.
- **Inteligência artificial:** integração com a API do Google Gemini para gerar respostas e títulos para as conversas.

## Funcionalidades

- Conversa com o assistente de planejamento docente.
- Geração de respostas com contexto das mensagens anteriores.
- Criação automática de títulos para novas conversas.
- Histórico de conversas por instalação do navegador.
- Renomeação e exclusão de conversas.
- Persistência local das conversas em banco SQLite.
- Indicador visual do status da API.
- Documentação dos endpoints pelo Swagger.

## Tecnologias

### Frontend

- HTML5
- CSS3
- JavaScript
- Tailwind CSS via CDN
- Lucide Icons
- KaTeX para renderização de fórmulas matemáticas

### Backend

- C#
- ASP.NET Core Web API
- .NET 10
- Entity Framework Core
- SQLite
- Swagger/OpenAPI
- Google Gemini API

## Estrutura do projeto

```text
ProfAssitencIA/
├── assets/                       # Imagens e recursos visuais
├── frontend/
│   ├── index.html                # Página principal
│   ├── css/style.css             # Estilos da aplicação
│   └── js/app.js                 # Lógica e integração com a API
├── backend/
│   └── ProfAssistenc.Api/
│       ├── Controllers/          # Endpoints da API
│       ├── Data/                 # Contexto do banco de dados
│       ├── Entities/             # Entidades persistidas
│       ├── Migrations/           # Migrações do Entity Framework
│       ├── Models/               # Modelos de requisição e resposta
│       └── Services/             # Regras de negócio e integração com IA
└── README.md
```

## Pré-requisitos

- [.NET SDK 10](https://dotnet.microsoft.com/download/dotnet/10.0)
- Um navegador atualizado
- Uma chave da API do [Google Gemini](https://ai.google.dev/)
- Uma extensão ou servidor local para servir o frontend, como o **Live Server** do VS Code

## Como executar

### 1. Configurar a chave da API Gemini

No terminal, entre na pasta do backend e configure a chave usando o User Secrets do .NET:

```powershell
cd backend\ProfAssistenc.Api
dotnet user-secrets set "Gemini:ApiKey" "SUA_CHAVE_DA_API_GEMINI"
```

Não envie a chave da API para o repositório.

### 2. Executar o backend

Ainda na pasta `backend\ProfAssistenc.Api`, execute:

```powershell
dotnet restore
dotnet ef database update
dotnet run --launch-profile http
```

Se o comando `dotnet ef` não estiver disponível, instale a ferramenta uma vez:

```powershell
dotnet tool install --global dotnet-ef
```

A API ficará disponível em:

- API: `http://localhost:5096`
- Swagger: `http://localhost:5096/swagger`

### 3. Executar o frontend

Na raiz do projeto, abra a pasta `frontend` com o Live Server. O endereço padrão esperado pela API é:

```text
http://127.0.0.1:5500
```

Depois, acesse a página aberta pelo Live Server no navegador. O frontend já está configurado para consumir a API em `http://localhost:5096`.

> Caso utilize outra porta ou endereço para o frontend, atualize a política de CORS em `backend/ProfAssistenc.Api/Program.cs`.

## Endpoints principais

| Método   | Endpoint                  | Descrição                                    |
| -------- | ------------------------- | -------------------------------------------- |
| `POST`   | `/api/LessonPlan`         | Envia uma mensagem e gera uma resposta da IA |
| `GET`    | `/api/Conversations`      | Lista as conversas da instalação             |
| `GET`    | `/api/Conversations/{id}` | Consulta uma conversa e suas mensagens       |
| `PATCH`  | `/api/Conversations/{id}` | Atualiza o título de uma conversa            |
| `DELETE` | `/api/Conversations/{id}` | Exclui uma conversa                          |

Os parâmetros necessários e os exemplos de requisição podem ser consultados no Swagger.

## Colaboradores

| Integrante        | Responsabilidade                                                                    | GitHub                                              |
| ----------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Raycka Castro** | Desenvolvimento do frontend com HTML, CSS e JavaScript                              | [Rayck4dev](https://github.com/Rayck4dev)           |
| **Victor Macedo** | Desenvolvimento do backend com C#, ASP.NET Core, banco de dados e integração com IA | [VictorMacedoCB](https://github.com/VictorMacedoCB) |

## Licença

Este projeto foi desenvolvido para fins acadêmicos e de extensão.
