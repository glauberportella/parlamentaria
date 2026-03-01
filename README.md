<p align="center">
  <img src="https://img.shields.io/badge/🇧🇷-Democracia_Participativa-009c3b?style=for-the-badge&labelColor=002776" alt="Democracia Participativa" />
</p>

<h1 align="center">Parlamentaria</h1>

<h3 align="center"><em>Seu Parlamentar de IA — conectando eleitores e parlamentares<br>através de conversa, transparência e voto popular</em></h3>

<p align="center">
  <a href="#-o-que-é">O que é</a> •
  <a href="#-para-quem">Para quem</a> •
  <a href="#-como-funciona">Como funciona</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-rodando-localmente">Setup</a> •
  <a href="#-como-contribuir">Contribuir</a> •
  <a href="#-licença">Licença</a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/license/glauberportella/parlamentaria?style=flat-square" alt="MIT License" />
  <img src="https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-0.135+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Google_ADK-Agent_Framework-4285f4?style=flat-square&logo=google&logoColor=white" alt="Google ADK" />
  <img src="https://img.shields.io/badge/Telegram-Bot-26a5e4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram" />
</p>

---

## 🗳️ O que é

**Parlamentaria** é uma plataforma open-source de **democracia participativa** que usa Inteligência Artificial para aproximar eleitores e parlamentares.

Através de um agente conversacional no **Telegram** (e futuramente **WhatsApp**), qualquer cidadão brasileiro pode:

- **Entender** o que está sendo votado na Câmara dos Deputados — em linguagem simples, sem juridiquês
- **Votar** nas proposições que impactam sua vida e expressar sua posição
- **Acompanhar** o resultado: o voto popular foi ouvido ou ignorado?

E qualquer parlamentar pode:

- **Ouvir** a posição real dos eleitores antes de votar
- **Publicar** seu alinhamento com a vontade popular
- **Demonstrar** compromisso com a democracia participativa

> **Sem app para instalar. Sem cadastro em site. Basta abrir o Telegram e conversar.**

---

## 👥 Para quem

### 🧑‍💼 Para o Cidadão

Você trabalha, estuda, cuida da família — e não tem tempo de ler diários oficiais. Mas as leis que saem do Congresso afetam **sua vida, seu bolso, sua saúde, sua segurança**.

A Parlamentaria coloca um **assistente de IA no seu Telegram** que:

- Resume proposições em linguagem que qualquer pessoa entende
- Analisa prós e contras de forma apartidária
- Permite que você vote SIM, NÃO ou ABSTENÇÃO com um toque
- Mostra se o Congresso votou como a maioria popular queria

**Sua voz merece ser ouvida entre as eleições, não apenas durante elas.**

### 🏛️ Para o Parlamentar

Legislar é representar. Mas como saber o que os eleitores realmente pensam sobre cada proposição?

A Parlamentaria oferece ao parlamentar:

- **RSS Feed** com o resultado consolidado da votação popular — filtrável por tema e UF
- **Webhooks** para integrar diretamente ao seu sistema ou gabinete
- **Comparativo público** entre o voto popular e o resultado parlamentar
- **Transparência** que fortalece a relação de confiança com o eleitorado

Assinar o feed da Parlamentaria é uma demonstração concreta de que **a vontade popular importa no seu mandato**.

---

## ⚙️ Como funciona

