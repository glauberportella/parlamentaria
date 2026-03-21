# Parlamentaria — Arquitetura do Software

> Plataforma agêntica que conecta eleitores às decisões legislativas da Câmara dos Deputados
> do Brasil através de agentes de IA conversacionais via Telegram.

---

## 1. Visão Geral

**Parlamentaria** é uma plataforma **agent-first** que democratiza o acesso à atividade legislativa brasileira. O eleitor interage com um agente de IA conversacional — o _Parlamentar de IA_ — diretamente via **Telegram** (canal primário), sem necessidade de frontend web.

O sistema monitora proposições legislativas, analisa textos com IA, coleta votação popular dos eleitores e compara com votações reais da Câmara, fechando o ciclo de democracia participativa.

---

## 2. Arquitetura Macro — Visão de Alto Nível

```mermaid
graph TD
    subgraph Entrada ["ENTRADA — Eleitores"]
        TG["👤 Eleitor<br/>(Telegram)"]
        WA["👤 Eleitor<br/>(WhatsApp — futuro)"]
    end

    subgraph Gateway ["Channel Gateway"]
        TGA["TelegramAdapter<br/>(python-telegram-bot)"]
        WAA["WhatsAppAdapter<br/>(placeholder)"]
    end

    subgraph Core ["Núcleo da Plataforma"]
        ADK["Agent Orchestrator<br/>(Google ADK Runner)"]
        FAPI["FastAPI<br/>(Backend API)"]
        SVC["Services<br/>(Lógica de Negócio)"]
        REPO["Repositories<br/>(Data Access)"]
    end

    subgraph Infra ["Infraestrutura"]
        PG[("PostgreSQL 16<br/>+ pgvector")]
        RD["Redis 7<br/>(Cache + Broker)"]
        CLR["Celery<br/>(Workers + Beat)"]
    end

    subgraph External ["APIs Externas"]
        API["API Dados Abertos<br/>Câmara dos Deputados"]
        LLM["LLM Provider<br/>(Gemini / LiteLLM)"]
    end

    subgraph Publication ["Camada de Publicação"]
        RSS["RSS/Atom Feed"]
        WHout["Webhooks de Saída"]
        DASH["Dashboard<br/>(Next.js — Parlamentar)"]
    end

    TG <--> TGA
    WA <--> WAA
    TGA --> ADK
    WAA --> ADK
    ADK --> SVC
    FAPI --> SVC
    SVC --> REPO
    REPO --> PG
    SVC --> RD
    CLR --> SVC
    CLR --> RD
    SVC --> API
    ADK --> LLM
    SVC --> Publication
    RSS --> Parl["Parlamentar<br/>(assinante)"]
    WHout --> Ext["Sistemas Externos"]
    DASH --> FAPI

    style Entrada fill:#e3f2fd,stroke:#1565c0
    style Gateway fill:#e1f5fe,stroke:#0288d1
    style Core fill:#fff3e0,stroke:#ef6c00
    style Infra fill:#e8f5e9,stroke:#2e7d32
    style External fill:#f3e5f5,stroke:#6a1b9a
    style Publication fill:#fce4ec,stroke:#c62828
```

---

## 3. Ciclo Completo da Democracia Participativa

O sistema fecha um ciclo completo entre eleitor e parlamentar:

```mermaid
graph LR
    E["👤 Eleitor<br/>(via chat)"] -->|vota| VP["Voto<br/>Popular"]
    VP --> C["Consolidação<br/>(tempo real)"]
    C --> P["Publicação<br/>(RSS + Webhooks)"]
    P --> Parl["👔 Parlamentar<br/>(Dashboard/RSS)"]
    VR["Votação Real<br/>(sync API Câmara)"] --> Comp["Comparativo<br/>Pop vs Real"]
    Comp --> FB["Feedback<br/>(ao eleitor)"]
    FB --> E

    style E fill:#e3f2fd,stroke:#1565c0
    style Parl fill:#e8f5e9,stroke:#2e7d32
    style Comp fill:#fff3e0,stroke:#ef6c00
```

1. **Eleitor vota** via Telegram em proposições legislativas.
2. **Votos são consolidados** em tempo real (SIM/NÃO/ABSTENÇÃO).
3. **Resultado publicado** via RSS Feed e Webhooks para parlamentares.
4. **Votação real** é sincronizada da API da Câmara.
5. **Comparativo** é gerado automaticamente (alinhamento 0%–100%).
6. **Feedback** é entregue ao eleitor via chat.

