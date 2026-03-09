# Parlamentaria — Schema do Banco de Dados

> PostgreSQL 16 com extensão pgvector para busca semântica vetorial.

---

## 1. Visão Geral

O banco possui **13 tabelas** organizadas em domínios funcionais:

| Domínio | Tabelas | Descrição |
|---------|---------|-----------|
| **Legislativo** | `proposicoes`, `votacoes`, `deputados`, `partidos`, `eventos` | Dados sincronizados da API da Câmara |
| **Análise IA** | `analises_ia` | Análises geradas por LLM |
| **Eleitores** | `eleitores`, `votos_populares` | Cadastro e votação popular |
| **Publicação** | `assinaturas_rss`, `assinaturas_webhooks`, `comparativos_votacao` | Distribuição de resultados |
| **RAG** | `document_chunks` | Embeddings vetoriais para busca semântica |
| **Dashboard** | `parlamentar_users` | Autenticação de parlamentares |

---

## 2. Diagrama ER (Entidade-Relacionamento)

```mermaid
erDiagram
    proposicoes ||--o{ analises_ia : "tem análises"
    proposicoes ||--o{ votos_populares : "recebe votos"
    proposicoes ||--o{ document_chunks : "tem chunks"
    proposicoes ||--o{ comparativos_votacao : "comparado em"
    votacoes }o--|| proposicoes : "sobre"
    votacoes ||--o{ comparativos_votacao : "resultado real"
    eleitores ||--o{ votos_populares : "vota em"
    deputados ||--o{ parlamentar_users : "vinculado a"

    proposicoes {
        int id PK "ID da API Câmara"
        varchar tipo "PL, PEC, MPV, PLP"
        int numero
        int ano
        text ementa
        varchar texto_completo_url
        date data_apresentacao
        varchar situacao
        text[] temas "ARRAY"
        jsonb autores "JSON"
        text resumo_ia
        timestamptz ultima_sincronizacao
        timestamptz created_at
        timestamptz updated_at
    }

    votacoes {
        varchar id PK "ID da API Câmara"
        int proposicao_id FK
        timestamptz data
        text descricao
        boolean aprovacao
        int votos_sim
        int votos_nao
        int abstencoes
        jsonb orientacoes
        jsonb votos_parlamentares
        timestamptz created_at
        timestamptz updated_at
    }

    eleitores {
        uuid id PK
        varchar nome
        varchar email UK
        varchar uf "2 chars"
        varchar chat_id UK
        varchar channel "telegram/whatsapp"
        boolean verificado
        text[] temas_interesse
        date data_nascimento
        boolean cidadao_brasileiro
        varchar cpf_hash UK "SHA-256 (64 chars)"
        varchar titulo_eleitor_hash UK "SHA-256 (64 chars)"
        enum nivel_verificacao "NAO_VERIFICADO/AUTO_DECLARADO/VERIFICADO_TITULO"
        enum frequencia_notificacao "IMEDIATA/DIARIA/SEMANAL/DESATIVADA"
        int horario_preferido_notificacao "0-23"
        timestamptz ultimo_digest_enviado
        timestamptz data_cadastro
        timestamptz updated_at
    }

    votos_populares {
        uuid id PK
        uuid eleitor_id FK
        int proposicao_id FK
        enum voto "SIM/NAO/ABSTENCAO"
        enum tipo_voto "OFICIAL/OPINIAO"
        text justificativa
        timestamptz data_voto
    }

    analises_ia {
        uuid id PK
        int proposicao_id FK
        text resumo_leigo
        text impacto_esperado
        text[] areas_afetadas
        text[] argumentos_favor
        text[] argumentos_contra
        varchar provedor_llm
        varchar modelo
        timestamptz data_geracao
        int versao
    }

    deputados {
        int id PK "ID da API Câmara"
        varchar nome
        varchar nome_civil
        varchar sigla_partido
        varchar sigla_uf
        varchar foto_url
        varchar email
        varchar situacao
        jsonb dados_extras
        timestamptz created_at
        timestamptz updated_at
    }

    eventos {
        int id PK "ID da API Câmara"
        text descricao
        varchar tipo_evento
        timestamptz data_inicio
        timestamptz data_fim
        varchar local
        varchar situacao
        jsonb pauta
        timestamptz created_at
    }

    partidos {
        int id PK "ID da API Câmara"
        varchar sigla UK
        varchar nome
        timestamptz created_at
    }

    assinaturas_rss {
        uuid id PK
        varchar nome
        varchar email
        varchar token UK "64 chars"
        text[] filtro_temas
        varchar filtro_uf
        boolean ativo
        timestamptz data_criacao
        timestamptz ultimo_acesso
    }

    assinaturas_webhooks {
        uuid id PK
        varchar nome
        varchar url "HTTPS"
        varchar secret "HMAC"
        text[] eventos "voto_consolidado/comparativo"
        text[] filtro_temas
        boolean ativo
        timestamptz data_criacao
        timestamptz ultimo_dispatch
        int falhas_consecutivas "circuit breaker"
    }

    comparativos_votacao {
        uuid id PK
        int proposicao_id FK
        varchar votacao_camara_id FK
        int voto_popular_sim
        int voto_popular_nao
        int voto_popular_abstencao
        varchar resultado_camara "APROVADO/REJEITADO"
        int votos_camara_sim
        int votos_camara_nao
        float alinhamento "0.0 a 1.0"
        text resumo_ia
        timestamptz data_geracao
    }

    document_chunks {
        uuid id PK
        int proposicao_id FK "CASCADE"
        varchar chunk_type "ementa/resumo_ia/analise/etc"
        text content
        varchar content_hash "SHA-256"
        vector embedding "3072 dims"
        text metadata_extra "JSON string"
        varchar embedding_model
        timestamptz created_at
        timestamptz updated_at
    }

    parlamentar_users {
        uuid id PK
        int deputado_id FK "SET NULL"
        varchar email UK
        varchar nome
        varchar cargo
        enum tipo "DEPUTADO/ASSESSOR/LIDERANCA"
        boolean ativo
        varchar codigo_convite UK
        boolean convite_usado
        timestamptz ultimo_login
        text[] temas_acompanhados
        boolean notificacoes_email
        varchar refresh_token_hash
        timestamptz created_at
        timestamptz updated_at
    }
```

