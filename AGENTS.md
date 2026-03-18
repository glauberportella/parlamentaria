# Parlamentaria — Seu Parlamentar de IA

> Plataforma agêntica que conecta eleitores às decisões legislativas da Câmara dos Deputados do Brasil
> através de mensageiros (Telegram, WhatsApp). Agentes de IA analisam proposições, geram resumos
> acessíveis e coletam votação popular — tudo via conversa natural.

---

## 1. Visão Geral do Projeto

**Parlamentaria** é uma **plataforma agêntica** (agent-first) que democratiza o acesso à atividade legislativa brasileira. O eleitor interage com um **agente de IA conversacional** — seu _Parlamentar de IA_ — diretamente via **Telegram** (canal primário) e futuramente **WhatsApp** (canal secundário).

**Não existe frontend web para o usuário final.** A interface é 100% conversacional via mensageiros.

### 1.1 O que o sistema faz

1. **Conversa** com o eleitor via Telegram/WhatsApp em linguagem natural.
2. **Monitora** proposições legislativas em tramitação e eventos de plenário.
3. **Analisa** textos legislativos usando IA para extrair impacto, prós/contras e áreas afetadas.
4. **Explica** proposições em linguagem acessível ao eleitor, respondendo dúvidas.
5. **Coleta votos** dos eleitores cadastrados sobre pautas em votação.
6. **Consolida** a posição da maioria dos eleitores e a publica como voto popular.
7. **Notifica** proativamente o eleitor sobre novas pautas relevantes ao seu perfil.
8. **Publica** resultados consolidados via RSS Feed e Webhooks para parlamentares e sistemas externos.
9. **Compara** o voto popular com o resultado real da votação parlamentar, gerando feedback ao eleitor.

### 1.2 Princípios de Desenvolvimento

- **Agent-First**: toda interação do eleitor ocorre via agentes conversacionais, sem webapp.
- **Simplicidade**: arquitetura limpa, sem over-engineering.
- **Funcionalidade**: código que resolve problemas reais do eleitor.
- **Escalabilidade**: decisões que permitam crescimento orgânico.
- **Design Patterns**: usar soluções consagradas — não reinventar a roda.
- **SOLID**: princípios SOLID aplicados em todo o backend.
- **DRY / KISS**: sem duplicação, sem complexidade desnecessária.
- **Channel-Agnostic**: o core agêntico funciona independente do mensageiro.

---

## 2. Tech Stack

| Camada                | Tecnologia                          | Justificativa                                             |
|-----------------------|-------------------------------------|-----------------------------------------------------------|
| **Agent Framework**   | Google ADK (Agent Development Kit)  | Multi-agent, tools nativas, sessions, model-agnostic      |
| **Backend API**       | Python 3.12+ / FastAPI              | Async nativo, webhooks, tipagem forte, ecossistema IA     |
| **Canal Primário**    | Telegram Bot API + python-telegram-bot | Gratuito, bots nativos, rich messages, grupos            |
| **Canal Futuro**      | WhatsApp Business API               | Alcance massivo no Brasil, expansão planejada             |
| **Banco de Dados**    | PostgreSQL 16+ com pgvector          | Relacional robusto, JSONB + busca vetorial/semântica      |
| **ORM**               | SQLAlchemy 2.0 (async)              | Mapeamento robusto, migrations com Alembic                |
| **Cache**             | Redis                               | Cache de respostas da API, sessões ADK, filas              |
| **Task Queue**        | Celery + Redis (broker)             | Jobs assíncronos: sync com API Câmara, notificações       |
| **LLM (Agentes)**     | Gemini (primário) via ADK           | Integração nativa com ADK, custo competitivo              |
| **LLM (Fallback)**    | LiteLLM via ADK                     | Permite fallback para OpenAI, Anthropic, Ollama           |
| **Testes**            | pytest + pytest-asyncio             | Cobertura mínima 80%, incluindo testes de agentes         |
| **Containerização**   | Docker + Docker Compose             | Ambiente reproduzível dev/prod                            |
| **CI/CD**             | GitHub Actions                      | Lint, test, build, deploy automatizado                    |
| **Linting**           | Ruff                                | Padrão de código consistente (Python-only)                |
| **RAG / Embeddings**  | pgvector + Google gemini-embedding-001 | Busca semântica sobre proposições sincronizadas           |

---

## 3. Arquitetura

### 3.1 Visão Macro — Plataforma Agêntica (Ciclo Completo)

```mermaid
graph TD
    subgraph Entrada ["ENTRADA (Eleitores)"]
        TG["Telegram<br/>(Eleitor)"] <--> GW["Channel Gateway<br/>(Webhooks / python-telegram-bot)"]
        WA["WhatsApp<br/>(Futuro)"] <--> GW
    end

    subgraph Saida ["SAÍDA (Parlamentares)"]
        API["API Câmara<br/>Dados Abertos"]
    end

    GW --> ADK["Agent Orchestrator<br/>(Google ADK)"]
    API --> ADK

    ADK --> FAPI["FastAPI<br/>(Core)"]
    ADK --> PG[("PostgreSQL")]
    ADK --> RD["Redis"]

    subgraph Publication ["Publication Layer (Saída)"]
        RSS["RSS/Atom Feed"]
        WHout["Webhooks Saída<br/>(dispatch)"]
    end

    FAPI --> Publication
    PG --> Publication

    RSS --> Parl["Parlamentar<br/>(assinante)"]
    WHout --> Ext["Sistemas Externos<br/>(webhook consumer)"]

    style Entrada fill:#e3f2fd,stroke:#1565c0
    style Saida fill:#e8f5e9,stroke:#2e7d32
    style Publication fill:#fff3e0,stroke:#ef6c00
```

### 3.1.1 Ciclo Completo da Democracia Participativa

```mermaid
graph LR
    E["Eleitor<br/>(chat)"] -->|vota| VP["Voto<br/>Popular"]
    VP --> C["Consolidação<br/>(tempo real)"]
    C --> P["Publicação<br/>(RSS + Webhooks)"]
    P --> VR["Votação Real<br/>(sync API)"]
    VR --> Parl["Parlamentar<br/>(assinante)"]
    Parl --> Comp["Comparativo<br/>Pop vs Real"]
    Comp --> FB["Feedback<br/>(ao eleitor)"]
    FB --> E

    style E fill:#e3f2fd,stroke:#1565c0
    style Parl fill:#e8f5e9,stroke:#2e7d32
    style Comp fill:#fff3e0,stroke:#ef6c00
```

### 3.2 Arquitetura Multi-Agent (Google ADK)

O sistema usa **multi-agent architecture** do Google ADK com agentes especializados:

```mermaid
graph TD
    Root["🧠 ParlamentarAgent (Root)<br/>LlmAgent — Orquestrador principal<br/>Recebe mensagens do eleitor, delega para sub-agents"]

    Root --> PA["ProposicaoAgent<br/>(Sub-Agent)<br/>• Buscar proposições<br/>• Resumir<br/>• Analisar<br/>• Explicar"]
    Root --> VA["VotacaoAgent<br/>(Sub-Agent)<br/>• Coletar voto pop.<br/>• Resultado<br/>• Orientação"]
    Root --> DA["DeputadoAgent<br/>(Sub-Agent)<br/>• Perfil deputado<br/>• Votações<br/>• Despesas<br/>• Comparar"]
    Root --> EA["EleitorAgent<br/>(Sub-Agent)<br/>• Cadastro<br/>• Preferências<br/>• Histórico<br/>• Notificação"]
    Root --> PubA["PublicacaoAgent<br/>(Sub-Agent)<br/>• Comparativo pop vs real<br/>• Status feed<br/>• Feedback"]

    subgraph Tools ["FunctionTools compartilhadas"]
        T1["camara_api"]
        T2["db_query"]
        T3["cache_lookup"]
        T4["notify_user"]
        T5["publicacao"]
    end

    PA -.-> Tools
    VA -.-> Tools
    DA -.-> Tools
    EA -.-> Tools
    PubA -.-> Tools

    style Root fill:#4285f4,color:#fff,stroke:#1a73e8
    style Tools fill:#f1f3f4,stroke:#dadce0
```

### 3.3 Padrão Arquitetural — Layered + Agent Architecture