---

## 4. Camadas Arquiteturais (Layered + Agent Architecture)

```mermaid
block-beta
    columns 1
    CH["Channel Layer — Telegram, WhatsApp (futuro)"]
    AG["Agent Layer — Google ADK (LlmAgents + FunctionTools)"]
    API["API Layer — FastAPI (Webhooks, Admin, RSS, Health)"]
    SV["Service Layer — Lógica de Negócio (Use Cases)"]
    PB["Publication Layer — RSS Feed, Webhooks, Dashboard"]
    RP["Repository Layer — Data Access (SQLAlchemy 2.0 async)"]
    TK["Task Layer — Celery (Sync, Notificações, Embeddings)"]
    IN["Integration Layer — Cliente HTTP (API Câmara)"]
    DM["Domain Layer — Modelos, Enums, Value Objects"]

    style CH fill:#e3f2fd,stroke:#1565c0
    style AG fill:#e8eaf6,stroke:#283593
    style API fill:#f1f8e9,stroke:#558b2f
    style SV fill:#fff3e0,stroke:#ef6c00
    style PB fill:#fce4ec,stroke:#c62828
    style RP fill:#e8f5e9,stroke:#2e7d32
    style TK fill:#f9fbe7,stroke:#827717
    style IN fill:#f3e5f5,stroke:#6a1b9a
    style DM fill:#fffde7,stroke:#f57f17
```

### 4.1 Descrição de Cada Camada

| Camada | Responsabilidade | Tecnologia |
|--------|------------------|------------|
| **Channel** | Adapters de mensageria (Telegram, WhatsApp) | python-telegram-bot |
| **Agent** | Agentes conversacionais multi-agent | Google ADK (LlmAgent) |
| **API** | Webhooks, endpoints admin, RSS, health | FastAPI |
| **Service** | Lógica de negócio, validações, orquestração | Python async |
| **Publication** | Saída para parlamentares (RSS, Webhooks, Dashboard) | feedgen, httpx |
| **Repository** | Abstração de acesso a dados | SQLAlchemy 2.0 async |
| **Task** | Jobs assíncronos e agendados | Celery + Redis |
| **Integration** | Clientes HTTP para APIs externas | httpx + tenacity |
| **Domain** | Entidades, enums, value objects | SQLAlchemy ORM |

---

## 5. Arquitetura Multi-Agent (Google ADK)

O sistema utiliza o padrão **Multi-Agent** do Google ADK, com um agente raiz orquestrando sub-agentes especializados:

```mermaid
graph TD
    Root["🧠 ParlamentarAgent<br/>(Root — Orquestrador)<br/>model: gemini-2.0-flash"]

    Root --> PA["📜 ProposicaoAgent<br/>Busca, resumo e análise<br/>de proposições legislativas"]
    Root --> VA["🗳️ VotacaoAgent<br/>Coleta voto popular,<br/>resultados e histórico"]
    Root --> DA["👤 DeputadoAgent<br/>Perfil de deputados,<br/>despesas e votações"]
    Root --> EA["📋 EleitorAgent<br/>Cadastro, verificação,<br/>preferências e notificações"]
    Root --> PubA["📊 PublicacaoAgent<br/>Comparativo pop vs real,<br/>status RSS e feedback"]

    subgraph Tools ["FunctionTools"]
        T1["camara_tools<br/>buscar_proposicoes<br/>buscar_eventos_pauta<br/>consultar_agenda"]
        T2["db_tools<br/>consultar_proposicao_local<br/>listar_proposicoes_local"]
        T3["rag_tools<br/>busca_semantica_proposicoes<br/>obter_estatisticas_rag"]
        T4["votacao_tools<br/>registrar_voto<br/>obter_resultado<br/>historico_votos"]
        T5["notification_tools<br/>configurar_frequencia<br/>verificar_notificacoes"]
        T6["publicacao_tools<br/>obter_comparativo<br/>status_publicacao<br/>listar_comparativos"]
    end

    PA -.-> T1
    PA -.-> T2
    PA -.-> T3
    VA -.-> T4
    EA -.-> T5
    PubA -.-> T6

    style Root fill:#4285f4,color:#fff,stroke:#1a73e8
    style PA fill:#e8eaf6,stroke:#283593
    style VA fill:#e8eaf6,stroke:#283593
    style DA fill:#e8eaf6,stroke:#283593
    style EA fill:#e8eaf6,stroke:#283593
    style PubA fill:#e8eaf6,stroke:#283593
    style Tools fill:#f1f3f4,stroke:#dadce0
```