---

## 3. Detalhamento por Tabela

### 3.1 `proposicoes` — Proposições Legislativas

Armazena proposições legislativas sincronizadas da API Dados Abertos da Câmara.

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `id` | `INTEGER` | **PK** | — | ID da API Câmara (não auto-incrementado) |
| `tipo` | `VARCHAR(20)` | NOT NULL | — | Tipo: PL, PEC, MPV, PLP, etc. |
| `numero` | `INTEGER` | NOT NULL | — | Número da proposição |
| `ano` | `INTEGER` | NOT NULL | — | Ano de apresentação |
| `ementa` | `TEXT` | NOT NULL | — | Texto da ementa |
| `texto_completo_url` | `VARCHAR(500)` | NULL | — | URL do texto integral |
| `data_apresentacao` | `DATE` | NULL | — | Data de apresentação |
| `situacao` | `VARCHAR(200)` | NOT NULL | `'Em tramitação'` | Situação atual |
| `temas` | `TEXT[]` | NULL | — | Array de temas (PostgreSQL ARRAY) |
| `autores` | `JSONB` | NULL | — | Lista de autores (JSON) |
| `resumo_ia` | `TEXT` | NULL | — | Resumo gerado por IA |
| `ultima_sincronizacao` | `TIMESTAMPTZ` | NOT NULL | `now()` | Última sincronização |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Criação |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Última atualização |

**Relacionamentos:**
- `analises_ia` (1:N) — Análises IA da proposição
- `votos_populares` (1:N) — Votos populares recebidos
- `document_chunks` (1:N, CASCADE) — Chunks vetorizados para RAG