```mermaid
block-beta
    columns 1
    CH["Channel Layer (Adapters) — Telegram, WhatsApp (futuro)"]
    AG["Agent Layer (Google ADK) — Agentes, tools, sessions"]
    SV["Service Layer (Use Cases) — Lógica de negócio"]
    PB["Publication Layer (Saída) — RSS Feed, Webhooks, comparativo"]
    RP["Repository Layer (Data Access) — Queries, ORM"]
    IN["Integration Layer (APIs) — Client HTTP Câmara"]
    DM["Domain Layer (Models) — Entidades, value objects, DTOs"]

    CH --> AG --> SV --> PB --> RP --> IN --> DM

    style CH fill:#e3f2fd,stroke:#1565c0
    style AG fill:#e8eaf6,stroke:#283593
    style SV fill:#fff3e0,stroke:#ef6c00
    style PB fill:#fce4ec,stroke:#c62828
    style RP fill:#e8f5e9,stroke:#2e7d32
    style IN fill:#f3e5f5,stroke:#6a1b9a
    style DM fill:#fffde7,stroke:#f57f17
```

### 3.4 Design Patterns Utilizados

| Pattern                | Onde                                | Por quê                                             |
|------------------------|-------------------------------------|-----------------------------------------------------|
| **Multi-Agent**        | Orquestração Google ADK             | Agentes especializados, escalabilidade               |
| **Channel Adapter**    | Telegram / WhatsApp                 | Trocar canal sem alterar lógica agêntica             |
| **Repository**         | Acesso a dados                      | Abstrai persistência, testabilidade                  |
| **Service**            | Lógica de negócio                   | Separa regras da camada de agentes                   |
| **FunctionTool**       | Tools do ADK                        | Funções Python como capacidades dos agentes          |
| **Agent-as-a-Tool**    | Sub-agentes como tools              | Delegação especializada entre agentes                |
| **Factory**            | Criação de channel adapters         | Instanciação flexível baseada em configuração        |
| **DTO**                | Transferência entre camadas         | Tipagem explícita, validação com Pydantic            |
| **Observer/Event**     | Notificação proativa ao eleitor     | Desacoplamento entre sync e notificação              |
| **Pub/Sub**            | RSS Feed + Webhook dispatch         | Parlamentares e sistemas assinam resultados de votos |
| **Comparator**         | Comparativo voto popular vs real    | Feedback transparente sobre alinhamento legislativo  |

---

## 4. Estrutura de Diretórios

```
parlamentaria/
├── AGENTS.md                         # Este arquivo — guia para agentes IA
├── docker-compose.yml                # Orquestração dos serviços
├── .env.example                      # Variáveis de ambiente (template)
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Pipeline CI (lint + test + build)
│       └── deploy.yml                # Pipeline deploy
│
├── agents/                           # Google ADK — Agentes de IA
│   ├── __init__.py
│   ├── parlamentar/                  # Root Agent package (ADK convention)
│   │   ├── __init__.py               # Exporta `root_agent`
│   │   ├── agent.py                  # ParlamentarAgent — orquestrador root
│   │   ├── prompts.py                # System instructions e prompt templates
│   │   ├── sub_agents/
│   │   │   ├── __init__.py
│   │   │   ├── proposicao_agent.py   # Busca, resume e analisa proposições
│   │   │   ├── votacao_agent.py      # Coleta voto popular, mostra resultados
│   │   │   ├── deputado_agent.py     # Perfil, votações, despesas de deputados
│   │   │   ├── eleitor_agent.py      # Cadastro, preferências, notificações
│   │   │   └── publicacao_agent.py   # Comparativo pop vs real, status feed
│   │   └── tools/                    # FunctionTools dos agentes
│   │       ├── __init__.py
│   │       ├── camara_tools.py       # Tools que consultam API da Câmara
│   │       ├── db_tools.py           # Tools que acessam banco de dados
│   │       ├── rag_tools.py          # Tools de busca semântica RAG (pgvector)
│   │       ├── votacao_tools.py      # Tools de votação popular
│   │       ├── notification_tools.py # Tools de notificação proativa
│   │       └── publicacao_tools.py   # Tools de publicação e comparativo
│   └── eval/                         # Datasets de avaliação ADK
│       ├── proposicao_eval.json
│       ├── votacao_eval.json
│       └── conversational_eval.json
│
├── channels/                         # Channel Adapters (Telegram, WhatsApp)
│   ├── __init__.py
│   ├── base.py                       # ChannelAdapter ABC — interface abstrata
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── bot.py                    # Telegram Bot (python-telegram-bot)
│   │   ├── handlers.py              # Command & message handlers
│   │   ├── keyboards.py             # Inline keyboards (votar, navegar)
│   │   └── webhook.py               # FastAPI webhook endpoint
│   └── whatsapp/                     # Futuro — WhatsApp Business API
│       ├── __init__.py
│       └── placeholder.py           # Stub para implementação futura
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml                # Dependências e config do projeto Python
│   ├── alembic/                      # Migrations do banco
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # Entrypoint FastAPI, lifespan, webhooks
│   │   ├── config.py                 # Settings com Pydantic BaseSettings
│   │   ├── dependencies.py           # Dependency injection FastAPI
│   │   │
│   │   ├── domain/                   # Entidades e Value Objects do domínio
│   │   │   ├── __init__.py
│   │   │   ├── deputado.py
│   │   │   ├── proposicao.py
│   │   │   ├── votacao.py
│   │   │   ├── evento.py
│   │   │   ├── partido.py
│   │   │   ├── eleitor.py
│   │   │   ├── voto_popular.py
│   │   │   ├── assinatura.py         # AssinaturaRSS + AssinaturaWebhook
│   │   │   ├── comparativo.py        # ComparativoVotacao
│   │   │   └── document_chunk.py     # DocumentChunk (embeddings pgvector)
│   │   │
│   │   ├── schemas/                  # Pydantic DTOs (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── deputado.py
│   │   │   ├── proposicao.py
│   │   │   ├── votacao.py
│   │   │   ├── eleitor.py
│   │   │   ├── voto_popular.py
│   │   │   ├── assinatura.py         # DTOs para RSS/Webhook subscriptions
│   │   │   └── comparativo.py        # DTOs para comparativo e feedback
│   │   │
│   │   ├── repositories/            # Data Access Layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseRepository (genérico)
│   │   │   ├── proposicao_repo.py
│   │   │   ├── votacao_repo.py
│   │   │   ├── eleitor_repo.py
│   │   │   ├── voto_popular_repo.py
│   │   │   ├── assinatura_repo.py   # Gestão de assinaturas RSS/Webhook
│   │   │   ├── comparativo_repo.py  # Persistência de comparativos
│   │   │   └── document_chunk_repo.py # Busca vetorial com pgvector
│   │   │
│   │   ├── services/                # Business Logic Layer
│   │   │   ├── __init__.py
│   │   │   ├── proposicao_service.py
│   │   │   ├── votacao_service.py
│   │   │   ├── eleitor_service.py
│   │   │   ├── analise_service.py   # Orquestra análise IA de proposições
│   │   │   ├── sync_service.py      # Sincronização com API da Câmara
│   │   │   ├── embedding_service.py  # Geração de embeddings (Google gemini-embedding-001)
│   │   │   ├── rag_service.py        # Indexação e busca semântica RAG
│   │   │   ├── digest_service.py     # Motor de geração de digests periódicos
│   │   │   ├── publicacao_service.py # Publicação RSS + dispatch webhooks
│   │   │   └── comparativo_service.py # Comparativo voto popular vs real
│   │   │
│   │   ├── integrations/            # External API Clients
│   │   │   ├── __init__.py
│   │   │   ├── camara_client.py     # HTTP Client para API Dados Abertos
│   │   │   └── camara_types.py      # Tipagem das respostas da API Câmara
│   │   │
│   │   ├── routers/                 # API Endpoints internos (admin/webhooks)
│   │   │   ├── __init__.py
│   │   │   ├── webhooks.py          # Webhook Telegram / WhatsApp
│   │   │   ├── admin.py             # Endpoints administrativos
│   │   │   ├── cidadao.py           # Endpoints públicos do Painel do Cidadão
│   │   │   ├── health.py            # Health checks
│   │   │   ├── rss.py               # RSS/Atom Feed público
│   │   │   └── assinaturas.py       # Gestão de assinaturas webhook
│   │   │
│   │   ├── tasks/                   # Celery async tasks
│   │   │   ├── __init__.py
│   │   │   ├── sync_proposicoes.py
│   │   │   ├── sync_votacoes.py
│   │   │   ├── notificar_eleitores.py
│   │   │   ├── dispatch_webhooks.py  # Dispara webhooks de saída
│   │   │   ├── gerar_comparativos.py # Gera comparativos pop vs real
│   │   │   ├── generate_embeddings.py # Gera embeddings RAG (pós-sync e daily)
│   │   │   └── send_digests.py       # Envia digests semanais/diários (Celery beat)
│   │   │
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── session.py           # Async engine + sessionmaker
│   │       └── base.py              # Base declarativa SQLAlchemy
│   │
│   └── tests/
│       ├── conftest.py              # Fixtures globais
│       ├── unit/
│       │   ├── test_services/
│       │   ├── test_repositories/
│       │   └── test_integrations/
│       ├── integration/
│       │   ├── test_agents/         # Testes dos agentes ADK
│       │   ├── test_channels/       # Testes dos channel adapters
│       │   └── test_db/
│       └── fixtures/                # JSON fixtures (respostas mock da API)
│           ├── proposicoes.json
│           ├── votacoes.json
│           └── telegram_updates.json
│
└── docs/
    ├── architecture.md               # Detalhamento arquitetural
    ├── agents.md                     # Documentação dos agentes ADK
    ├── channels.md                   # Documentação dos canais de mensageria
    └── decisions/                    # ADRs (Architecture Decision Records)
```