### 5.1 Fluxo de Mensagem (End-to-End)

```mermaid
sequenceDiagram
    participant E as 👤 Eleitor (Telegram)
    participant TG as Telegram Bot API
    participant WH as FastAPI /webhook/telegram
    participant TA as TelegramAdapter
    participant RN as ADK Runner
    participant RA as ParlamentarAgent (Root)
    participant SA as Sub-Agent Especializado
    participant T as FunctionTool
    participant DB as PostgreSQL

    E->>TG: Envia mensagem
    TG->>WH: webhook POST (payload JSON)
    WH->>TA: process_incoming(payload)
    TA->>RN: run_agent(user_id, session_id, text)
    RN->>RA: Delega mensagem
    RA->>SA: transfer_to_agent (LLM decide)
    SA->>T: Chama FunctionTool
    T->>DB: Query / Insert
    DB-->>T: Resultado
    T-->>SA: Dict com dados
    SA-->>RA: Resposta formatada
    RA-->>RN: Texto final
    RN-->>TA: response_text
    TA->>TG: send_message(chat_id, text)
    TG->>E: Resposta no chat
```

---

## 6. Fluxo de Dados — Sincronização com API Câmara

```mermaid
flowchart LR
    subgraph Celery ["Celery Beat (agendado)"]
        BEAT["⏰ Scheduler<br/>2x/dia"]
    end

    subgraph Tasks ["Celery Workers"]
        T1["sync_proposicoes"]
        T2["sync_votacoes"]
        T3["sync_deputados"]
        T4["sync_partidos"]
        T5["sync_eventos"]
    end

    subgraph API ["API Câmara"]
        EP["Dados Abertos<br/>v2"]
    end

    subgraph DB ["PostgreSQL"]
        PG[("Tabelas<br/>proposicoes<br/>votacoes<br/>deputados<br/>partidos<br/>eventos")]
    end

    subgraph Post ["Pós-Sync"]
        EMB["generate_embeddings<br/>(pgvector)"]
        ANA["generate_analysis<br/>(LLM)"]
        COMP["gerar_comparativos"]
        NOT["notificar_eleitores"]
    end

    BEAT --> T1 & T2 & T3 & T4 & T5
    T1 & T2 & T3 & T4 & T5 --> EP
    EP --> T1 & T2 & T3 & T4 & T5
    T1 & T2 & T3 & T4 & T5 --> PG
    PG --> EMB & ANA & COMP & NOT

    style Celery fill:#f9fbe7,stroke:#827717
    style Tasks fill:#fff3e0,stroke:#ef6c00
    style API fill:#e8f5e9,stroke:#2e7d32
    style DB fill:#e3f2fd,stroke:#1565c0
    style Post fill:#f3e5f5,stroke:#6a1b9a
```

---

## 7. Pipeline RAG (Busca Semântica)

O sistema utiliza **RAG (Retrieval-Augmented Generation)** para busca semântica sobre proposições:

```mermaid
flowchart LR
    subgraph Indexação ["Pipeline de Indexação"]
        SYNC["Sync API Câmara"] --> PROP[("Proposição")]
        PROP --> CHUNK["Chunking<br/>(ementa, resumo, análise)"]
        CHUNK --> HASH["SHA-256<br/>(deduplicação)"]
        HASH --> EMB["Embedding<br/>(gemini-embedding-001<br/>3072 dims)"]
        EMB --> PGV[("pgvector<br/>(document_chunks)")]
    end

    subgraph Busca ["Pipeline de Busca"]
        Q["Pergunta do eleitor"] --> QEMB["Embedding<br/>da query"]
        QEMB --> COS["Cosine<br/>Similarity"]
        PGV --> COS
        COS --> TOP["Top-K<br/>resultados"]
        TOP --> AGT["Agente responde<br/>com contexto"]
    end

    style Indexação fill:#e8f5e9,stroke:#2e7d32
    style Busca fill:#e3f2fd,stroke:#1565c0
```