```
  Eleitor                                                      Parlamentar
  (Telegram)                                                   (RSS / Webhook)
     │                                                              ▲
     │  "O que é o PL 1234?"                                        │
     ▼                                                              │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Parlamentaria                                       │
│                                                                             │
│  ┌──────────┐   ┌───────────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │ Telegram  │──▶│  Agente de IA     │──▶│  Voto        │──▶│ Publicação │──┼──▶ RSS Feed
│  │ Gateway   │◀──│  (Google ADK)     │   │  Popular     │   │ & Feedback │──┼──▶ Webhooks
│  └──────────┘   └──────────┬────────┘   └──────────────┘   └─────┬──────┘  │
│                            │                                      │         │
│                  ┌─────────▼──────────┐              ┌────────────▼──────┐  │
│                  │  API Dados Abertos │              │  Comparativo      │  │
│                  │  Câmara dos        │              │  Popular vs Real  │  │
│                  │  Deputados         │              └───────────────────┘  │
│                  └────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### O ciclo completo

1. **Sincronização** — O sistema monitora a API de Dados Abertos da Câmara continuamente
2. **Análise** — IA resume e analisa cada proposição de forma apartidária
3. **Notificação** — Eleitores recebem alertas sobre temas do seu interesse
4. **Conversa** — O eleitor pergunta, o agente explica — sem jargão político
5. **Voto Popular** — O eleitor registra sua posição com um toque
6. **Consolidação** — Votos são agregados em tempo real
7. **Publicação** — Resultados são disponibilizados via RSS Feed e Webhooks
8. **Comparativo** — Quando a Câmara vota, o sistema compara com o voto popular
9. **Feedback** — O eleitor recebe: "A proposição X foi aprovada. 73% dos eleitores queriam SIM. Alinhamento: 95%"

---

## 🧠 Tech Stack

| Camada | Tecnologia | Papel |
|--------|-----------|-------|
| **Agentes de IA** | Google ADK (Agent Development Kit) | Framework multi-agent conversacional |
| **Backend** | Python 3.11+ / FastAPI | API async, webhooks, orquestração |
| **Mensageria** | Telegram Bot API | Canal primário de interação |
| **Banco de Dados** | PostgreSQL 16 | Persistência relacional + JSONB |
| **Cache / Filas** | Redis + Celery | Cache, sessões, jobs assíncronos |
| **LLM** | Gemini (primário) via ADK | Análise e conversa — model-agnostic |
| **Containers** | Docker + Docker Compose | Ambiente reproduzível |
| **CI/CD** | GitHub Actions | Lint, test, build, deploy |
| **Testes** | pytest + pytest-asyncio | Cobertura mínima 75%, críticos 85%+ |

---

## 🚀 Rodando localmente

### Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Uma API key do Google (Gemini) — [obter aqui](https://aistudio.google.com/app/apikey)
- Token de bot do Telegram — [criar com @BotFather](https://t.me/BotFather)

### Setup

```bash
# 1. Clone o repositório
git clone https://github.com/glauberportella/parlamentaria.git
cd parlamentaria

# 2. Copie as variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves (GOOGLE_API_KEY, TELEGRAM_BOT_TOKEN, etc.)

# 3. Suba os serviços com Docker
docker compose up -d

# 4. Rode as migrações
docker compose exec backend alembic upgrade head

# 5. Pronto! O bot está rodando. Converse com ele no Telegram.
```

### Desenvolvimento (sem Docker)

```bash
cd backend

# Crie e ative o virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instale as dependências (incluindo dev)
pip install -e ".[dev]"

# Rode os testes
pytest tests/ -v --cov=app

# Rode o servidor
uvicorn app.main:app --reload --port 8000
```

---

## 🏗️ Estrutura do Projeto

```
parlamentaria/
├── AGENTS.md              # Guia completo para desenvolvimento (fonte de verdade)
├── docker-compose.yml     # Orquestração dos serviços
├── .env.example           # Template de variáveis de ambiente
│
├── agents/                # Agentes de IA (Google ADK)
│   └── parlamentar/       # Root Agent + Sub-Agents + Tools
│
├── channels/              # Adapters de mensageria (Telegram, WhatsApp)
│   ├── telegram/
│   └── whatsapp/          # Futuro
│
└── backend/
    ├── app/
    │   ├── domain/        # Entidades do domínio (SQLAlchemy)
    │   ├── schemas/       # DTOs Pydantic (request/response)
    │   ├── repositories/  # Acesso a dados
    │   ├── services/      # Lógica de negócio
    │   ├── integrations/  # Client HTTP da API Câmara
    │   ├── routers/       # Endpoints FastAPI (webhooks, admin, RSS)
    │   └── tasks/         # Jobs Celery (sync, notificações)
    └── tests/             # Testes unitários e de integração