---

### 3.2 `votacoes` — Votações Parlamentares

Votações reais ocorridas na Câmara dos Deputados.

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `id` | `VARCHAR(50)` | **PK** | — | ID da API Câmara (string) |
| `proposicao_id` | `INTEGER` | NULL | — | FK → `proposicoes.id` |
| `data` | `TIMESTAMPTZ` | NOT NULL | — | Data/hora da votação |
| `descricao` | `TEXT` | NOT NULL | — | Descrição da votação |
| `aprovacao` | `BOOLEAN` | NULL | — | Se foi aprovada |
| `votos_sim` | `INTEGER` | NOT NULL | `0` | Total de votos SIM |
| `votos_nao` | `INTEGER` | NOT NULL | `0` | Total de votos NÃO |
| `abstencoes` | `INTEGER` | NOT NULL | `0` | Total de abstenções |
| `orientacoes` | `JSONB` | NULL | — | Orientações de bancada |
| `votos_parlamentares` | `JSONB` | NULL | — | Votos individuais |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Criação |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Última atualização |

---

### 3.3 `eleitores` — Eleitores Cadastrados

Eleitores registrados na plataforma com sistema de verificação progressiva.

| Coluna | Tipo | Nullable | Constraints | Descrição |
|--------|------|----------|-------------|-----------|
| `id` | `UUID` | **PK** | `uuid4()` | Identificador único |
| `nome` | `VARCHAR(200)` | NOT NULL | — | Nome completo |
| `email` | `VARCHAR(300)` | NOT NULL | **UNIQUE** | Email do eleitor |
| `uf` | `VARCHAR(2)` | NOT NULL | — | Sigla do estado |
| `chat_id` | `VARCHAR(100)` | NULL | **UNIQUE** | ID do chat Telegram |
| `channel` | `VARCHAR(20)` | NOT NULL | `'telegram'` | Canal de mensageria |
| `verificado` | `BOOLEAN` | NOT NULL | `false` | Se está verificado |
| `temas_interesse` | `TEXT[]` | NULL | — | Temas de interesse |
| `data_nascimento` | `DATE` | NULL | — | Para cálculo de idade |
| `cidadao_brasileiro` | `BOOLEAN` | NOT NULL | `false` | Autodeclaração |
| `cpf_hash` | `VARCHAR(64)` | NULL | **UNIQUE** | SHA-256 do CPF |
| `titulo_eleitor_hash` | `VARCHAR(64)` | NULL | **UNIQUE** | SHA-256 do título |
| `nivel_verificacao` | `ENUM` | NOT NULL | `NAO_VERIFICADO` | Nível progressivo |
| `frequencia_notificacao` | `ENUM` | NOT NULL | `SEMANAL` | Frequência de digest |
| `horario_preferido_notificacao` | `INTEGER` | NOT NULL | `9` | Hora (0-23) |
| `ultimo_digest_enviado` | `TIMESTAMPTZ` | NULL | — | Anti-duplicação |
| `data_cadastro` | `TIMESTAMPTZ` | NOT NULL | `now()` | Criação |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Última atualização |

**Enums:**
- `NivelVerificacao`: `NAO_VERIFICADO` | `AUTO_DECLARADO` | `VERIFICADO_TITULO`
- `FrequenciaNotificacao`: `IMEDIATA` | `DIARIA` | `SEMANAL` | `DESATIVADA`

**Propriedades computadas (Python):**
- `idade` — Calcula idade a partir de `data_nascimento`
- `elegivel` — Brasileiro, 16+, CPF registrado, nível ≥ AUTO_DECLARADO

---

### 3.4 `votos_populares` — Votos Populares

Votos dos eleitores em proposições legislativas.