---

## 5. Integração com API Dados Abertos da Câmara

### 5.1 Base URL

```
https://dadosabertos.camara.leg.br/api/v2
```

- Formato: JSON (padrão) ou XML
- Paginação: `pagina` e `itens` (padrão 15, máximo 100)
- Rate limit: sem autenticação, respeitar limite razoável (~1 req/s)

### 5.2 Endpoints Utilizados (prioridade)

#### Proposições (core)
| Endpoint                                | Uso no Sistema                              |
|-----------------------------------------|---------------------------------------------|
| `GET /proposicoes`                      | Listar/buscar proposições em tramitação     |
| `GET /proposicoes/{id}`                 | Detalhes de uma proposição                   |
| `GET /proposicoes/{id}/autores`         | Autores da proposição                        |
| `GET /proposicoes/{id}/temas`           | Áreas temáticas                              |
| `GET /proposicoes/{id}/tramitacoes`     | Histórico de tramitação                      |
| `GET /proposicoes/{id}/votacoes`        | Votações sobre a proposição                  |

#### Votações (core)
| Endpoint                                | Uso no Sistema                              |
|-----------------------------------------|---------------------------------------------|
| `GET /votacoes`                         | Listar votações recentes                     |
| `GET /votacoes/{id}`                    | Detalhes de uma votação                      |
| `GET /votacoes/{id}/orientacoes`        | Orientação de bancada                        |
| `GET /votacoes/{id}/votos`              | Voto individual de cada parlamentar          |

#### Deputados
| Endpoint                                | Uso no Sistema                              |
|-----------------------------------------|---------------------------------------------|
| `GET /deputados`                        | Listar deputados ativos                      |
| `GET /deputados/{id}`                   | Perfil do deputado                           |
| `GET /deputados/{id}/despesas`          | Transparência                                |

#### Eventos
| Endpoint                                | Uso no Sistema                              |
|-----------------------------------------|---------------------------------------------|
| `GET /eventos`                          | Agenda do plenário                           |
| `GET /eventos/{id}/pauta`              | Proposições em pauta                         |
| `GET /eventos/{id}/votacoes`           | Votações de um evento                        |

#### Referências
| Endpoint                                    | Uso no Sistema                          |
|---------------------------------------------|-----------------------------------------|
| `GET /referencias/proposicoes/codTema`      | Lista de temas possíveis                |
| `GET /referencias/proposicoes/codSituacao`  | Situações de tramitação                 |
| `GET /referencias/proposicoes/codTipo`      | Tipos de proposição (PL, PEC, etc.)     |

### 5.3 Implementação do Client HTTP

- Usar `httpx.AsyncClient` com retry automático (tenacity).
- Cache com Redis (TTL de 5 min para listagens, 1h para dados estáticos).
- Tipagem completa com dataclasses/Pydantic para respostas.
- Tratamento de paginação transparente (iterator async).
- Respeitar headers `Last-Modified` / `ETag` quando disponíveis.

```python
# Exemplo de interface esperada:
class CamaraClient:
    async def listar_proposicoes(self, **filtros) -> list[Proposicao]: ...
    async def obter_proposicao(self, id: int) -> ProposicaoDetalhada: ...
    async def listar_votacoes(self, **filtros) -> list[Votacao]: ...
    async def obter_votos(self, votacao_id: int) -> list[VotoParlamentar]: ...
    async def listar_eventos(self, **filtros) -> list[Evento]: ...
    async def obter_pauta_evento(self, evento_id: int) -> list[ItemPauta]: ...
```

---

## 6. Modelos de Domínio

### 6.1 Entidades Principais

```
Proposicao
├── id: int (id da API Câmara)
├── tipo: str (PL, PEC, MPV, PLP, etc.)
├── numero: int
├── ano: int
├── ementa: str
├── texto_completo_url: str | None
├── data_apresentacao: date
├── situacao: str
├── temas: list[str]
├── autores: list[Autor]
├── resumo_ia: str | None          # Gerado pelo sistema
├── analise_ia: AnaliseIA | None    # Gerado pelo sistema
├── ultima_sincronizacao: datetime
└── votos_populares: list[VotoPopular]

Votacao
├── id: int (id da API Câmara)
├── proposicao_id: int | None
├── data: datetime
├── descricao: str
├── aprovacao: bool | None
├── votos_sim: int
├── votos_nao: int
├── abstencoes: int
├── orientacoes: list[OrientacaoBancada]
└── votos_parlamentares: list[VotoParlamentar]

Eleitor
├── id: uuid
├── nome: str
├── email: str (unique)
├── uf: str (2 chars, sigla estado)
├── chat_id: str | None (unique, ID do mensageiro)
├── channel: str (telegram, whatsapp)
├── verificado: bool
├── cidadao_brasileiro: bool
├── data_nascimento: date | None
├── cpf_hash: str | None (SHA-256, unique)
├── titulo_eleitor_hash: str | None (SHA-256, unique)
├── nivel_verificacao: NivelVerificacao (NAO_VERIFICADO, AUTO_DECLARADO, VERIFICADO_TITULO)
├── temas_interesse: list[str] | None
├── frequencia_notificacao: FrequenciaNotificacao (IMEDIATA, DIARIA, SEMANAL, DESATIVADA) [default: SEMANAL]
├── horario_preferido_notificacao: int (0-23, default 9)
├── ultimo_digest_enviado: datetime | None
├── data_cadastro: datetime
├── updated_at: datetime
└── votos: list[VotoPopular]

VotoPopular
├── id: uuid
├── eleitor_id: uuid
├── proposicao_id: int
├── voto: enum (SIM, NAO, ABSTENCAO)
├── tipo_voto: enum (OFICIAL, OPINIAO)   # Classificação automática por elegibilidade
├── data_voto: datetime
└── justificativa: str | None

AnaliseIA
├── id: uuid
├── proposicao_id: int
├── resumo_leigo: str              # Resumo em linguagem acessível
├── impacto_esperado: str          # Análise de impacto
├── areas_afetadas: list[str]      # Saúde, educação, economia, etc.
├── argumentos_favor: list[str]
├── argumentos_contra: list[str]
├── provedor_llm: str              # Qual LLM gerou
├── modelo: str                    # Modelo específico utilizado
├── data_geracao: datetime
└── versao: int                    # Permite re-análise
AssinaturaRSS
├── id: uuid
├── nome: str                      # Nome do assinante (parlamentar, org)
├── email: str | None              # Contato (opcional)
├── token: str                     # Token único para acesso ao feed
├── filtro_temas: list[str]        # Filtrar feed por temas específicos
├── filtro_uf: str | None           # Filtrar por UF dos eleitores
├── ativo: bool
├── data_criacao: datetime
└── ultimo_acesso: datetime | None

AssinaturaWebhook
├── id: uuid
├── nome: str                      # Nome do sistema/assinante
├── url: str                       # URL de callback (HTTPS obrigatório)
├── secret: str                    # HMAC secret para validação de payload
├── eventos: list[str]             # Tipos: "voto_consolidado", "comparativo"
├── filtro_temas: list[str]        # Filtrar por temas
├── ativo: bool
├── data_criacao: datetime
├── ultimo_dispatch: datetime | None
└── falhas_consecutivas: int       # Circuit breaker: desativa após N falhas

ComparativoVotacao
├── id: uuid
├── proposicao_id: int
├── votacao_camara_id: int         # ID da votação real na Câmara
├── voto_popular_sim: int          # Total votos populares SIM
├── voto_popular_nao: int          # Total votos populares NÃO
├── voto_popular_abstencao: int
├── resultado_camara: str          # "APROVADO" | "REJEITADO"
├── votos_camara_sim: int
├── votos_camara_nao: int
├── alinhamento: float             # 0.0 a 1.0 — quão alinhado pop/real
├── resumo_ia: str | None          # Análise IA do comparativo
└── data_geracao: datetime```

