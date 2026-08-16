# Help Desk SaaS — Documento Base de Desenvolvimento

## 1. Visão geral

O projeto consiste em uma plataforma de Help Desk para atendimento ao cliente.

O sistema permitirá que **Customers** abram chamados para uma equipe de suporte, enquanto **Agents** trabalham nesses chamados e **Admins** administram usuários, categorias e a operação do sistema.

O objetivo principal do projeto é construir um backend profissional, com foco em:

- API REST
- autenticação e autorização
- modelagem relacional
- regras de negócio
- testes automatizados
- processamento assíncrono
- documentação
- Docker
- CI/CD
- observabilidade
- comunicação em tempo real como evolução do projeto

> O projeto deve priorizar simplicidade e qualidade. Não adicionar tecnologias ou funcionalidades apenas para aumentar a complexidade.

---

## 2. Objetivos do projeto

### Objetivos técnicos

Demonstrar domínio prático de:

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT
- RBAC
- pytest
- Docker
- CI/CD
- Redis
- background jobs
- WebSockets
- logging e observabilidade

### Objetivos de portfólio

O projeto deve ser suficientemente completo para demonstrar capacidade de desenvolvimento de backend compatível com uma evolução de **Junior para Pleno**.

O foco não é criar uma plataforma comercial completa, mas sim um sistema pequeno, consistente e bem projetado.

---

# 3. Escopo do MVP

O MVP deverá conter:

- cadastro de usuários
- login
- autenticação JWT
- controle de acesso por papel
- criação de tickets
- listagem de tickets
- visualização de ticket
- atualização de ticket
- envio de mensagens
- categorias
- atribuição de agente
- alteração de status
- alteração de prioridade
- paginação
- filtros
- ordenação
- testes automatizados
- documentação OpenAPI
- Docker
- CI

Funcionalidades avançadas serão adicionadas somente após o MVP estar estável.

---

# 4. Papéis do sistema

## 4.1 Customer

O Customer representa o cliente que utiliza o serviço de suporte.

Permissões:

- criar tickets
- visualizar seus próprios tickets
- visualizar mensagens dos próprios tickets
- enviar mensagens nos próprios tickets

Não pode:

- visualizar tickets de outros clientes
- alterar prioridade
- atribuir agentes
- alterar o status do ticket
- administrar usuários

---

## 4.2 Agent

O Agent representa um membro da equipe de suporte.

Permissões:

- visualizar tickets que pode atender
- visualizar detalhes dos tickets
- responder tickets
- alterar status
- alterar prioridade
- assumir tickets

Não pode:

- gerenciar usuários
- alterar permissões
- administrar configurações globais

---

## 4.3 Admin

O Admin possui controle administrativo do sistema.

Permissões:

- todas as permissões de Agent
- visualizar todos os tickets
- atribuir tickets a agentes
- gerenciar usuários
- gerenciar categorias
- visualizar métricas administrativas

---

# 5. Fluxo principal

```text
Customer
   |
   | cria ticket
   v
OPEN
   |
   | Agent assume
   v
IN_PROGRESS
   |
   | Agent resolve
   v
RESOLVED
   |
   v
CLOSED
```

Fluxo de comunicação:

```text
Customer
   |
   | mensagem
   v
Ticket
   |
   v
Agent
   |
   | resposta
   v
Customer
```

No MVP, a comunicação pode utilizar REST.

WebSocket será uma evolução posterior.

---

# 6. Modelo de domínio

## User

Representa qualquer usuário do sistema.

Campos sugeridos:

```text
id
name
email
password_hash
role
is_active
created_at
updated_at
```

Roles:

```text
CUSTOMER
AGENT
ADMIN
```

---

## Ticket

Representa um chamado de suporte.

Campos sugeridos:

```text
id
title
description
status
priority
customer_id
agent_id
category_id
created_at
updated_at
resolved_at
closed_at
```

### Status

```text
OPEN
IN_PROGRESS
RESOLVED
CLOSED
```

### Prioridade

```text
LOW
MEDIUM
HIGH
URGENT
```

---

## Message

Representa uma mensagem dentro de um ticket.

Campos sugeridos:

```text
id
ticket_id
author_id
content
created_at
updated_at
```

---

## Category