| Coluna | Tipo | Nullable | Constraints | Descrição |
|--------|------|----------|-------------|-----------|
| `id` | `UUID` | **PK** | `uuid4()` | Identificador único |
| `eleitor_id` | `UUID` | NOT NULL | FK → `eleitores.id` | Eleitor que votou |
| `proposicao_id` | `INTEGER` | NOT NULL | FK → `proposicoes.id` | Proposição votada |
| `voto` | `ENUM` | NOT NULL | — | SIM / NAO / ABSTENCAO |
| `tipo_voto` | `ENUM` | NOT NULL | `OPINIAO` | OFICIAL ou OPINIAO |
| `justificativa` | `TEXT` | NULL | — | Justificativa opcional |
| `data_voto` | `TIMESTAMPTZ` | NOT NULL | `now()` | Momento do voto |

**Constraints:**
- `UNIQUE(eleitor_id, proposicao_id)` — 1 voto por eleitor por proposição

**Enums:**
- `VotoEnum`: `SIM` | `NAO` | `ABSTENCAO`
- `TipoVoto`: `OFICIAL` (eleitor elegível) | `OPINIAO` (consultivo)

---

### 3.5 `analises_ia` — Análises por IA

Análises geradas por LLM vinculadas a proposições.

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | `UUID` | **PK** | Identificador único |
| `proposicao_id` | `INTEGER` | NOT NULL | FK → `proposicoes.id` |
| `resumo_leigo` | `TEXT` | NOT NULL | Resumo em linguagem acessível |
| `impacto_esperado` | `TEXT` | NOT NULL | Análise de impacto |
| `areas_afetadas` | `TEXT[]` | NOT NULL | Áreas impactadas |
| `argumentos_favor` | `TEXT[]` | NOT NULL | Argumentos a favor |
| `argumentos_contra` | `TEXT[]` | NOT NULL | Argumentos contra |
| `provedor_llm` | `VARCHAR(50)` | NOT NULL | Provider (ex: google) |
| `modelo` | `VARCHAR(100)` | NOT NULL | Modelo utilizado |
| `data_geracao` | `TIMESTAMPTZ` | NOT NULL | Quando foi gerada |
| `versao` | `INTEGER` | NOT NULL | `1` — Permite re-análise |

---

### 3.6 `deputados` — Deputados Federais

Deputados sincronizados da API da Câmara.

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | `INTEGER` | **PK** | ID da API Câmara |
| `nome` | `VARCHAR(200)` | NOT NULL | Nome parlamentar |
| `nome_civil` | `VARCHAR(300)` | NULL | Nome civil completo |
| `sigla_partido` | `VARCHAR(20)` | NULL | Sigla do partido |
| `sigla_uf` | `VARCHAR(2)` | NULL | Estado (UF) |
| `foto_url` | `VARCHAR(500)` | NULL | URL da foto |
| `email` | `VARCHAR(200)` | NULL | Email institucional |
| `situacao` | `VARCHAR(100)` | NULL | Exercício, licença, etc. |
| `dados_extras` | `JSONB` | NULL | Dados adicionais |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Criação |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Última atualização |

---

### 3.7 `eventos` — Eventos do Plenário

Sessões plenárias, audiências e reuniões.

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | `INTEGER` | **PK** | ID da API Câmara |
| `descricao` | `TEXT` | NOT NULL | Descrição do evento |
| `tipo_evento` | `VARCHAR(100)` | NULL | Tipo (sessão, audiência, etc.) |
| `data_inicio` | `TIMESTAMPTZ` | NOT NULL | Início do evento |
| `data_fim` | `TIMESTAMPTZ` | NULL | Fim do evento |
| `local` | `VARCHAR(200)` | NULL | Local do evento |
| `situacao` | `VARCHAR(100)` | NULL | Situação (agendado, etc.) |
| `pauta` | `JSONB` | NULL | Itens em pauta |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Criação |

---

### 3.8 `partidos` — Partidos Políticos