---

## 7. Agentes — Google ADK (Agent Development Kit)

O coração da plataforma são os **agentes conversacionais** do Google ADK. A IA não é apenas uma camada de análise — é a **interface principal** com o eleitor.

### 7.1 Conceitos ADK Utilizados

| Conceito ADK        | Uso no Sistema                                                |
|---------------------|---------------------------------------------------------------|
| **LlmAgent**        | Todos os agentes (root + sub-agents) usam LLM para conversar |
| **FunctionTool**    | Funções Python que os agentes chamam (API Câmara, DB, etc.)  |
| **Agent-as-a-Tool** | Sub-agentes invocados como tools pelo root agent              |
| **Session**         | Contexto da conversa com cada eleitor (histórico + state)     |
| **State**           | Dados temporários da sessão (eleitor logado, proposição ativa)|
| **Memory**          | Memória de longo prazo — preferências do eleitor entre sessões|
| **Callbacks**       | Logging, validação de segurança, rate limiting por eleitor    |

### 7.2 Root Agent — ParlamentarAgent

O agente principal que recebe todas as mensagens do eleitor e orquestra a resposta:

```python
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool

from agents.parlamentar.sub_agents.proposicao_agent import proposicao_agent
from agents.parlamentar.sub_agents.votacao_agent import votacao_agent
from agents.parlamentar.sub_agents.deputado_agent import deputado_agent
from agents.parlamentar.sub_agents.eleitor_agent import eleitor_agent
from agents.parlamentar.sub_agents.publicacao_agent import publicacao_agent

root_agent = LlmAgent(
    name="ParlamentarAgent",
    model="gemini-2.0-flash",  # via ADK — model-agnostic
    instruction="""Você é o Parlamentar de IA — um assistente que ajuda
    eleitores brasileiros a entender e participar das decisões legislativas
    da Câmara dos Deputados.

    Seu tom é: acessível, apartidário, informativo e respeitoso.
    Nunca emita opinião política pessoal. Apresente fatos e análises equilibradas.

    Delegue para sub-agentes especializados conforme o tema da conversa.""",
    sub_agents=[proposicao_agent, votacao_agent, deputado_agent, eleitor_agent, publicacao_agent],
)
```

### 7.3 Sub-Agents

Cada sub-agent é um `LlmAgent` especializado com suas próprias tools:

| Sub-Agent            | Responsabilidade                           | Tools Principais                              |
|----------------------|--------------------------------------------|-----------------------------------------------|
| `ProposicaoAgent`    | Buscar, resumir, analisar proposições      | `busca_semantica_proposicoes`, `buscar_proposicoes`, `obter_analise_ia` |
| `VotacaoAgent`       | Coletar voto popular, mostrar resultados   | `registrar_voto`, `obter_resultado_votacao`   |
| `DeputadoAgent`      | Perfil de deputados, votações, despesas    | `buscar_deputado`, `obter_despesas`           |
| `EleitorAgent`       | Cadastro, preferências, verificação        | `cadastrar_eleitor`, `atualizar_preferencias` |
| `PublicacaoAgent`    | Comparativo pop vs real, status de feed    | `obter_comparativo`, `status_publicacao`      |

### 7.4 FunctionTools — Exemplo

```python
def buscar_proposicoes(
    tema: str | None = None,
    tipo: str | None = None,
    ano: int | None = None,
) -> dict:
    """Busca proposições legislativas na Câmara dos Deputados.

    Args:
        tema: Área temática (ex: 'saúde', 'educação', 'economia').
        tipo: Tipo de proposição (ex: 'PL', 'PEC', 'MPV').
        ano: Ano de apresentação da proposição.

    Returns:
        Dict com lista de proposições encontradas e total de resultados.
    """
    # Chama CamaraClient → retorna dados estruturados para o agente
    ...
    return {"status": "success", "proposicoes": [...], "total": 42}
```

### 7.5 LLM — Modelo Agnóstico via ADK

O Google ADK é **model-agnostic**. O sistema usa Gemini como padrão mas permite trocar:

| Modelo             | Quando Usar                   | Config ADK                          |
|--------------------|-------------------------------|-------------------------------------|
| `gemini-2.0-flash` | Produção — padrão (rápido)    | `model="gemini-2.0-flash"`          |
| `gemini-2.5-pro`   | Análises complexas            | `model="gemini-2.5-pro"`            |
| LiteLLM (qualquer) | Fallback / custom             | `model="litellm/gpt-4o"` etc.      |
| Ollama (local)      | Desenvolvimento offline       | `model="ollama/llama3"` etc.        |

A seleção do modelo é feita via variável de ambiente `AGENT_MODEL`.

### 7.6 Sessions e State

Cada eleitor tem uma **session** persistente no ADK:

```python
# State keys usados nas sessões:
STATE_KEYS = {
    "eleitor_id": str,           # UUID do eleitor cadastrado
    "eleitor_verificado": bool,   # Se completou verificação
    "eleitor_uf": str,           # UF do eleitor (para filtros)
    "proposicao_ativa": int,     # ID da proposição sendo discutida
    "contexto_conversa": str,    # Contexto atual (proposição, deputado, etc.)
}
```

---

## 8. Canal de Mensageria — Channel Adapter Pattern

### 8.1 Interface Abstrata

```python
from abc import ABC, abstractmethod

class ChannelAdapter(ABC):
    """Interface abstrata para canais de mensageria."""

    @abstractmethod
    async def send_message(self, chat_id: str, text: str) -> None:
        """Envia mensagem de texto para o eleitor."""
        ...

    @abstractmethod
    async def send_rich_message(self, chat_id: str, text: str, buttons: list[dict]) -> None:
        """Envia mensagem com botões interativos."""
        ...

    @abstractmethod
    async def setup_webhook(self, url: str) -> None:
        """Configura webhook para receber mensagens."""
        ...

    @abstractmethod
    async def process_incoming(self, payload: dict) -> tuple[str, str]:
        """Processa mensagem recebida. Retorna (chat_id, texto)."""
        ...
```

### 8.2 Telegram (Canal Primário)

- **Biblioteca**: `python-telegram-bot` (async nativo).
- **Webhook**: mensagens chegam via webhook no FastAPI → repassadas ao ADK Runner.
- **Rich Messages**: Inline Keyboards para votação (SIM/NÃO/ABSTENÇÃO), navegação.
- **Comandos**: `/start`, `/proposicoes`, `/votar`, `/meuperfil`, `/ajuda`.
- **Grupos**: suporte a interação em grupos do Telegram (futuro).

### 8.3 WhatsApp (Canal Futuro)

- **API**: WhatsApp Business API (Meta).
- **Webhook**: mesmo padrão do Telegram — messages chegam via webhook.
- **Implementação**: mesma interface `ChannelAdapter`, adapter diferente.
- **Status**: stub/placeholder — implementação planejada para fase posterior.

### 8.4 Fluxo de Mensagem (End-to-End)

```mermaid
sequenceDiagram
    participant E as Eleitor (Telegram)
    participant TG as Telegram Bot API
    participant WH as FastAPI /webhook/telegram
    participant TA as TelegramAdapter
    participant ADK as ADK Runner
    participant AG as Root Agent → Sub-Agents → Tools

    E->>TG: Mensagem
    TG->>WH: webhook POST
    WH->>TA: process_incoming()
    TA->>ADK: run_async()
    ADK->>AG: Delega para sub-agents
    AG-->>ADK: Resposta processada
    ADK-->>TA: Agent Response (texto)
    TA->>TG: send_message()
    TG->>E: Resposta no chat
```

---

## 9. Funcionalidades e Módulos

### 9.1 Módulo: Sincronização com a Câmara (`sync_service`)

- **Job periódico** (Celery beat) 2x/dia (manhã 6h e noite 20h).
- Sincroniza proposições recentes, votações do dia, eventos com pauta.
- Usa paginação da API para consumir dados incrementalmente.
- Persiste no PostgreSQL com lógica de upsert (evita duplicatas).
- Dispara **notificação proativa** ao eleitor quando detecta nova proposição relevante.