**Tipos de chunk indexados:**
- `ementa` — Texto da ementa da proposição
- `resumo_ia` — Resumo acessível gerado por IA
- `analise_resumo_leigo` — Análise simplificada
- `analise_impacto` — Análise de impacto esperado
- `analise_argumentos` — Argumentos a favor e contra
- `tramitacao` — Última tramitação

---

## 8. Infraestrutura e Deploy

### 8.1 Serviços Docker

```mermaid
graph TB
    subgraph Docker ["Docker Compose"]
        BE["backend<br/>(FastAPI + Uvicorn)<br/>:8000"]
        DASH["dashboard<br/>(Next.js)<br/>:3000"]
        DB[("db<br/>(pgvector/pgvector:pg16)<br/>:5432")]
        RD["redis<br/>(redis:7-alpine)<br/>:6379"]
        CW["celery-worker<br/>(2 workers)"]
        CB["celery-beat<br/>(scheduler)"]
    end

    BE --> DB
    BE --> RD
    DASH --> BE
    CW --> DB
    CW --> RD
    CB --> RD

    style Docker fill:#f5f5f5,stroke:#616161
    style DB fill:#e3f2fd,stroke:#1565c0
    style RD fill:#ffebee,stroke:#c62828
```

| Serviço | Imagem/Build | Porta | Função |
|---------|-------------|-------|--------|
| **backend** | `./backend` (Dockerfile) | 8000 | API FastAPI, webhooks, ADK |
| **dashboard** | `./dashboard` (Next.js) | 3000 | Dashboard para parlamentares |
| **db** | `pgvector/pgvector:pg16` | 5432 | PostgreSQL + pgvector |
| **redis** | `redis:7-alpine` | 6379 | Cache, broker Celery, sessões |
| **celery-worker** | `./backend` | — | Processamento assíncrono |
| **celery-beat** | `./backend` | — | Agendamento de tasks |

### 8.2 Volumes Persistentes

- `pgdata` — Dados do PostgreSQL
- `redisdata` — Dados do Redis (AOF)

---

## 9. Tech Stack

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| **Agent Framework** | Google ADK | latest |
| **Backend API** | Python + FastAPI | 3.12+ |
| **Banco de Dados** | PostgreSQL + pgvector | 16+ |
| **ORM** | SQLAlchemy (async) | 2.0 |
| **Migrations** | Alembic | — |
| **Cache / Broker** | Redis | 7 |
| **Task Queue** | Celery | 5.x |
| **Canal Primário** | python-telegram-bot | — |
| **LLM** | Google Gemini (via ADK) | gemini-2.0-flash |
| **Embeddings** | gemini-embedding-001 | 3072 dims |
| **Dashboard** | Next.js | 15+ |
| **Container** | Docker + Docker Compose | — |
| **CI/CD** | GitHub Actions | — |
| **Linting** | Ruff | — |

---

## 10. Design Patterns

| Pattern | Onde | Justificativa |
|---------|------|---------------|
| **Multi-Agent** | Google ADK | Agentes especializados com delegação inteligente |
| **Channel Adapter** | `channels/` | Canal de mensageria desacoplado da lógica |
| **Repository** | `repositories/` | Abstração de persistência, testabilidade |
| **Service** | `services/` | Separação de regras de negócio |
| **FunctionTool** | `agents/tools/` | Funções Python como capacidades dos agentes |
| **Agent-as-a-Tool** | Sub-agents ADK | Delegação especializada por transferência |
| **Factory** | Channel adapters | Instanciação flexível por configuração |
| **DTO** | `schemas/` | Validação com Pydantic, transferência entre camadas |
| **Observer/Event** | Notificações | Desacoplamento entre sync e notificação |
| **Pub/Sub** | RSS + Webhooks | Parlamentares assinam resultados |
| **Comparator** | Comparativo service | Feedback transparente pop vs real |
| **Savepoint** | Sync batch | Isolamento de erros em operações em lote |

---

## 11. Estrutura de Diretórios

