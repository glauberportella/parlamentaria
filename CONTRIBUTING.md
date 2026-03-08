# Guia de Contribuição — Parlamentaria

Obrigado por considerar contribuir com a **Parlamentaria**! 🇧🇷

Este projeto é de **democracia participativa sobre democracia participativa** — ele só faz sentido sendo construído pela comunidade. Toda contribuição, grande ou pequena, é valorizada.

---

## 📋 Índice

- [Código de Conduta](#-código-de-conduta)
- [Como Começar](#-como-começar)
- [Ambiente de Desenvolvimento](#-ambiente-de-desenvolvimento)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Padrões de Código](#-padrões-de-código)
- [Convenções de Commit e Branch](#-convenções-de-commit-e-branch)
- [Testes](#-testes)
- [Pull Requests](#-pull-requests)
- [Tipos de Contribuição](#-tipos-de-contribuição)
- [Padrões para FunctionTools (ADK)](#-padrões-para-functiontools-adk)
- [Segurança e Privacidade](#-segurança-e-privacidade)
- [Lições Aprendidas](#-lições-aprendidas)
- [Dúvidas?](#-dúvidas)

---

## 🤝 Código de Conduta

- Seja respeitoso, inclusivo e construtivo.
- Mantenha o tom apartidário — o projeto não tem posição política.
- Críticas ao código são bem-vindas; ataques pessoais, não.
- Contribuições em português brasileiro são preferidas na documentação. Código (variáveis, funções, classes) em inglês.

---

## 🚀 Como Começar

1. **Leia o [AGENTS.md](AGENTS.md)** — é a fonte de verdade para arquitetura, padrões e estrutura.
2. **Procure issues** com labels `good first issue` ou `help wanted`.
3. **Comente na issue** que pretende trabalhar — evita trabalho duplicado.
4. **Fork o repositório** e crie uma branch a partir de `main`.
5. **Implemente**, seguindo os padrões descritos abaixo.
6. **Abra um Pull Request** referenciando a issue.

---

## 🛠️ Ambiente de Desenvolvimento

### Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Uma API key do Google (Gemini) — [obter aqui](https://aistudio.google.com/app/apikey)
- Token de bot do Telegram — [criar com @BotFather](https://t.me/BotFather)

### Setup com Docker (recomendado)

```bash
# Clone seu fork
git clone https://github.com/SEU_USUARIO/parlamentaria.git
cd parlamentaria

# Copie e configure as variáveis de ambiente
cp .env.example .env
# Edite .env com GOOGLE_API_KEY e TELEGRAM_BOT_TOKEN

# Suba os serviços
docker compose up -d

# Rode as migrações
docker compose exec backend alembic upgrade head
```

### Setup sem Docker (desenvolvimento local)

```bash
cd backend

# Crie e ative o virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instale as dependências (incluindo dev)
pip install -e ".[dev]"

# Garanta que PostgreSQL e Redis estejam rodando
# (ou use o docker-compose apenas para DB e Redis)
docker compose up -d db redis

# Rode as migrações
alembic upgrade head

# Rode o servidor com hot-reload
uvicorn app.main:app --reload --port 8000
```

### Verificando que tudo funciona

```bash
cd backend

# Rode os testes
pytest tests/ -v --cov=app

# Lint
ruff check .

# Type check (opcional)
mypy app/
```

---

## 📁 Estrutura do Projeto

```
parlamentaria/
├── AGENTS.md              # ⭐ Fonte de verdade — leia primeiro
├── CONTRIBUTING.md         # Este arquivo
├── docker-compose.yml      # Orquestração dos serviços
├── agents/                 # Agentes de IA (Google ADK)
│   └── parlamentar/        # Root Agent + Sub-Agents + Tools
├── channels/               # Adapters de mensageria
│   ├── telegram/           # Bot Telegram (canal primário)
│   └── whatsapp/           # WhatsApp (em desenvolvimento)
└── backend/
    ├── app/
    │   ├── domain/         # Entidades SQLAlchemy
    │   ├── schemas/        # DTOs Pydantic
    │   ├── repositories/   # Acesso a dados
    │   ├── services/       # Lógica de negócio
    │   ├── integrations/   # Client HTTP da API Câmara
    │   ├── routers/        # Endpoints FastAPI
    │   └── tasks/          # Jobs Celery
    └── tests/              # Testes
```

> ⚠️ **Não crie arquivos fora desta estrutura** sem justificativa explícita no PR.

---

## 📐 Padrões de Código

### Python

- **PEP 8** + formatação com **Ruff**
- **Type hints obrigatórios** em todas as funções públicas
- **Docstrings**: Google style em classes e métodos públicos
- **Async/await** para toda operação de I/O (DB, HTTP, Redis)
- **Validação**: Pydantic models para input/output
- **Imports**: absolutos a partir de `app.` (ex: `from app.services.proposicao_service import ...`)
- **Nomes**: `snake_case` para funções/variáveis, `PascalCase` para classes

### Exceções

Use a hierarquia customizada do projeto:

```python
from app.exceptions import AppException, NotFoundException, ValidationException

# Nunca use exceções genéricas para erros de negócio
raise NotFoundException(detail="Proposição não encontrada")
```

### Variáveis de ambiente

**Nunca hardcode** URLs, credenciais ou configurações. Use `app.config.settings`:

```python
from app.config import settings

# ✅ Correto
model = settings.embedding_model

# ❌ Errado
model = "gemini-embedding-001"
```

---

## 📝 Convenções de Commit e Branch

### Branches

| Prefixo      | Uso                                    |
|---------------|----------------------------------------|
| `feat/`       | Nova funcionalidade                    |
| `fix/`        | Correção de bug                        |
| `refactor/`   | Refatoração sem mudança de comportamento |
| `docs/`       | Documentação                           |
| `chore/`      | Infra, CI, dependências               |
| `test/`       | Adição/melhoria de testes              |

### Commits — Conventional Commits

```
feat: adicionar busca por tema no ProposicaoAgent
fix: corrigir validação de CPF com dígitos repetidos
refactor: extrair lógica de chunking do RAGService
docs: atualizar seção de RAG no AGENTS.md
test: adicionar testes para VotacaoService
chore: atualizar dependências do google-adk
```

### Regras

- **Commits atômicos** — um fix/feature por commit.
- **Em português** — mensagens de commit em português brasileiro.
- **Referência a issue** — quando aplicável: `fix: corrigir validação (#42)`.

---

## 🧪 Testes

### Regras obrigatórias

1. **Todo service novo deve ter test file correspondente** — sem exceções.
2. **Todo repository deve ter testes com mock de session** — validar queries.
3. **Toda FunctionTool do ADK deve ter teste unitário** — validar input/output.
4. **Fixtures JSON para respostas da API Câmara** — nunca depender de API real em CI.
5. **Testes async usam `pytest-asyncio`** com `mode=auto`.

### Meta de cobertura

- **Cobertura global mínima**: 75% (CI falha abaixo disso)
- **Módulos críticos**: 85-90% (`services/`, `repositories/`, `integrations/`, `agents/tools/`, `channels/`)

### Rodando os testes

```bash
cd backend

# Todos os testes
pytest tests/ -v --cov=app --cov-report=term-missing

# Testes unitários apenas
pytest tests/ -v -k "not integration"

# Um módulo específico
pytest tests/test_proposicao_service.py -v

# Com cobertura mínima enforçada
pytest tests/ --cov=app --cov-fail-under=75
```

### Categorização

Use `pytest.mark` para categorizar:

```python
import pytest

@pytest.mark.unit
async def test_buscar_proposicoes():
    ...

@pytest.mark.integration
async def test_webhook_telegram():
    ...
```

---

## 🔀 Pull Requests

### Checklist do PR

- [ ] Código segue os padrões descritos neste guia
- [ ] Type hints presentes em todas as funções públicas
- [ ] Testes escritos para código novo
- [ ] Testes existentes passam (`pytest tests/ -v`)
- [ ] Lint passa (`ruff check .`)
- [ ] Sem credenciais ou configurações hardcoded
- [ ] Branch criada a partir de `main` atualizada
- [ ] Commit messages seguem Conventional Commits
- [ ] Issue referenciada na descrição do PR

### Descrição do PR

Use este template:

```markdown
## O que este PR faz?

Breve descrição da mudança.

## Issue relacionada

Closes #XX

## Tipo de mudança

- [ ] Nova funcionalidade (feat)
- [ ] Correção de bug (fix)
- [ ] Refatoração (refactor)
- [ ] Documentação (docs)
- [ ] Testes (test)

## Como testar?

Passos para o reviewer verificar a mudança.
```

---

## 🎯 Tipos de Contribuição

### Quem pode contribuir

| Perfil | Como ajudar |
|--------|-------------|
| **Desenvolvedores** | Python, FastAPI, IA, bots, DevOps |
| **Designers** | UX conversacional, fluxos de chatbot |
| **Cientistas de dados** | Análise legislativa, NLP em português |
| **Jornalistas** | Linguagem acessível, fact-checking |
| **Juristas** | Validação de análises de proposições |
| **Cidadãos** | Testar, reportar bugs, sugerir funcionalidades |

### Oportunidades de contribuição

| Área | O que fazer |
|------|-------------|
| 📱 WhatsApp | Homologação do adapter com API real da Meta |
| 💬 Grupos Telegram | Suporte a interação em grupos |
| 🧠 Prompts IA | Refinar prompts, testar com diferentes LLMs |
| 🧪 Testes E2E | Testes end-to-end com agentes reais |
| 🏛️ Senado Federal | Expandir para API do Senado |
| 📊 Monitoramento | Prometheus/Grafana, dashboards |
| ♿ Acessibilidade | Mensagens de áudio, linguagem simplificada |
| 🔍 RAG | Refinar chunking, tuning de threshold |
| ⚡ Performance | Otimizar queries, cache avançado |
| 🔐 Auditoria | Compliance LGPD, rastreabilidade |

---

## 🔧 Padrões para FunctionTools (ADK)

As FunctionTools são funções Python que os agentes LLM chamam. Elas exigem cuidado especial porque o **LLM decide quando e como chamar** com base no nome e docstring.

### Regras

1. **Nomes claros em português** — o LLM usa o nome para decidir.
2. **Docstrings completas** — Google style com `Args` e `Returns`.
3. **Return `dict`** — sempre com chave `"status"` (`"success"` ou `"error"`).
4. **Parâmetros simples** — preferir `str`, `int`, `bool`.
5. **Poucos parâmetros** — o LLM decide os valores.
6. **Sem side effects ocultos** — previsíveis e idempotentes.
7. **Mensagens de erro amigáveis** — **NUNCA retornar `str(e)` diretamente**. Usar mensagens genéricas que o agente possa repassar ao eleitor sem expor detalhes técnicos (ver [Lições Aprendidas](#-lições-aprendidas)).

### Exemplo

```python
async def buscar_proposicoes(
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
    try:
        # ... lógica ...
        return {"status": "success", "proposicoes": [...], "total": 42}
    except Exception:
        return {
            "status": "error",
            "error": "Não foi possível buscar proposições no momento. Tente novamente.",
        }
```

---

## 🔐 Segurança e Privacidade

- **CPF e título de eleitor** são armazenados apenas como hash SHA-256 — nunca em texto.
- **Secrets** nunca são commitados. Use `.env` local e secrets do CI/CD em produção.
- **Input validation** — Pydantic valida 100% dos inputs na borda.
- **SQL Injection** — prevenido nativamente pelo SQLAlchemy.
- **HTTPS** obrigatório em staging e produção.
- **Se encontrar uma vulnerabilidade**, não abra issue pública — entre em contato diretamente via email ou Discussions marcada como privada.

---

## 📚 Lições Aprendidas

Problemas já encontrados e solucionados que servem de referência para contribuidores:

### Agentes LLM expondo detalhes técnicos internos

**Problema**: O agente mencionava nomes de modelos internos (ex: `text-embedding-004`) e detalhes de implementação nas respostas ao eleitor. Não era um erro real de API — o LLM "alucinava" nomes de modelos do seu treinamento quando uma tool falhava ou retornava vazio.

**Causa raiz**: As FunctionTools retornavam `str(e)` (mensagem de exceção bruta) no campo `"error"` do dict de retorno. O LLM interpretava esses erros técnicos e os mencionava na resposta conversacional.

**Solução**:
1. Substituir `str(e)` por mensagens amigáveis em todas as FunctionTools.
2. Adicionar instruções explícitas nos prompts dos agentes para **NUNCA mencionar** nomes de modelos, endpoints de API, bancos de dados ou detalhes de implementação ao eleitor.

**Regra**: Toda FunctionTool deve retornar mensagens de erro que possam ser mostradas diretamente ao eleitor, sem exposição de internos do sistema.

### Savepoints em operações de lote

**Problema**: Um erro em um registro durante sincronização em lote corrompia a session inteira.

**Solução**: Usar `session.begin_nested()` (SAVEPOINT do PostgreSQL) para isolar cada operação individual. Detalhes na seção 14.1 do [AGENTS.md](AGENTS.md).

---

## ❓ Dúvidas?

- **Issues**: [github.com/glauberportella/parlamentaria/issues](https://github.com/glauberportella/parlamentaria/issues)
- **Discussions**: [github.com/glauberportella/parlamentaria/discussions](https://github.com/glauberportella/parlamentaria/discussions)
- **Documentação técnica**: [AGENTS.md](AGENTS.md) — fonte de verdade para arquitetura e padrões

---

<p align="center">
  <strong>A democracia se constrói em comunidade. Obrigado por fazer parte.</strong>
</p>