Representa a categoria do ticket.

Campos sugeridos:

```text
id
name
description
created_at
updated_at
```

Exemplos:

```text
Technical
Billing
Account
General
```

---

## TicketEvent

Entidade opcional para auditoria.

Representa eventos importantes ocorridos em um ticket.

Campos sugeridos:

```text
id
ticket_id
actor_id
event_type
metadata
created_at
```

Exemplos:

```text
TICKET_CREATED
AGENT_ASSIGNED
STATUS_CHANGED
PRIORITY_CHANGED
MESSAGE_ADDED
TICKET_RESOLVED
TICKET_CLOSED
```

Essa entidade pode ser adicionada após o MVP.

---

# 7. Relacionamentos

```text
User 1 ───── N Ticket
User 1 ───── N Message
Ticket 1 ─── N Message
Category 1 ─ N Ticket
Ticket 1 ─── N TicketEvent
```

Relações principais:

```text
Ticket.customer_id → User.id
Ticket.agent_id    → User.id
Ticket.category_id → Category.id

Message.ticket_id  → Ticket.id
Message.author_id  → User.id
```

---

# 8. API

A API deverá utilizar versionamento:

```text
/api/v1
```

## Authentication

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
```

---

## Users

```text
GET   /api/v1/users/me
GET   /api/v1/users
GET   /api/v1/users/{user_id}
PATCH /api/v1/users/{user_id}
```

Os endpoints administrativos devem possuir autorização adequada.

---

## Tickets

```text
POST   /api/v1/tickets
GET    /api/v1/tickets
GET    /api/v1/tickets/{ticket_id}
PATCH  /api/v1/tickets/{ticket_id}
```

---

## Ticket messages

```text
GET  /api/v1/tickets/{ticket_id}/messages
POST /api/v1/tickets/{ticket_id}/messages
```

---

## Ticket actions

```text
POST  /api/v1/tickets/{ticket_id}/assign
PATCH /api/v1/tickets/{ticket_id}/status
PATCH /api/v1/tickets/{ticket_id}/priority
```

---

## Categories

```text
GET    /api/v1/categories
POST   /api/v1/categories
PATCH  /api/v1/categories/{category_id}
DELETE /api/v1/categories/{category_id}
```

A criação, alteração e exclusão de categorias devem ser restritas ao Admin.

---

# 9. Listagem de tickets

A listagem deve suportar paginação, filtros e ordenação.

Exemplo:

```text
GET /api/v1/tickets?
    status=OPEN
    &priority=HIGH
    &category_id=2
    &agent_id=10
    &page=1
    &limit=20
    &sort=-created_at
```

Filtros iniciais:

- status
- priority
- category
- agent
- customer
- created_at

Ordenação:

- created_at
- updated_at
- priority

---

# 10. Regras de negócio

## Tickets

1. Um Customer só pode visualizar seus próprios tickets.
2. Um Customer não pode atribuir um ticket a um Agent.
3. Um Customer não pode alterar a prioridade.
4. Um Customer não pode alterar o status.
5. Um Agent pode assumir um ticket.
6. Um Agent pode responder tickets.
7. Um Agent pode alterar status e prioridade.
8. Um Admin pode atribuir tickets.
9. Um ticket fechado não deve receber novas mensagens.
10. Um ticket resolvido pode possuir uma regra definida posteriormente para reabertura.
11. Um ticket deve possuir uma categoria.
12. O Agent atribuído deve possuir role `AGENT` ou `ADMIN`.

As regras devem ser implementadas na camada de domínio/serviço, e não apenas no endpoint.

---

# 11. Autenticação

A autenticação deverá utilizar JWT.

Fluxo:

```text
Login
  |
  v
Access Token + Refresh Token
  |
  v
API Request
  |
  v
JWT validation
  |
  v