| Coluna | Tipo | Nullable | Constraints | Descrição |
|--------|------|----------|-------------|-----------|
| `id` | `INTEGER` | **PK** | — | ID da API Câmara |
| `sigla` | `VARCHAR(20)` | NOT NULL | **UNIQUE** | Sigla (PT, PL, etc.) |
| `nome` | `VARCHAR(200)` | NOT NULL | — | Nome completo |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Criação |

---

### 3.9 `assinaturas_rss` — Assinaturas RSS

Assinaturas de feeds RSS para parlamentares e organizações.

| Coluna | Tipo | Nullable | Constraints | Descrição |
|--------|------|----------|-------------|-----------|
| `id` | `UUID` | **PK** | — | Identificador |
| `nome` | `VARCHAR(200)` | NOT NULL | — | Nome do assinante |
| `email` | `VARCHAR(300)` | NULL | — | Email de contato |
| `token` | `VARCHAR(64)` | NOT NULL | **UNIQUE** | Token de acesso |
| `filtro_temas` | `TEXT[]` | NULL | — | Filtro por temas |
| `filtro_uf` | `VARCHAR(2)` | NULL | — | Filtro por UF |
| `ativo` | `BOOLEAN` | NOT NULL | `true` | Ativo/inativo |
| `data_criacao` | `TIMESTAMPTZ` | NOT NULL | `now()` | Criação |
| `ultimo_acesso` | `TIMESTAMPTZ` | NULL | — | Último acesso ao feed |

---

### 3.10 `assinaturas_webhooks` — Webhooks de Saída

Webhooks registrados por sistemas externos para receber notificações push.

| Coluna | Tipo | Nullable | Constraints | Descrição |
|--------|------|----------|-------------|-----------|
| `id` | `UUID` | **PK** | — | Identificador |
| `nome` | `VARCHAR(200)` | NOT NULL | — | Nome do sistema |
| `url` | `VARCHAR(500)` | NOT NULL | — | URL de callback (HTTPS) |
| `secret` | `VARCHAR(128)` | NOT NULL | — | HMAC secret |
| `eventos` | `TEXT[]` | NOT NULL | — | Tipos de evento |
| `filtro_temas` | `TEXT[]` | NULL | — | Filtro por temas |
| `ativo` | `BOOLEAN` | NOT NULL | `true` | Ativo/inativo |
| `data_criacao` | `TIMESTAMPTZ` | NOT NULL | `now()` | Criação |
| `ultimo_dispatch` | `TIMESTAMPTZ` | NULL | — | Último envio |
| `falhas_consecutivas` | `INTEGER` | NOT NULL | `0` | Circuit breaker |

**Circuit Breaker:** Após 5 falhas consecutivas, a assinatura é desativada automaticamente.

---

### 3.11 `comparativos_votacao` — Comparativos Pop vs Real

Comparação entre votação popular e resultado parlamentar real.

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | `UUID` | **PK** | Identificador |
| `proposicao_id` | `INTEGER` | NOT NULL | FK → `proposicoes.id` |
| `votacao_camara_id` | `VARCHAR(50)` | NOT NULL | FK → `votacoes.id` |
| `voto_popular_sim` | `INTEGER` | NOT NULL | Total votos SIM popular |
| `voto_popular_nao` | `INTEGER` | NOT NULL | Total votos NÃO popular |
| `voto_popular_abstencao` | `INTEGER` | NOT NULL | Total abstenções |
| `resultado_camara` | `VARCHAR(20)` | NOT NULL | APROVADO / REJEITADO |
| `votos_camara_sim` | `INTEGER` | NOT NULL | Votos SIM na Câmara |
| `votos_camara_nao` | `INTEGER` | NOT NULL | Votos NÃO na Câmara |
| `alinhamento` | `FLOAT` | NOT NULL | 0.0 (divergência) a 1.0 (alinhamento) |
| `resumo_ia` | `TEXT` | NULL | Análise IA do comparativo |
| `data_geracao` | `TIMESTAMPTZ` | NOT NULL | Quando foi gerado |

---

### 3.12 `document_chunks` — Chunks Vetoriais (RAG)

