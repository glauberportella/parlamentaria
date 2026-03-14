# Raio-X do Deputado — Plano de Aprimoramento

> Feature que responde à pergunta central do eleitor: **"Meu deputado está me representando bem?"**

---

## 1. Estado Atual

O `DeputadoAgent` hoje possui **4 tools** que cobrem funcionalidades básicas:

| Tool existente | Endpoint usado | O que faz |
|---|---|---|
| `buscar_deputado` | `GET /deputados` | Busca por nome/UF/partido |
| `obter_perfil_deputado` | `GET /deputados/{id}` | Perfil básico (nome, partido, UF, foto) |
| `obter_despesas_deputado` | `GET /deputados/{id}/despesas` | Cota parlamentar |
| `obter_votos_parlamentares` | `GET /votacoes/{id}/votos` | Votos individuais (por votação, não por deputado) |

---

## 2. Endpoints Disponíveis Não Explorados

| Endpoint | Valor p/ Eleitor | Estratégia |
|---|:---:|---|
| `GET /deputados/{id}/discursos` | **ALTO** | **RAG** — indexar discursos para busca semântica |
| `GET /deputados/{id}/orgaos` | **ALTO** | **API direta** — comissões e áreas de influência |
| `GET /deputados/{id}/frentes` | **ALTO** | **API direta** — frentes parlamentares e causas |
| `GET /deputados/{id}/eventos` | **MÉDIO-ALTO** | **API direta + agregação** — presença e participação |
| `GET /deputados/{id}/profissoes` | **MÉDIO** | **API direta** — formação profissional |
| `GET /deputados/{id}/historico` | **MÉDIO** | **API direta** — mudanças de partido, licenças |
| `GET /deputados/{id}/mandatosExternos` | **BAIXO-MÉDIO** | **API direta** — carreira política prévia |
| `GET /deputados/{id}/ocupacoes` | **BAIXO** | **API direta** — empregos anteriores |

---

## 3. Classificação: RAG vs API Direta

### RAG (indexação com embeddings para busca semântica)

- **Discursos** — Volume alto de texto, eleitor quer buscar por tema/assunto, não por ID.
  Perguntas como *"O que meu deputado disse sobre reforma tributária?"* exigem busca semântica.
  Chunk por discurso, indexar no pgvector.

### API direta (consultas on-demand)

- **Órgãos, Frentes, Eventos, Profissões, Histórico, Mandatos, Ocupações** — Dados estruturados,
  listas curtas, que mudam pouco. Não precisam de embedding. Uma chamada à API é suficiente e
  o agente formata a resposta.

---

## 4. Feature: Raio-X do Deputado

O **Raio-X** combina múltiplos dados em um perfil enriquecido + busca semântica sobre discursos.

### 4.1 Perfil Enriquecido (API direta)

O eleitor pergunta *"me fala sobre o deputado Fulano"* e recebe:

- Dados básicos (partido, UF, foto, gabinete)
- **Comissões** em que atua (órgãos) — mostra áreas de influência
- **Frentes parlamentares** — mostra bandeiras que defende
- **Formação/profissão** — contexto profissional
- **Histórico parlamentar** — mudanças de partido, licenças

### 4.2 Transparência Financeira (API direta — enriquecer o existente)

- Despesas da cota parlamentar (já existe)
- **Ranking de gastos** — comparar com média dos deputados do mesmo estado/partido
- Evolução mensal dos gastos

### 4.3 Participação e Presença (API direta + agregação)

- **Eventos que participou** — quantos, tipos (audiências, sessões deliberativas)
- **Taxa de presença estimada** — proporção entre eventos do órgão e participações
- Últimos eventos que participou

### 4.4 Discursos — Busca Semântica (RAG)

Esta é a parte mais diferenciadora:

- **Sync periódica** dos discursos via `GET /deputados/{id}/discursos`
- **Chunking e embedding** de cada discurso no pgvector
- **Tool `buscar_discursos_deputado`** — o eleitor pergunta por tema:
  *"O que a deputada Maria disse sobre educação?"*
- **Nuvem de temas** — temas mais discursados pelo deputado (agregação)

### 4.5 Alinhamento com Voto Popular (dados internos)

- Pegar votações em que o deputado votou E que tiveram voto popular
- Calcular **índice de alinhamento pessoal** do deputado com a maioria popular
- *"O deputado Fulano votou junto com a maioria popular em 73% das vezes"*

---

## 5. Implementação — Artefatos por Camada