### 9.2 Módulo: Análise IA via Agentes (`analise_service`)

- **Trigger**: nova proposição sincronizada ou solicitação do eleitor via chat.
- O `ProposicaoAgent` usa tools para buscar texto completo e gerar análise.
- Gera: resumo leigo, impacto, áreas afetadas, prós/contras.
- Armazena resultado em `AnaliseIA` vinculada à proposição.
- Permite re-análise (versionamento).

### 9.3 Módulo: Votação Popular (`votacao_service`)

- Eleitor vota via **Inline Keyboard** no Telegram: SIM / NÃO / ABSTENÇÃO.
- 1 voto por eleitor por proposição (idempotente — último voto vale).
- Consolidação em tempo real: total SIM, NÃO, ABSTENÇÃO, percentuais.
- O agente apresenta resultado ao eleitor de forma conversacional.

### 9.4 Módulo: Gestão de Eleitores (`eleitor_service`)

- Cadastro via conversa com o `EleitorAgent` (pede nome, UF, cidadania, data de nascimento, CPF).
- Identificação pelo `chat_id` do mensageiro (Telegram ID).
- Perfil progressivo: dados coletados em etapas naturais da conversa.
- Preferências: temas de interesse para notificações proativas.
- **Verificação de identidade**: sistema progressivo de verificação (ver 9.4.1).

#### 9.4.1 Sistema de Verificação Progressiva

O sistema implementa **três níveis de verificação** progressivos para equilibrar
inclusão (qualquer pessoa pode participar) com integridade (votos oficiais requerem
identificação básica):

| Nível | Enum | Requisitos | Tipo de Voto |
|-------|------|-----------|-------------|
| 1 | `NAO_VERIFICADO` | Conta criada, dados mínimos | OPINIÃO (consultivo) |
| 2 | `AUTO_DECLARADO` | Nome, UF, CPF, nascimento, cidadania | OFICIAL |
| 3 | `VERIFICADO_TITULO` | + Título de eleitor validado | OFICIAL (máxima confiança) |

**Validações implementadas:**
- **CPF**: Algoritmo módulo-11 com blacklist (dígitos iguais). Apenas hash SHA-256 armazenado.
- **Título de Eleitor**: Algoritmo de 12 dígitos (8 sequenciais + 2 código estado + 2 verificadores),
  tratamento especial para SP/MG (estados 01/02). UF do título cruzada com UF do cadastro.

**Segurança de dados:**
- CPF e título de eleitor **nunca** são armazenados em texto — apenas hashes SHA-256 (64 chars hex).
- Um CPF = uma conta (constraint UNIQUE impede duplicidade).
- O hash impede que o número original seja recuperado, mesmo em caso de vazamento.

**Fluxo típico:**
```
1. Usuário inicia conversa → conta criada (NAO_VERIFICADO)
2. Fornece nome, UF, cidadania, nascimento, CPF → AUTO_DECLARADO (votos OFICIAIS)
3. Opcionalmente valida título de eleitor → VERIFICADO_TITULO (máxima confiança)
```

### 9.5 Módulo: Notificações Proativas e Engajamento

O sistema implementa uma **estratégia de engajamento em 3 camadas** que equilibra
informação com respeito à atenção do eleitor:

| Camada | Frequência | Público | Conteúdo |
|--------|-----------|---------|----------|
| **Resumo Semanal** | Segunda-feira 9h | Todos (default) | Novas proposições, highlights, comparativos, agenda |
| **Resumo Diário** | Diário 8:30h | Opt-in | Mesmo conteúdo, filtrado por 24h |
| **Alertas Imediatos** | Tempo real | Opt-in | Proposição relevante ao perfil + resumo diário |

#### 9.5.1 Preferências de Frequência (`FrequenciaNotificacao`)

Enum no modelo `Eleitor` com 4 valores:

| Valor | Comportamento |
|-------|---------------|
| `SEMANAL` | Default para novos usuários. Resumo semanal toda segunda. |
| `DIARIA` | Resumo diário. Mais engajado mas não invasivo. |
| `IMEDIATA` | Alertas em tempo real + resumo diário. Para power users. |
| `DESATIVADA` | Sem digests. Ainda recebe comparativos de proposições em que votou. |

Campos adicionais no `Eleitor`:
- `horario_preferido_notificacao: int` — hora (0-23) preferida, default 9h.
- `ultimo_digest_enviado: datetime | None` — previne envio duplicado.

#### 9.5.2 DigestService (`digest_service.py`)

Motor central de geração de digests personalizados. Compõe 5 seções:

1. **Temas de interesse**: proposições novas filtradas por `temas_interesse` do eleitor.
2. **Destaques**: proposições mais votadas no período (popularidade).
3. **Comparativos**: resultados de votos popular vs real publicados no período.
4. **Agenda**: eventos/plenário nos próximos 7 dias.
5. **Estatísticas**: total votos, eleitores ativos, novas proposições.

Fluxo: `find_voters_for_digest()` → `generate_digest_for_voter()` → `format_digest()` → `send via channel adapter` → `update ultimo_digest_enviado`.

#### 9.5.3 Celery Tasks e Schedule

| Task | Schedule | Config |
|------|----------|--------|
| `send_weekly_digest_task` | `DIGEST_WEEKLY_DAY` (0=seg) às `DIGEST_WEEKLY_HOUR:00` | `digest_weekly_day`, `digest_weekly_hour` |
| `send_daily_digest_task` | Diário às `DIGEST_DAILY_HOUR:DIGEST_DAILY_MINUTE` | `digest_daily_hour`, `digest_daily_minute` |

Processamento em lotes (`digest_batch_size=50`) com rate limiting (`digest_max_daily_notifications=3`).

#### 9.5.4 Alertas Imediatos (Filtro de Frequência)

O `NotificationService.notify_voters_about_proposicao()` agora **só envia alertas
imediatos para eleitores com `frequencia_notificacao == IMEDIATA`**. Eleitores em
`DIARIA` ou `SEMANAL` receberão a mesma informação no próximo digest.

#### 9.5.5 Tool do Agente (`configurar_frequencia_notificacao`)

O `EleitorAgent` expõe a tool `configurar_frequencia_notificacao(chat_id, frequencia, horario)`
para que o eleitor configure suas preferências via conversa natural:

- "Quero receber notificações todo dia" → `DIARIA`
- "Prefiro só o resumo semanal" → `SEMANAL`
- "Me avise de tudo em tempo real" → `IMEDIATA`
- "Não quero mais receber mensagens" → `DESATIVADA`

#### 9.5.6 Variáveis de Ambiente (Engajamento)

```bash
DIGEST_MAX_DAILY_NOTIFICATIONS=3    # Max notificações/dia por eleitor
DIGEST_WEEKLY_DAY=0                 # 0=segunda, 6=domingo
DIGEST_WEEKLY_HOUR=9                # Hora do envio semanal
DIGEST_DAILY_HOUR=8                 # Hora do envio diário
DIGEST_DAILY_MINUTE=30              # Minuto do envio diário
DIGEST_BATCH_SIZE=50                # Eleitores processados por lote
```

### 9.6 Módulo: Publicação e Distribuição (`publicacao_service`)

Este módulo é a **camada de saída** que dá vazão aos votos populares, entregando-os a parlamentares e sistemas externos.

#### 9.6.1 RSS/Atom Feed

- **Endpoint público**: `GET /rss/votos` — feed RSS 2.0 / Atom com resultados de votação popular.
- Cada item do feed = 1 proposição com resultado consolidado (SIM%, NÃO%, ABSTENÇÃO%, total votos).
- **Filtros via query params**: `?tema=saude&uf=SP` — parlamentar pode assinar feed filtrado.
- **Autenticação via token**: `?token=<uuid>` — cada `AssinaturaRSS` gera token único.
- **Formato**: RSS 2.0 com enclosures para dados estruturados (JSON attachment).
- Feed atualizado automaticamente quando nova votação popular é consolidada.
- TTL configurável (padrão: 15 min) para caching em leitores RSS.

```python
# Exemplo de item RSS:
<item>
  <title>PL 1234/2026 - Reforma Tributária: Voto Popular</title>
  <description>
    73% dos eleitores votaram SIM (1.247 votos).
    21% votaram NÃO. 6% se abstiveram.
  </description>
  <link>https://parlamentaria.app/proposicao/1234</link>
  <pubDate>Mon, 01 Mar 2026 14:30:00 -0300</pubDate>
  <category>economia</category>
  <category>tributos</category>
  <enclosure url="https://parlamentaria.app/api/votos/1234.json" type="application/json" />
</item>
```