Chunks de texto com embeddings vetoriais para busca semântica via pgvector.

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | `UUID` | **PK** | Identificador |
| `proposicao_id` | `INTEGER` | NOT NULL | FK → `proposicoes.id` (CASCADE) |
| `chunk_type` | `VARCHAR(50)` | NOT NULL | Tipo: ementa, resumo_ia, analise, etc. |
| `content` | `TEXT` | NOT NULL | Texto original do chunk |
| `content_hash` | `VARCHAR(64)` | NOT NULL | SHA-256 para deduplicação |
| `embedding` | `VECTOR(3072)` | NOT NULL | Vetor do gemini-embedding-001 |
| `metadata_extra` | `TEXT` | NULL | Metadados extras (JSON string) |
| `embedding_model` | `VARCHAR(100)` | NOT NULL | Modelo gerador do embedding |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Criação |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | Última atualização |

**Tipos de chunk (`chunk_type`):**
| Tipo | Descrição |
|------|-----------|
| `ementa` | Texto da ementa da proposição |
| `resumo_ia` | Resumo em linguagem acessível gerado por IA |
| `analise_resumo_leigo` | Análise resumida para leigos |
| `analise_impacto` | Análise de impacto esperado |
| `analise_argumentos` | Argumentos a favor e contra |
| `tramitacao` | Última tramitação |

**Busca:** Cosine distance (busca exata, sem índice ANN — adequado para o volume do projeto).

---

### 3.13 `parlamentar_users` — Usuários do Dashboard

Usuários que acessam o dashboard parlamentar (deputados, assessores, lideranças).

| Coluna | Tipo | Nullable | Constraints | Descrição |
|--------|------|----------|-------------|-----------|
| `id` | `UUID` | **PK** | — | Identificador |
| `deputado_id` | `INTEGER` | NULL | FK → `deputados.id` (SET NULL) | Deputado vinculado |
| `email` | `VARCHAR(200)` | NOT NULL | **UNIQUE** | Email institucional |
| `nome` | `VARCHAR(300)` | NOT NULL | — | Nome completo |
| `cargo` | `VARCHAR(200)` | NULL | — | Cargo descritivo |
| `tipo` | `ENUM` | NOT NULL | `ASSESSOR` | Tipo de usuário |
| `ativo` | `BOOLEAN` | NOT NULL | `true` | Ativo/inativo |
| `codigo_convite` | `VARCHAR(64)` | NULL | **UNIQUE** | Código de primeiro acesso |
| `convite_usado` | `BOOLEAN` | NOT NULL | `false` | Se convite foi usado |
| `ultimo_login` | `TIMESTAMPTZ` | NULL | — | Último login |
| `temas_acompanhados` | `TEXT[]` | NULL | — | Temas de interesse |
| `notificacoes_email` | `BOOLEAN` | NOT NULL | `true` | Recebe emails |
| `refresh_token_hash` | `VARCHAR(128)` | NULL | — | Hash do refresh token |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Criação |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Última atualização |

**Enum `TipoParlamentarUser`:** `DEPUTADO` | `ASSESSOR` | `LIDERANCA`

---

## 4. Relacionamentos entre Tabelas

```mermaid
graph LR
    P["proposicoes"] --> A["analises_ia"]
    P --> VP["votos_populares"]
    P --> DC["document_chunks"]
    P --> CV["comparativos_votacao"]
    V["votacoes"] --> P
    V --> CV
    EL["eleitores"] --> VP
    D["deputados"] --> PU["parlamentar_users"]

    style P fill:#e3f2fd,stroke:#1565c0
    style V fill:#e3f2fd,stroke:#1565c0
    style EL fill:#fff3e0,stroke:#ef6c00
    style D fill:#e3f2fd,stroke:#1565c0
```

### Chaves Estrangeiras