| Camada | Artefato | Trabalho |
|---|---|---|
| **Integration** | `camara_client.py` | Adicionar métodos: `obter_discursos()`, `obter_orgaos_deputado()`, `obter_frentes()`, `obter_eventos_deputado()`, `obter_profissoes()`, `obter_historico()` |
| **Types** | `camara_types.py` | Novos modelos: `DiscursoAPI`, `OrgaoDeputadoAPI`, `FrenteAPI`, `ProfissaoAPI`, `HistoricoAPI`, `MandatoExternoAPI` |
| **Domain** | Novo: `domain/discurso.py` | Modelo SQLAlchemy para persistir discursos (para RAG) |
| **Repository** | Novo: `repositories/discurso_repo.py` | CRUD de discursos |
| **Service** | Novo: `services/discurso_service.py` | Lógica de sync + indexação RAG de discursos |
| **Service** | Enriquecer `deputado_service.py` | Método `gerar_raio_x()` que agrega todos os dados |
| **RAG** | Enriquecer `rag_service.py` | Novo `ChunkType.discurso`, indexação de discursos |
| **Tasks** | Novo: `tasks/sync_discursos.py` | Celery task periódica para sync de discursos |
| **Tools** | Enriquecer `camara_tools.py` | Novas tools: `obter_raio_x_deputado`, `buscar_discursos_deputado`, `obter_comissoes_deputado`, `obter_frentes_deputado`, `obter_presenca_deputado` |
| **Agent** | Enriquecer `deputado_agent.py` | Adicionar novas tools, atualizar instruction |
| **Testes** | Novos test files | Testes para cada nova tool, service, client method |

---

## 6. Fases de Entrega

### Fase A — Quick wins (API direta, sem RAG)

Maior custo-benefício. Agrega valor imediato com chamadas HTTP + tools novas.

```
├── Client + Types: orgãos, frentes, profissões, histórico
├── Tools: obter_comissoes_deputado, obter_frentes_deputado
├── Tool: obter_raio_x_deputado (perfil enriquecido combinando tudo)
└── Testes
```

**Estimativa**: ~2-3 dias

### Fase B — Discursos RAG (maior valor diferenciador)

Exige mais infra (sync, storage, embeddings), mas é o principal diferencial.

```
├── Client + Types: discursos
├── Domain model: Discurso (persistir e indexar)
├── Sync task: sync_discursos periódica
├── RAG: chunking + embedding de discursos
├── Tool: buscar_discursos_deputado (busca semântica)
└── Testes
```

**Estimativa**: ~3-5 dias

### Fase C — Alinhamento e participação

Fecha o ciclo de accountability do deputado.

```
├── Client + Types: eventos de deputado
├── Tool: obter_presenca_deputado (eventos + agregação)
├── Service: calcular alinhamento deputado vs voto popular
├── Tool: obter_alinhamento_deputado
└── Testes
```

**Estimativa**: ~2-3 dias

---

## 7. Exemplos de Conversa (UX esperada)

```
Eleitor: "Me fala sobre o deputado João Silva"
→ Raio-X: perfil, partido, comissões, frentes, profissão, resumo de gastos

Eleitor: "Em quais comissões o deputado atua?"
→ Lista de comissões/órgãos com cargo e período

Eleitor: "O que a deputada Maria disse sobre saúde?"
→ Busca semântica nos discursos indexados, retorna trechos relevantes

Eleitor: "Quais frentes parlamentares meu deputado participa?"
→ Lista de frentes parlamentares

Eleitor: "Quanto meu deputado gastou comparado com a média?"
→ Gastos + comparativo com média UF/partido

Eleitor: "Meu deputado vota de acordo com o povo?"
→ Índice de alinhamento com voto popular
```

---

## 8. Decisões Técnicas

### Discursos — Estratégia de Sync

- **Não sincronizar todos os deputados de uma vez** — volume muito alto.
- **Sync on-demand + lazy caching**: ao acessar discursos de um deputado, sync se dados > 24h.
- **Sync em background**: Celery task agenda sync dos deputados mais consultados (top 50).
- **Retenção**: manter discursos da legislatura atual (últimos 4 anos).

### Discursos — Estratégia de Chunking

- **1 chunk = 1 discurso** (ementas são curtas o suficiente).
- Se discurso for longo (> 2000 chars), dividir em parágrafos.
- Metadata no chunk: `deputado_id`, `data`, `tipo_evento`, `keywords`.
- `ChunkType.discurso` no enum existente.

### Raio-X — Estratégia de Agregação

- A tool `obter_raio_x_deputado` faz múltiplas chamadas paralelas à API:
  `asyncio.gather(perfil, orgaos, frentes, profissoes)`.
- Resultado consolidado num dict estruturado para o agente formatar.
- Cache Redis (TTL 1h) para evitar chamadas repetidas.

### Alinhamento — Cálculo

- Apenas votações com ≥ 10 votos populares são consideradas.
- Índice: proporção de votações onde o deputado votou com a maioria popular.
- Exibido como percentual + classificação qualitativa
  ("alto alinhamento", "alinhamento moderado", "baixo alinhamento").