#### 9.6.2 Webhooks de Saída (Push)

- Sistemas externos registram URL de callback via API admin.
- Quando votação popular é consolidada (ou comparativo é gerado), Celery dispara task `dispatch_webhooks`.
- **Payload**: JSON com dados da proposição, resultado consolidado e metadata.
- **Segurança**: payload assinado com HMAC-SHA256 usando `secret` do assinante (header `X-Webhook-Signature`).
- **Retry**: 3 tentativas com backoff exponencial (1s, 5s, 25s).
- **Circuit breaker**: após 5 falhas consecutivas, assinatura é desativada automaticamente.
- **Eventos disponíveis**: `voto_consolidado`, `comparativo_gerado`, `nova_proposicao`.

```python
# Payload exemplo de webhook:
{
  "evento": "voto_consolidado",
  "timestamp": "2026-03-01T14:30:00-03:00",
  "proposicao": {
    "id": 1234,
    "tipo": "PL",
    "numero": 1234,
    "ano": 2026,
    "ementa": "Reforma Tributária...",
    "temas": ["economia", "tributos"]
  },
  "resultado": {
    "total_votos": 1247,
    "sim": 910,
    "nao": 262,
    "abstencao": 75,
    "percentual_sim": 73.0,
    "percentual_nao": 21.0,
    "percentual_abstencao": 6.0
  }
}
```

### 9.7 Módulo: Comparativo Popular vs Real (`comparativo_service`)

Fecha o ciclo de democracia participativa comparando o desejo popular com a votação real dos parlamentares.

- **Trigger**: quando `sync_service` detecta resultado de votação real (API Câmara) para uma proposição que teve votação popular.
- **Cálculo de alinhamento**: índice 0.0 a 1.0 baseado na correlação entre maioria popular e resultado parlamentar.
- **Análise IA**: o agente gera resumo em linguagem acessível do comparativo.
- **Notificação aos eleitores**: quem votou na proposição recebe feedback via chat.
- **Publicação**: resultado do comparativo é publicado via RSS Feed e disparado via Webhooks.

```python
# Lógica de alinhamento:
def calcular_alinhamento(voto_popular: dict, resultado_camara: str) -> float:
    """Calcula o índice de alinhamento entre voto popular e resultado real.

    Returns:
        Float 0.0 (total divergência) a 1.0 (total alinhamento).
    """
    maioria_popular = "SIM" if voto_popular["sim"] > voto_popular["nao"] else "NAO"
    alinhado = maioria_popular == ("SIM" if resultado_camara == "APROVADO" else "NAO")

    # Peso proporcional: quão forte foi a maioria popular
    total = voto_popular["sim"] + voto_popular["nao"]
    if total == 0:
        return 0.5
    forca = max(voto_popular["sim"], voto_popular["nao"]) / total
    return forca if alinhado else 1.0 - forca
```

### 9.8 Módulo: RAG — Busca Semântica com pgvector (`rag_service`)

O sistema usa **RAG (Retrieval-Augmented Generation)** para permitir buscas semânticas sobre proposições sincronizadas. Isso permite ao agente encontrar proposições relevantes usando linguagem natural do eleitor, sem depender de palavras-chave exatas.

**Arquitetura RAG:**

```mermaid
graph LR
    subgraph Indexação
        SYNC["Sync API Câmara"] --> PROP[("Proposição (DB)")]
        PROP --> CHUNK["Chunking"]
        CHUNK --> EMB["Embedding"]
        EMB --> PGV[("pgvector<br/>(cosine search)")]
    end

    subgraph Busca
        Q["Eleitor pergunta"] --> QEMB["Embedding da query"]
        QEMB --> COS["Cosine similarity"]
        PGV --> COS
        COS --> TOP["Top-K results"]
        TOP --> RESP["Agente responde"]
    end

    style Indexação fill:#e8f5e9,stroke:#2e7d32
    style Busca fill:#e3f2fd,stroke:#1565c0
```

**Componentes:**

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| **EmbeddingService** | `embedding_service.py` | Wrapper do Google `gemini-embedding-001` (3072 dims) |
| **RAGService** | `rag_service.py` | Indexação (chunking + embed + upsert) e busca semântica |
| **DocumentChunkRepository** | `document_chunk_repo.py` | Queries pgvector com `cosine_distance` operator |
| **DocumentChunk** | `document_chunk.py` | Modelo SQLAlchemy com coluna `Vector(3072)` |
| **rag_tools.py** | `agents/parlamentar/tools/rag_tools.py` | FunctionTools do agente: `busca_semantica_proposicoes`, `obter_estatisticas_rag` |
| **generate_embeddings.py** | `tasks/generate_embeddings.py` | Celery tasks: embedding pós-sync + reindex diário (3 AM) |

**Tipos de chunk** (`ChunkType`):
- `ementa` — Texto da ementa da proposição
- `resumo_ia` — Resumo em linguagem acessível gerado por IA
- `analise_resumo_leigo` — Análise resumida para leigos
- `analise_impacto` — Análise de impacto esperado
- `analise_argumentos` — Argumentos a favor e contra
- `tramitacao` — Última tramitação

**Deduplicação**: SHA-256 do conteúdo (`content_hash`) evita re-embedding de conteúdo idêntico.

**Pipeline de indexação**:
1. Sync Celery task baixa proposições da API Câmara.
2. Ao finalizar com sucesso, chama `generate_embeddings_task.delay()`.
3. Task extrai chunks, calcula hash, gera embeddings apenas para conteúdo novo.
4. Re-index completo agendado via Celery Beat às 3:00 AM diariamente.

**Configuração** (variáveis de ambiente / `config.py`):
- `EMBEDDING_MODEL` — Modelo de embeddings (padrão: `gemini-embedding-001`)
- `EMBEDDING_DIMENSIONS` — Dimensões do vetor (padrão: `3072`)
- `RAG_SIMILARITY_THRESHOLD` — Threshold mínimo de similaridade (padrão: `0.3`)
- `RAG_MAX_RESULTS` — Máximo de resultados por busca (padrão: `10`)

**Índice pgvector**: Busca exata por cosine distance (sem índice ANN). pgvector HNSW suporta máx. 2000 dims, e o `gemini-embedding-001` gera 3072 dims. Para o volume do projeto (milhares de chunks), busca exata é suficiente. Para escalar, considerar IVFFlat ou redução de dimensões via `output_dimensionality`.

### 9.9 Módulo: Feedback ao Eleitor

- Quando comparativo é gerado, o sistema notifica proativamente os eleitores que votaram.
- Mensagem via chat: "A PL 1234/2026 foi APROVADA pela Câmara. 73% dos eleitores queriam SIM. Alinhamento: 95%."
- O eleitor pode perguntar detalhes via conversa com o `PublicacaoAgent`.
- Histórico de comparativos acessível ao eleitor ("como foi votado X?").

---

## 10. API Interna do Backend (Endpoints Admin/Webhooks)

A API FastAPI **não é consumida por frontend** (exceto Painel do Cidadão). Serve para:
- Receber **webhooks** dos mensageiros (Telegram, WhatsApp).
- Endpoints **administrativos** para monitoramento e operações manuais.
- **RSS Feed público** para parlamentares assinarem resultados de votação popular.
- **Gestão de assinaturas** (RSS e Webhooks de saída).
- **Painel do Cidadão** — endpoints públicos e read-only consumidos pelo site.
- **Health checks** para orquestração Docker/K8s.