```

> 📖 Para documentação completa da arquitetura, agentes, padrões e convenções, consulte o [AGENTS.md](AGENTS.md).

---

## 🤝 Como contribuir

A Parlamentaria é um projeto de **democracia participativa sobre democracia participativa** — ela só faz sentido se for construída pela comunidade.

### Quem pode contribuir

- **Desenvolvedores** — Python, FastAPI, IA, bots, DevOps
- **Designers** — UX conversacional, fluxos de chatbot
- **Cientistas de dados** — análise legislativa, NLP em português
- **Jornalistas / Comunicadores** — linguagem acessível, fact-checking
- **Advogados / Juristas** — validação de análises de proposições
- **Cidadãos** — testar, reportar bugs, sugerir funcionalidades, divulgar

### Como começar

1. **Leia o [AGENTS.md](AGENTS.md)** — é o guia completo do projeto
2. **Escolha uma issue** — procure por labels `good first issue` ou `help wanted`
3. **Fork + Branch** — crie uma branch `feat/`, `fix/` ou `docs/`
4. **Implemente** — siga os padrões do AGENTS.md (tipagem, testes, docstrings)
5. **Abra um PR** — descreva o que fez, referencie a issue

### Convenções

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat: ...`, `fix: ...`, `docs: ...`
- **Branches**: `feat/descricao`, `fix/descricao`, `docs/descricao`
- **Testes**: todo código novo deve vir acompanhado de testes
- **Linting**: Ruff — rode `ruff check .` antes de commitar
- **Idioma do código**: inglês (variáveis, funções, classes) | **Documentação**: português

### Ideias para contribuições

| Área | O que fazer |
|------|-------------|
| 📱 Telegram | Inline keyboards, comandos, fluxos conversacionais |
| 🗳️ Votação | Fluxo de votação popular via chat, consolidação |
| 📊 Análise | Melhorar prompts de análise legislativa |
| 📡 RSS/Webhooks | Feed RSS público, dispatch de webhooks |
| 🧪 Testes | Aumentar cobertura, testes de integração, eval de agentes |
| 📝 Documentação | Guias, tutoriais, tradução para inglês |
| 🔒 Segurança | Rate limiting, validação de webhooks, auditoria |
| ♿ Acessibilidade | Linguagem simples, suporte a áudio, inclusão digital |

---

## 📜 Princípios

1. **Apartidário** — A plataforma não tem posição política. Apresenta fatos e análises equilibradas.
2. **Transparente** — Todo o código é aberto. Todo dado público é rastreável à fonte oficial.
3. **Acessível** — Se o cidadão não entende, a explicação falhou — não o cidadão.
4. **Para todos** — Eleitores e parlamentares. A democracia é diálogo, não monólogo.
5. **Privacidade** — Dados mínimos. Sem rastreamento. O voto é do eleitor.

---

## 📡 API Dados Abertos da Câmara

Este projeto consome exclusivamente dados públicos da [API de Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html):

- Proposições em tramitação
- Votações e resultados
- Perfis de deputados
- Eventos e pautas do plenário

Nenhum dado sigiloso é acessado. Toda informação é pública e de livre acesso.

---

## 🗺️ Roadmap

- [x] **Fase 1** — Fundação: setup, banco de dados, integração API Câmara, modelos, testes
- [x] **Fase 2** — Core Backend: services, repositórios, sincronização Celery, routers RSS/admin
- [x] **Fase 3** — Agentes de IA: root agent, 5 sub-agents, 25 tools, sessions, eval datasets
- [x] **Fase 4** — Canal Telegram: bot, webhooks, inline keyboards
- [ ] **Fase 5** — Votação Popular: fluxo de voto, consolidação, notificações
- [ ] **Fase 6** — Publicação: RSS Feed, webhooks de saída
- [ ] **Fase 7** — Comparativo: voto popular vs real, feedback ao eleitor
- [ ] **Fase 8** — Polimento: segurança, monitoring, deploy, WhatsApp

---

## 📄 Licença

Este projeto é distribuído sob a licença **MIT**. Veja [LICENSE](LICENSE) para detalhes.

Isso significa que você pode usar, copiar, modificar e distribuir livremente — inclusive em projetos comerciais — desde que mantenha a atribuição.

---

## 💬 Contato

- **Issues**: [github.com/glauberportella/parlamentaria/issues](https://github.com/glauberportella/parlamentaria/issues)
- **Discussions**: [github.com/glauberportella/parlamentaria/discussions](https://github.com/glauberportella/parlamentaria/discussions)

---

<p align="center">
  <strong>A democracia não acontece a cada 4 anos.<br>Acontece todos os dias.</strong>
</p>

<p align="center">
  <em>Se este projeto te representa, dê uma ⭐ e compartilhe.</em>
</p>