Authorization
```

Requisitos:

- senha armazenada somente como hash
- access token com expiração curta
- refresh token com expiração maior
- validação de usuário ativo
- autorização baseada em role

---

# 12. Estrutura inicial do projeto

Sugestão:

```text
app/
├── main.py
│
├── api/
│   ├── dependencies.py
│   └── v1/
│       ├── auth.py
│       ├── users.py
│       ├── tickets.py
│       ├── messages.py
│       └── categories.py
│
├── core/
│   ├── config.py
│   ├── security.py
│   └── logging.py
│
├── db/
│   ├── session.py
│   └── base.py
│
├── models/
│   ├── user.py
│   ├── ticket.py
│   ├── message.py
│   └── category.py
│
├── schemas/
│   ├── auth.py
│   ├── user.py
│   ├── ticket.py
│   ├── message.py
│   └── category.py
│
├── services/
│   ├── auth.py
│   ├── ticket.py
│   ├── message.py
│   └── user.py
│
└── repositories/
    ├── ticket.py
    ├── message.py
    └── user.py
```

A estrutura pode ser alterada conforme o projeto evoluir. O objetivo é manter responsabilidades bem separadas, e não seguir uma arquitetura específica por obrigação.

---

# 13. Banco de dados

Banco principal:

```text
PostgreSQL
```

ORM:

```text
SQLAlchemy
```

Migrations:

```text
Alembic
```

Requisitos:

- foreign keys
- indexes onde fizer sentido
- unique constraints
- not null constraints
- timestamps
- transações
- migrations versionadas

Evitar criar índices indiscriminadamente. Cada índice deve possuir uma justificativa relacionada às consultas realizadas pela aplicação.

---

# 14. Testes

Framework:

```text
pytest
```

Tipos de teste:

### Unitários

Testar regras isoladas:

```text
- validação de transição de status
- permissões
- regras de negócio
```

### Integração

Testar:

```text
API + PostgreSQL
```

Exemplos:

```text
POST /tickets
GET /tickets
POST /tickets/{id}/messages
```

### Autenticação

Testar:

```text
login válido
login inválido
token expirado
token inválido
role sem permissão
```

Objetivo inicial:

> Priorizar testes de comportamento e regras de negócio, não simplesmente buscar uma porcentagem alta de coverage.

---

# 15. Tratamento de erros

A API deverá possuir respostas consistentes.

Exemplo:

```json
{
  "detail": "Ticket not found"
}
```

Erros esperados:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
500 Internal Server Error
```

Erros internos não devem expor stack traces ou informações sensíveis ao cliente.

---

# 16. Logging

Implementar logging estruturado.

Eventos importantes:

```text
User authenticated
Ticket created
Ticket assigned
Ticket status changed
Message created
Unexpected exception
```

Nunca registrar:

- senhas
- tokens
- secrets
- informações sensíveis desnecessárias

---

# 17. Redis

Redis não faz parte do MVP inicial.

Será introduzido quando existir uma necessidade clara.

Possíveis usos:

- cache
- rate limiting
- background jobs
- WebSocket pub/sub
- sessões temporárias

Não utilizar Redis simplesmente para adicionar uma tecnologia ao projeto.

---

# 18. Background Jobs

Após o MVP, implementar tarefas assíncronas.

Primeiro caso de uso:

```text
Ticket criado
     |
     v
Background Job
     |
     v
Enviar notificação
```

Possíveis tecnologias:

- ARQ
- Celery
- Redis Queue

Escolher uma e documentar a decisão.

---

# 19. WebSocket

WebSocket será uma funcionalidade de evolução.

Endpoint possível:

```text
WS /api/v1/tickets/{ticket_id}/ws
```

Objetivo:

- receber novas mensagens em tempo real
- notificar mudança de status
- notificar atribuição
- futuramente indicar presença/digitação

Importante:

> REST continuará sendo utilizado para operações persistentes. WebSocket será utilizado principalmente para comunicação/eventos em tempo real.

Fluxo:

```text
Agent
  |
  | POST /messages
  v
FastAPI
  |
  ├── PostgreSQL
  |
  └── WebSocket event
          |
          v
       Customer
```

---

# 20. Docker

O projeto deverá possuir:

```text
Dockerfile
docker-compose.yml
```

Ambiente local:

```text
FastAPI
PostgreSQL
```

Posteriormente:

```text
FastAPI
PostgreSQL
Redis
Worker
```

Variáveis de ambiente deverão ser utilizadas para configurações.

Nunca versionar secrets.

---

# 21. CI/CD

Pipeline inicial:

```text
Push
  |
  v
Lint
  |
  v
Type Check
  |
  v
Tests
  |
  v
Build
```