```
# Webhooks (recebem mensagens dos mensageiros)
POST   /webhook/telegram                     # Webhook Telegram Bot API
POST   /webhook/whatsapp                     # Webhook WhatsApp (futuro)

# RSS Feed Público (saída para parlamentares)
GET    /rss/votos                            # Feed RSS com resultados consolidados
GET    /rss/votos?tema=saude&uf=SP           # Feed filtrado por tema e/ou UF
GET    /rss/comparativos                     # Feed RSS com comparativos pop vs real

# Assinaturas (gestão de distribuição)
POST   /assinaturas/rss                      # Criar nova assinatura RSS (retorna token)
GET    /assinaturas/rss/{id}                 # Detalhes de assinatura RSS
DELETE /assinaturas/rss/{id}                 # Cancelar assinatura RSS
POST   /assinaturas/webhooks                 # Registrar novo webhook de saída
GET    /assinaturas/webhooks/{id}            # Detalhes + status de webhook
PUT    /assinaturas/webhooks/{id}            # Atualizar URL/filtros de webhook
DELETE /assinaturas/webhooks/{id}            # Remover webhook
POST   /assinaturas/webhooks/{id}/test       # Dispara payload de teste

# Admin (acesso restrito, protegido por API key)
GET    /admin/proposicoes                    # Lista proposições sincronizadas
POST   /admin/proposicoes/{id}/analisar      # Trigger análise IA manual
GET    /admin/eleitores                      # Lista eleitores cadastrados
GET    /admin/votacoes/resultado/{id}        # Resultado consolidado de votação
GET    /admin/comparativos                   # Lista comparativos pop vs real
GET    /admin/assinaturas                    # Lista todas as assinaturas ativas
GET    /admin/webhooks/log                   # Log de dispatches (sucesso/falha)

# RAG — Busca Semântica (admin tools)
GET    /admin/rag/stats                      # Estatísticas do índice vetorial
POST   /admin/rag/reindex                    # Re-indexar embeddings (single ou full)
POST   /admin/rag/search                     # Teste de busca semântica (debugging)

# Health
GET    /health                               # Health check simples
GET    /health/detailed                      # Status de DB, Redis, API Câmara

# Painel do Cidadão (público, sem auth, rate-limited)
GET    /cidadao/resumo                       # KPIs, top proposições, temas ativos, timeline 30d
GET    /cidadao/proposicoes                  # Lista paginada com filtros (tema, tipo, ano, busca)
GET    /cidadao/proposicoes/{id}             # Detalhe com análise IA + comparativo
GET    /cidadao/votos/por-tema               # Breakdown de votos por tema
GET    /cidadao/votos/timeline?dias=30       # Série temporal diária de votos
GET    /cidadao/votos/ranking?limite=10      # Ranking das proposições mais votadas
GET    /cidadao/comparativos                 # Lista paginada comparativos pop vs câmara
GET    /cidadao/comparativos/evolucao?meses=12 # Evolução mensal do alinhamento
```

---

## 11. Variáveis de Ambiente

```bash
# Banco de Dados
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/parlamentaria

# Redis
REDIS_URL=redis://localhost:6379/0

# API Câmara
CAMARA_API_BASE_URL=https://dadosabertos.camara.leg.br/api/v2
CAMARA_API_RATE_LIMIT=1.0  # requests por segundo

# Google ADK / LLM
AGENT_MODEL=gemini-2.0-flash        # modelo dos agentes (gemini, litellm/*, ollama/*)
GOOGLE_API_KEY=...                   # API key Gemini (para produção)
GOOGLE_CLOUD_PROJECT=                # projeto GCP (se usar Vertex AI)

# Telegram
TELEGRAM_BOT_TOKEN=...               # Token do @BotFather
TELEGRAM_WEBHOOK_URL=https://seu-dominio.com/webhook/telegram
TELEGRAM_WEBHOOK_SECRET=<random-32>  # Secret para validação de webhook

# WhatsApp (futuro)
WHATSAPP_API_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=

# Admin API
ADMIN_API_KEY=<random-64-chars>      # Protege endpoints admin

# Publicação (RSS + Webhooks de Saída)
RSS_BASE_URL=https://parlamentaria.app/rss  # URL base dos feeds RSS
RSS_TTL_MINUTES=15                   # TTL do cache RSS
WEBHOOK_DISPATCH_TIMEOUT=10          # Timeout (segundos) para dispatch
WEBHOOK_MAX_RETRIES=3                # Tentativas de reenvio
WEBHOOK_CIRCUIT_BREAKER_THRESHOLD=5  # Falhas para desativar assinatura

# RAG / Embeddings (pgvector)
EMBEDDING_MODEL=gemini-embedding-001   # Modelo Google Embeddings
EMBEDDING_DIMENSIONS=3072            # Dimensões do vetor
RAG_SIMILARITY_THRESHOLD=0.3         # Threshold mínimo cosine similarity
RAG_MAX_RESULTS=10                   # Máximo de resultados por busca semântica

# Engajamento / Digest
DIGEST_MAX_DAILY_NOTIFICATIONS=3    # Max notificações/dia por eleitor
DIGEST_WEEKLY_DAY=0                 # 0=segunda, 6=domingo
DIGEST_WEEKLY_HOUR=9                # Hora do envio semanal
DIGEST_DAILY_HOUR=8                 # Hora do envio diário
DIGEST_DAILY_MINUTE=30              # Minuto do envio diário
DIGEST_BATCH_SIZE=50                # Eleitores processados por lote

# App
APP_ENV=development                  # development | staging | production
APP_DEBUG=true
LOG_LEVEL=INFO

# CORS / Dashboard / Site
DASHBOARD_URL=http://localhost:3000       # URL do painel parlamentar
CIDADAO_SITE_URL=http://localhost:3001    # URL do site público (Painel do Cidadão)
CORS_EXTRA_ORIGINS=                       # Origens CORS extras (separadas por vírgula)
```

---

## 12. Padrões de Código

### 12.1 Python (Backend + Agents + Channels)

- **Estilo**: PEP 8, formatação com Ruff.
- **Tipagem**: type hints obrigatórios em todas as funções públicas.
- **Docstrings**: Google style em classes e métodos públicos.
- **Async**: usar `async/await` para I/O (DB, HTTP, Redis).
- **Validação**: Pydantic models para input/output em toda a API.
- **Exceções**: hierarquia customizada herdando de `AppException`.
- **Imports**: absolutos a partir de `app.` (ex: `from app.services.proposicao_service import ...`).
- **Nomes**: snake_case para funções/variáveis, PascalCase para classes.

```python
# Hierarquia de exceções
class AppException(Exception):
    status_code: int = 500
    detail: str = "Erro interno"

class NotFoundException(AppException):
    status_code = 404

class ValidationException(AppException):
    status_code = 422

class ExternalAPIException(AppException):
    status_code = 502
```

### 12.2 Padrões para FunctionTools (ADK)

- **Nomes claros**: o LLM usa o nome e docstring para decidir quando chamar a tool.
- **Docstrings detalhadas**: Google style com Args e Returns documentados.
- **Return dict**: sempre retornar `dict` com chave `"status"` (success/error).
- **Parâmetros simples**: preferir `str`, `int`, `bool` — evitar tipos complexos.
- **Poucos parâmetros**: minimizar número de args (o LLM decide os valores).
- **Sem side effects ocultos**: tools devem ser previsíveis e idempotentes quando possível.
- **Mensagens de erro amigáveis**: **NUNCA retornar `str(e)` diretamente** no dict de erro. \
Usar mensagens genéricas e orientativas que o agente possa repassar ao eleitor \
sem expor detalhes técnicos (nomes de modelos, endpoints, stack traces). \
Exemplo: `{"status": "error", "error": "Não foi possível buscar proposições no momento."}` \
em vez de `{"status": "error", "error": str(e)}`. O LLM pode "alucinar" detalhes \
técnicos do seu treinamento (ex: mencionar nomes de modelos internos) se receber \
mensagens de erro brutas.

---

## 13. Estratégia de Testes

### 13.1 Meta de Cobertura

- **Cobertura global mínima**: 75%
- **Cobertura de módulos críticos**: 85-90% (services, repositories, integrations, tools ADK)
- **Módulos críticos**: `services/`, `repositories/`, `integrations/`, `agents/tools/`, `channels/`
- **Ferramenta de medição**: `pytest-cov` com report em terminal e HTML
- **CI enforcement**: pipeline falha se cobertura global < 75%

### 13.2 Tipos de Teste

| Tipo                | Ferramenta              | O quê                                               | Meta Cobertura |
|---------------------|-------------------------|------------------------------------------------------|----------------|
| **Unit**            | pytest + pytest-asyncio | Services, repositories (com mock), tools ADK         | 85-90%         |
| **Integration**     | pytest + testcontainers | Routers, DB real, client API mockado                 | Fluxos críticos|
| **Agent Eval**      | ADK Evaluation          | Qualidade das respostas dos agentes (conversacional) | Todas as intents|
| **Channel**         | pytest                  | Telegram adapter, webhook processing                 | Todos os handlers|
| **Fixtures**        | JSON estáticos          | Respostas mock da API Câmara, Telegram updates       | Completo       |

### 13.3 Regras de Teste