| Tabela Origem | Coluna | → Tabela Destino | Coluna | On Delete |
|---------------|--------|------------------|--------|-----------|
| `votacoes` | `proposicao_id` | `proposicoes` | `id` | — |
| `votos_populares` | `eleitor_id` | `eleitores` | `id` | — |
| `votos_populares` | `proposicao_id` | `proposicoes` | `id` | — |
| `analises_ia` | `proposicao_id` | `proposicoes` | `id` | — |
| `comparativos_votacao` | `proposicao_id` | `proposicoes` | `id` | — |
| `comparativos_votacao` | `votacao_camara_id` | `votacoes` | `id` | — |
| `document_chunks` | `proposicao_id` | `proposicoes` | `id` | CASCADE |
| `parlamentar_users` | `deputado_id` | `deputados` | `id` | SET NULL |

---

## 5. Extensões PostgreSQL

| Extensão | Uso |
|----------|-----|
| **pgvector** | Tipo `VECTOR(3072)` para embeddings, operador de cosine distance |
| **uuid-ossp** | Geração de UUIDs (via SQLAlchemy `uuid4()`) |

---

## 6. Índices Notáveis

| Tabela | Coluna(s) | Tipo | Motivo |
|--------|-----------|------|--------|
| `eleitores` | `email` | UNIQUE | Busca por email |
| `eleitores` | `chat_id` | UNIQUE | Lookup por Telegram ID |
| `eleitores` | `cpf_hash` | UNIQUE | 1 CPF = 1 conta |
| `eleitores` | `titulo_eleitor_hash` | UNIQUE | 1 título = 1 conta |
| `partidos` | `sigla` | UNIQUE | Busca por sigla |
| `votos_populares` | `(eleitor_id, proposicao_id)` | UNIQUE | 1 voto por proposição |
| `document_chunks` | `proposicao_id` | INDEX | Busca de chunks por proposição |
| `parlamentar_users` | `email` | UNIQUE + INDEX | Login por email |
| `parlamentar_users` | `deputado_id` | INDEX | Vincular ao deputado |
| `assinaturas_rss` | `token` | UNIQUE | Autenticação por token |
| `assinaturas_webhooks` | — | — | — |

---

## 7. Migrations (Alembic)

As migrations são gerenciadas pelo Alembic e estão em `backend/alembic/versions/`:

| Migration | Descrição |
|-----------|-----------|
| `0001_initial` | Criação das tabelas base (proposicoes, votacoes, deputados, etc.) |
| `0002_add_pgvector_rag` | Extensão pgvector + tabela document_chunks |
| `0003_add_eleitor_eligibility_and_voto_tipo` | Campos de elegibilidade e tipo de voto |
| `0004_add_verification_fields` | CPF hash, título hash, nível de verificação |
| `0005_nullable_data_apresentacao` | Torna data_apresentacao nullable |
| `0006_embedding_3072_dimensions` | Atualiza vetor para 3072 dimensões |
| `0007_votacao_id_string` | ID de votação muda de int para varchar |
| `0008_align_eventos_columns` | Alinhamento de colunas na tabela eventos |
| `0009_add_notification_preferences` | Campos de frequência e horário de notificação |
| `0010_add_parlamentar_users_table` | Tabela de usuários do dashboard |

### Executar migrations

```bash
# Aplicar todas as migrations pendentes
cd backend && alembic upgrade head

# Criar nova migration
alembic revision --autogenerate -m "descricao_da_mudanca"

# Reverter última migration
alembic downgrade -1
```

---

## 8. Configuração de Conexão

```python
# backend/app/db/session.py
engine = create_async_engine(
    settings.database_url,        # postgresql+asyncpg://user:pass@host:5432/parlamentaria
    echo=settings.app_debug,      # Log de SQL em dev
    pool_pre_ping=True,           # Verifica conexão antes de usar
    pool_size=10,                 # Pool de conexões
    max_overflow=20,              # Conexões extras além do pool
)
```

**Variável de ambiente:**
```bash
DATABASE_URL=postgresql+asyncpg://parlamentaria:parlamentaria@db:5432/parlamentaria
```