```
parlamentaria/
├── agents/                           # Google ADK — Agentes de IA
│   ├── parlamentar/
│   │   ├── agent.py                  # ParlamentarAgent (root)
│   │   ├── prompts.py                # System instructions
│   │   ├── runner.py                 # ADK Runner + session management
│   │   ├── sub_agents/               # Sub-agentes especializados
│   │   │   ├── proposicao_agent.py
│   │   │   ├── votacao_agent.py
│   │   │   ├── deputado_agent.py
│   │   │   ├── eleitor_agent.py
│   │   │   └── publicacao_agent.py
│   │   └── tools/                    # FunctionTools dos agentes
│   │       ├── camara_tools.py
│   │       ├── db_tools.py
│   │       ├── rag_tools.py
│   │       ├── votacao_tools.py
│   │       ├── notification_tools.py
│   │       └── publicacao_tools.py
│   └── eval/                         # Datasets de avaliação
│
├── channels/                         # Channel Adapters
│   ├── base.py                       # ChannelAdapter ABC
│   ├── telegram/                     # Telegram Bot
│   │   ├── bot.py                    # TelegramAdapter
│   │   ├── handlers.py               # Command handlers
│   │   ├── keyboards.py              # Inline keyboards
│   │   └── webhook.py                # FastAPI webhook
│   └── whatsapp/                     # Placeholder futuro
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # Entrypoint FastAPI
│   │   ├── config.py                 # Settings (Pydantic)
│   │   ├── domain/                   # Modelos SQLAlchemy
│   │   ├── schemas/                  # DTOs Pydantic
│   │   ├── repositories/             # Data Access Layer
│   │   ├── services/                 # Business Logic
│   │   ├── integrations/             # Clients HTTP (API Câmara)
│   │   ├── routers/                  # API Endpoints
│   │   ├── tasks/                    # Celery Tasks
│   │   └── db/                       # Engine + Session factory
│   ├── alembic/                      # Database Migrations
│   └── tests/                        # Testes (pytest)
│
├── dashboard/                        # Next.js (Parlamentar Dashboard)
│
├── docs/                             # Documentação
│   ├── architecture.md               # Este documento
│   ├── database-schema.md            # Schema do banco de dados
│   ├── agents.md                     # Documentação dos agentes ADK
│   └── channels.md                   # Documentação dos canais
│
├── docker-compose.yaml                # Orquestração principal
└── AGENTS.md                         # Guia para agentes IA
```

---

## 12. Endpoints da API

### Webhooks (entrada de mensagens)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/webhook/telegram` | Webhook Telegram Bot API |
| POST | `/webhook/whatsapp` | Webhook WhatsApp (futuro) |

### RSS Feed (saída para parlamentares)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/rss/votos` | Feed RSS com resultados consolidados |
| GET | `/rss/comparativos` | Feed RSS com comparativos pop vs real |

### Assinaturas
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/assinaturas/rss` | Criar assinatura RSS |
| POST | `/assinaturas/webhooks` | Registrar webhook de saída |
| POST | `/assinaturas/webhooks/{id}/test` | Disparar payload de teste |

### Admin (protegido por API key)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/admin/proposicoes` | Proposições sincronizadas |
| POST | `/admin/proposicoes/{id}/analisar` | Trigger análise IA |
| GET | `/admin/eleitores` | Eleitores cadastrados |
| GET | `/admin/rag/stats` | Estatísticas do índice vetorial |
| POST | `/admin/rag/reindex` | Re-indexar embeddings |

### Health
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check simples |
| GET | `/health/detailed` | Status DB, Redis, API Câmara |

---

## 13. Segurança

- **Autenticação de eleitores**: via `chat_id` do Telegram + verificação progressiva (CPF, título)
- **Dados sensíveis**: CPF e título de eleitor armazenados apenas como hash SHA-256
- **Admin API**: protegida por API key (`X-API-Key` header)
- **Webhooks de entrada**: validação de secret/assinatura do Telegram
- **Webhooks de saída**: payload assinado com HMAC-SHA256
- **Rate limiting**: `slowapi` por chat_id e por IP
- **Input validation**: Pydantic valida 100% dos inputs
- **SQL injection**: prevenido por SQLAlchemy ORM
- **HTTPS**: obrigatório em produção (webhooks exigem HTTPS)

---

## 14. Referências

- [AGENTS.md](../AGENTS.md) — Guia completo para agentes IA
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [API Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/swagger/api.html)
- [python-telegram-bot](https://python-telegram-bot.readthedocs.io/)