Posteriormente:

```text
Push main
    |
    v
Tests
    |
    v
Docker Build
    |
    v
Deploy
```

---

# 22. Documentação

A API deverá possuir documentação OpenAPI/Swagger.

Além disso, o README deverá explicar:

- objetivo do projeto
- funcionalidades
- arquitetura
- stack
- como executar localmente
- variáveis de ambiente
- como executar testes
- como executar migrations
- decisões arquiteturais
- exemplos de uso da API

---

# 23. Roadmap

## Milestone 1 — Setup

- [ ] Criar projeto FastAPI
- [ ] Configurar Poetry/uv
- [ ] Configurar Ruff
- [ ] Configurar PostgreSQL
- [ ] Configurar SQLAlchemy
- [ ] Configurar Alembic
- [ ] Configurar Docker
- [ ] Configurar pytest

## Milestone 2 — Authentication

- [ ] User model
- [ ] Register
- [ ] Login
- [ ] Password hashing
- [ ] JWT access token
- [ ] Refresh token
- [ ] RBAC

## Milestone 3 — Tickets

- [ ] Ticket model
- [ ] Category model
- [ ] Create ticket
- [ ] Get ticket
- [ ] List tickets
- [ ] Pagination
- [ ] Filters
- [ ] Sorting

## Milestone 4 — Support workflow

- [ ] Assign agent
- [ ] Change status
- [ ] Change priority
- [ ] Ticket messages
- [ ] Permission rules
- [ ] Business rules

## Milestone 5 — Quality

- [ ] Unit tests
- [ ] Integration tests
- [ ] Error handling
- [ ] Logging
- [ ] OpenAPI documentation
- [ ] CI

## Milestone 6 — Async

- [ ] Redis
- [ ] Background worker
- [ ] Email notification
- [ ] Retry mechanism

## Milestone 7 — Real-time

- [ ] WebSocket
- [ ] Real-time messages
- [ ] Real-time ticket events
- [ ] Connection handling

## Milestone 8 — Production

- [ ] Production Docker image
- [ ] Deploy
- [ ] Environment configuration
- [ ] Health check
- [ ] Metrics
- [ ] Monitoring

---

# 24. Definition of Done

Uma funcionalidade só deve ser considerada concluída quando:

- [ ] implementação concluída
- [ ] validação implementada
- [ ] autorização implementada
- [ ] tratamento de erros implementado
- [ ] testes relevantes adicionados
- [ ] documentação atualizada
- [ ] lint passando
- [ ] type checking passando
- [ ] migrations atualizadas quando necessário

---

# 25. Princípios do projeto

1. **Keep it simple.**
2. Não adicionar tecnologia sem necessidade.
3. Priorizar regras de negócio claras.
4. Preferir código simples e legível.
5. Testar comportamento importante.
6. Não criar abstrações prematuramente.
7. Não utilizar microservices.
8. Começar com um monólito modular.
9. Evoluir a arquitetura conforme surgirem necessidades reais.
10. Toda decisão arquitetural relevante deve ser justificável.

---

# 26. Stack inicial

```text
Language: Python
Framework: FastAPI
Database: PostgreSQL
ORM: SQLAlchemy
Migrations: Alembic
Validation: Pydantic
Authentication: JWT
Testing: pytest
Lint/Formatting: Ruff
Containerization: Docker
CI/CD: GitHub Actions
Cache/Queue: Redis (fase posterior)
Background Jobs: a definir
Real-time: WebSocket (fase posterior)
```

---

# 27. Resultado esperado

Ao final, o projeto deverá representar uma aplicação backend completa, porém de escopo controlado.

O foco do portfólio será demonstrar que o desenvolvedor consegue:

- projetar uma API
- modelar um banco relacional
- implementar autenticação
- controlar permissões
- implementar regras de negócio
- escrever testes
- trabalhar com processamento assíncrono
- documentar uma aplicação
- containerizar o projeto
- configurar CI/CD
- realizar deploy
- explicar as decisões técnicas tomadas

O objetivo não é ter o maior número possível de tecnologias.

O objetivo é conseguir explicar **por que cada parte existe, quais problemas resolve e quais trade-offs foram considerados**.