1. **Todo service novo deve ter test file correspondente** — sem exceções.
2. **Todo repository deve ter testes com mock de session** — validar queries.
3. **Toda FunctionTool do ADK deve ter teste unitário** — validar input/output.
4. **Testes de integração cobrem fluxos end-to-end** — webhook → agent → response.
5. **Fixtures JSON para toda resposta da API Câmara** — nunca depender de API real em CI.
6. **Usar `pytest.mark` para categorizar**: `@pytest.mark.unit`, `@pytest.mark.integration`.
7. **Async tests usam `pytest-asyncio`** com `mode=auto`.
8. **Coverage report**: `pytest --cov=app --cov-report=term-missing --cov-fail-under=75`.

---

## 14. Tratamento de Erros

- Toda exceção inesperada retorna `500` com mensagem genérica (sem stack trace em prod).
- Exceções de negócio usam a hierarquia `AppException` com status code apropriado.
- Falhas na API da Câmara retornam `502 Bad Gateway` e o sistema opera com cache.
- Retry automático para chamadas à API da Câmara (3 tentativas, backoff exponencial).
- Logging estruturado (JSON) com `structlog` — inclui request_id em cada log.

### 14.1 Savepoints em Operações de Lote (Sync)

Operações de sincronização em lote (ex: `sync_proposicoes`, `sync_votacoes`) processam muitos
registros numa mesma session. Um erro em um único registro (ex: `IntegrityError`, `NotNullViolation`)
**não deve corromper** a session e impedir o processamento dos demais.

**Padrão obrigatório**: usar `session.begin_nested()` (SAVEPOINT do PostgreSQL) para isolar cada
operação individual dentro de um loop de lote:

```python
for item in itens:
    try:
        async with self.session.begin_nested():
            await self.service.upsert_from_api(item)
        stats["created"] += 1
    except Exception as e:
        logger.error("sync.upsert_error", id=item.id, error=str(e))
        stats["errors"] += 1
        # Savepoint revertido automaticamente — session continua válida
```

**Por que não usar `session.rollback()` diretamente:**
- `session.rollback()` reverte **toda** a transação, perdendo registros já persistidos.
- Com `begin_nested()`, apenas o savepoint do registro com erro é revertido.
- A session permanece em estado válido para os próximos registros.

**Nas Celery tasks**: o `session.commit()` final deve ser protegido com `try/except`:

```python
try:
    await session.commit()
except Exception:
    await session.rollback()
    logger.warning("task.commit_failed_rollback")
```

---

## 15. Segurança

- **Autenticação**: eleitores identificados pelo `chat_id` do mensageiro + verificação via conversa.
- **Verificação de identidade**: CPF e título de eleitor validados matematicamente, armazenados como hash SHA-256 (nunca em texto).
- **Privacidade**: documentos de identidade são irreversivelmente hasheados — mesmo em vazamento, números originais não podem ser recuperados.
- **Unicidade**: constraints UNIQUE em cpf_hash e titulo_eleitor_hash garantem 1 pessoa = 1 conta.
- **Admin API**: protegida por API key no header `X-API-Key`.
- **Webhook Validation**: validar assinatura/secret dos webhooks Telegram/WhatsApp.
- **Rate limiting**: aplicar no backend com `slowapi` (por chat_id e por IP).
- **Input validation**: Pydantic valida 100% dos inputs na borda.
- **SQL Injection**: prevenido nativamente pelo SQLAlchemy.
- **Secrets**: nunca commitar. Usar `.env` local e secrets do CI/CD em prod.
- **HTTPS**: obrigatório em staging e produção (webhooks exigem HTTPS).

---

## 16. Docker & Deploy

### 16.1 Docker Compose (desenvolvimento)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db, redis]
    volumes:
      - ./agents:/app/agents        # Hot-reload dos agentes ADK
      - ./channels:/app/channels    # Hot-reload dos channel adapters

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: parlamentaria
      POSTGRES_USER: parlamentaria
      POSTGRES_PASSWORD: parlamentaria
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  celery-worker:
    build: ./backend
    command: celery -A app.tasks worker -l info
    env_file: .env
    depends_on: [db, redis]

  celery-beat:
    build: ./backend
    command: celery -A app.tasks beat -l info
    env_file: .env
    depends_on: [redis]

volumes:
  pgdata:
```

### 16.2 Deploy Produção

- Imagens Docker multi-stage para builds otimizados.
- Backend serve via Uvicorn com Gunicorn (workers = 2 * CPU + 1).
- PostgreSQL gerenciado (ex: RDS, Cloud SQL, Supabase).
- Redis gerenciado (ex: ElastiCache, Upstash).
- Webhook HTTPS obrigatório para Telegram Bot API.
- Opção: deploy dos agentes via Google Cloud Run ou Vertex AI Agent Engine.

---

## 17. Workflow de Desenvolvimento

### 17.1 Sequência de Implementação (prioridade)

```
Fase 1 — Fundação
  ├── Setup do projeto (monorepo, Docker, CI)
  ├── Config FastAPI + PostgreSQL + Alembic
  ├── CamaraClient (integração HTTP)
  └── Modelos de domínio + migrations

Fase 2 — Core Backend
  ├── Repositories + Services (proposições, votações)
  ├── Sincronização com API da Câmara (Celery)
  ├── Routers admin/health
  └── Testes unitários

Fase 3 — Agentes (Google ADK)
  ├── Root Agent (ParlamentarAgent)
  ├── ProposicaoAgent + tools
  ├── VotacaoAgent + tools
  ├── DeputadoAgent + tools
  ├── EleitorAgent + tools
  ├── Sessions + State management
  └── Testes de agentes (ADK eval)

Fase 4 — Canal Telegram
  ├── Telegram Bot + webhook
  ├── TelegramAdapter (ChannelAdapter)
  ├── Inline Keyboards (votação, navegação)
  ├── Integração Telegram ↔ ADK Runner
  └── Testes de canal

Fase 5 — Votação Popular
  ├── Fluxo de votação via chat
  ├── Consolidação de resultados
  ├── Notificações proativas (Celery)
  └── Testes de integração

Fase 6 — Publicação e Distribuição
  ├── RSS/Atom Feed (endpoint público)
  ├── Assinaturas RSS (token, filtros)
  ├── Webhooks de saída (dispatch + HMAC)
  ├── PublicacaoAgent + tools
  └── Testes de publicação

Fase 7 — Comparativo e Feedback
  ├── Comparativo voto popular vs real
  ├── Feedback proativo ao eleitor
  ├── Publicação de comparativos (RSS + Webhooks)
  └── Testes de ciclo completo

Fase 8 — Polimento
  ├── Monitoring + health checks
  ├── Rate limiting + segurança
  ├── ADK Evaluation (qualidade das respostas)
  ├── Deploy produção
  └── Canal WhatsApp (stub → implementação)
```

### 17.2 Convenções Git

- **Branch**: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`
- **Commits**: Conventional Commits (`feat: ...`, `fix: ...`, `refactor: ...`)
- **PR**: sempre com descrição, linked issue, review obrigatório.
- **Main**: protegida, deploy automático via CI/CD.

---

## 18. Regras para Agentes IA

> **LEIA ESTA SEÇÃO ANTES DE GERAR QUALQUER CÓDIGO.**

1. **Siga este AGENTS.md como fonte de verdade** para arquitetura, padrões e estrutura.
2. **Não crie arquivos fora da estrutura definida** na seção 4 sem justificativa explícita.
3. **Sempre use tipagem completa** em Python — type hints obrigatórios.
4. **Nunca hardcode** URLs, credenciais ou configurações — use variáveis de ambiente.
5. **Todo serviço deve ter testes** — crie testes junto com a implementação.
6. **Use async/await** para toda operação de I/O no backend.
7. **Siga os Design Patterns** da seção 3.4 — Multi-Agent, Channel Adapter, Repository, Service, FunctionTool, DTO.
8. **Respostas da API da Câmara mudam** — sempre trate campos opcionais com `| None`.
9. **Commits devem ser atômicos** — uma feature/fix por commit.
10. **Não existe frontend web** — toda interação do eleitor é via agentes + mensageiros.
11. **FunctionTools devem ser simples** — poucos parâmetros, return dict, docstrings claras.
12. **FunctionTools nunca retornam `str(e)`** — erros devem usar mensagens amigáveis (ver seção 12.2).
13. **Prompts dos agentes proíbem expor internos** — nomes de modelos, endpoints, tools, erros técnicos.
14. **Ante qualquer dúvida**, consulte a seção relevante deste AGENTS.md.


