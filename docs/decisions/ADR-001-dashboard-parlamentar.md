# ADR-001 — Dashboard do Parlamentar

> **Status**: Proposta  
> **Data**: 2026-03-08  
> **Autor**: GitHub Copilot + Glauber Portella  
> **Decisão**: Criar dashboard web para parlamentares acompanharem votos populares

---

## 1. Contexto e Motivação

Até agora o Parlamentaria foca 100% no eleitor (Telegram/WhatsApp). Para o parlamentar, a plataforma oferece apenas:

- **RSS Feed** (`/rss/votos`, `/rss/comparativos`) — consumo passivo, limitado
- **Webhooks de saída** — integração técnica, requer desenvolvimento do lado do parlamentar
- **Admin API** — endpoints operacionais, não pensados para análise

**O parlamentar precisa de uma ferramenta visual** para:
- Acompanhar o sentimento popular sobre proposições em tramitação  
- Analisar tendências de voto por tema, região e ao longo do tempo  
- Comparar como vota vs como o povo quer  
- Tomar decisões informadas com base em dados reais de participação

---

## 2. Decisão de Arquitetura

### 2.1 Frontend: Next.js 15 (App Router) + Vercel

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| **Framework** | Next.js 15 (App Router) | SSR/SSG, React Server Components, melhor SEO, API routes |
| **Linguagem** | TypeScript | Type safety, melhor DX, documenta contratos da API |
| **UI Library** | shadcn/ui + Tailwind CSS 4 | Componentes acessíveis, customizáveis, sem lock-in |
| **Charts** | Recharts ou Tremor | Gráficos declarativos React, boa UX para dashboards |
| **State** | TanStack Query (React Query) | Cache, polling, invalidação automática para dados da API |
| **Auth** | NextAuth.js v5 (Auth.js) | Multi-provider, session management, JWT/DB sessions |
| **Deploy** | Vercel | Zero-config para Next.js, edge functions, preview deploys |
| **Monorepo** | Pasta `dashboard/` na raiz do projeto | Coeso com o monorepo existente |

### 2.2 Backend: Nova camada de API separada no FastAPI existente

Em vez de criar um backend separado, **adicionamos um novo router** `/parlamentar/` no FastAPI existente, com:
- Autenticação própria (JWT, não API key)
- Endpoints otimizados para dashboard (agregações, séries temporais)
- Rate limits adequados para SPA

```
backend/app/
├── routers/
│   ├── parlamentar/              # NOVO — API dedicada ao dashboard
│   │   ├── __init__.py
│   │   ├── auth.py               # Login, registro, refresh token
│   │   ├── dashboard.py          # Dados agregados, KPIs, widgets
│   │   ├── proposicoes.py        # Proposições com filtros avançados
│   │   ├── votacao_popular.py    # Resultados de votos populares
│   │   ├── comparativos.py       # Comparativos pop vs real
│   │   ├── meu_mandato.py        # Dados específicos do parlamentar logado
│   │   └── exportar.py           # Export CSV/PDF de dados
│   └── ... (routers existentes inalterados)
├── services/
│   └── parlamentar_auth_service.py  # NOVO — autenticação de parlamentares
├── domain/
│   └── parlamentar_user.py          # NOVO — modelo de conta do parlamentar
├── schemas/
│   └── parlamentar/                 # NOVO — DTOs do dashboard
│       ├── auth.py
│       ├── dashboard.py
│       └── filtros.py
```

---

## 3. Autenticação do Parlamentar

### 3.1 Estratégia: Multi-camada Progressiva

O parlamentar não é um "usuário" da plataforma no mesmo sentido que o eleitor. Precisamos de um sistema de autenticação **seguro mas prático** que permita identificar quem é o parlamentar acessando o dashboard.

### 3.2 Opções Analisadas

| Opção | Prós | Contras | Decisão |
|-------|------|---------|---------|
| **A) gov.br (Login Único Federal)** | Identidade oficial, alta confiança | Burocracia para integrar, processo demorado de homologação | Futuro (Fase 3) |
| **B) OAuth Social (Google/GitHub)** | Fácil de implementar, familiar | Não comprova que é parlamentar | Complementar |
| **C) Email institucional + convite** | Valida domínio @camara.leg.br | Nem todo assessor tem acesso | **Fase 1 (primário)** |
| **D) Código de convite + Magic Link** | Simples, onboarding controlado | Requer gestão manual inicial | **Fase 1 (complementar)** |
| **E) Username/password tradicional** | Universal | Password fatigue, menor segurança | Descartado |

### 3.3 Decisão: Fluxo de Autenticação em 3 Fases

#### Fase 1 — Login por Magic Link + Convite (MVP)

```
1. Admin cria convite para o parlamentar (via API admin existente)
   → Gera código + vincula ao deputado_id da API da Câmara

2. Parlamentar acessa dashboard, insere email + código de convite
   → Sistema valida código e email
   → Envia Magic Link (link com token JWT de curta duração) para o email

3. Parlamentar clica no Magic Link
   → Token validado → Sessão JWT criada (access + refresh tokens)
   → Dashboard acessível

4. Sessões subsequentes: email → Magic Link (sem necessidade de código)
```

**Vantagens do Magic Link:**
- Sem password para gerenciar
- Email funciona como 2º fator implícito
- Onboarding controlado (só quem tem convite entra)
- Simples de implementar com NextAuth.js

#### Fase 2 — OAuth Social + Vinculação

Adicionar login via Google/Microsoft como alternativa ao Magic Link. O primeiro login ainda requer convite para vincular ao perfil do parlamentar.

#### Fase 3 — Integração gov.br (Futuro)

Login federado via gov.br para máxima confiança na identidade. Requer processo formal de integração com o governo.

### 3.4 Modelo: ParlamentarUser

```python
class ParlamentarUser(Base):
    """Conta de acesso ao dashboard do parlamentar."""
    __tablename__ = "parlamentar_users"

    id: Mapped[uuid.UUID]                     # PK
    deputado_id: Mapped[int]                  # FK → deputados.id (da API Câmara)
    email: Mapped[str]                        # Email principal (pode ser @camara.leg.br)
    nome: Mapped[str]                         # Nome para exibição
    cargo: Mapped[str]                        # "Deputado(a) Federal", "Assessor(a)"
    tipo: Mapped[TipoParlamentarUser]         # DEPUTADO, ASSESSOR, LIDERANCA
    ativo: Mapped[bool]                       # Conta ativa
    codigo_convite: Mapped[str | None]        # Código usado no primeiro acesso
    ultimo_login: Mapped[datetime | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    
    # Preferências do dashboard
    temas_acompanhados: Mapped[list[str] | None]  # Filtros salvos
    notificacoes_email: Mapped[bool]               # Receber alertas por email
```

### 3.5 JWT Tokens (Backend)

```python
# Access Token: curta duração (15 min), usado em cada request
# Refresh Token: longa duração (7 dias), usado para renovar access
# Magic Link Token: uso único (15 min), usado no link enviado por email

JWT_SECRET_KEY = env("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAGIC_LINK_EXPIRE_MINUTES = 15
```

---

## 4. API do Parlamentar — Endpoints Necessários

### 4.1 Autenticação

```
POST /parlamentar/auth/convite           # Cria convite (admin only)
POST /parlamentar/auth/login             # Solicita Magic Link (envia email)
POST /parlamentar/auth/verify            # Valida Magic Link token
POST /parlamentar/auth/refresh           # Renova access token
POST /parlamentar/auth/logout            # Invalida refresh token
GET  /parlamentar/auth/me                # Perfil do parlamentar logado
```

### 4.2 Dashboard — KPIs e Agregações

```
GET /parlamentar/dashboard/resumo
```
Retorna painel principal com:
```json
{
  "kpis": {
    "total_proposicoes_ativas": 142,
    "total_eleitores_cadastrados": 15420,
    "total_votos_populares": 87350,
    "total_comparativos": 38,
    "alinhamento_medio": 0.72,
    "taxa_participacao": 0.45
  },
  "tendencias": {
    "votos_ultimos_7_dias": 2340,
    "novos_eleitores_ultimos_7_dias": 180,
    "proposicoes_mais_votadas": [...],
    "temas_mais_ativos": [...]
  },
  "alertas": [
    {"tipo": "nova_votacao", "mensagem": "PL 1234/2026 em votação hoje", "urgencia": "alta"}
  ]
}
```

### 4.3 Proposições com Dados Enriquecidos

```
GET /parlamentar/proposicoes
    ?tema=saude
    &tipo=PL
    &ano=2026
    &ordenar=votos_desc|recentes|alinhamento
    &pagina=1
    &itens=20
```
Retorna proposições + resultado de votação popular inline + análise IA resumida.

```
GET /parlamentar/proposicoes/{id}
```
Detalhes completos: ementa, análise IA, prós/contras, resultado de votação popular, comparativo (se existir), histórico.

### 4.4 Votação Popular — Dados Analíticos

```
GET /parlamentar/votos/por-tema
    ?periodo=7d|30d|90d|1a
```
Agregação de votos populares agrupados por tema.

```
GET /parlamentar/votos/por-uf
    ?proposicao_id=1234
```
Distribuição geográfica dos votos por UF.

```
GET /parlamentar/votos/timeline
    ?proposicao_id=1234
    &granularidade=dia|semana|mes
```
Série temporal de votos (para gráficos de linha).

```
GET /parlamentar/votos/ranking
    ?periodo=30d
    &limite=20
```
Proposições com mais votos populares (ranking de engajamento).

### 4.5 Comparativos

```
GET /parlamentar/comparativos
    ?periodo=90d
    &alinhamento_min=0.0
    &alinhamento_max=1.0
```
Lista com filtros avançados.

```
GET /parlamentar/comparativos/evolucao
```
Série temporal do índice de alinhamento médio ao longo do tempo.

### 4.6 Meu Mandato (Dados do Parlamentar Logado)

```
GET /parlamentar/meu-mandato/resumo
```
Dados específicos do deputado logado:
- Suas votações na Câmara vs voto popular (alinhamento pessoal)
- Proposições que ele é autor vs popularidade
- Ranking de alinhamento em relação a outros deputados do partido/UF

```
GET /parlamentar/meu-mandato/alinhamento
    ?periodo=90d
```
Evolução do índice de alinhamento do parlamentar logado com o voto popular.

### 4.7 Exportação

```
GET /parlamentar/exportar/votos?formato=csv&proposicao_id=1234
GET /parlamentar/exportar/comparativos?formato=csv&periodo=90d
GET /parlamentar/exportar/relatorio?proposicao_id=1234&formato=pdf
```

---

## 5. Dashboard — Páginas e Wireframe

### 5.1 Mapa de Páginas

```
/                          → Redirect para /dashboard
/login                     → Tela de login (email + Magic Link)
/login/verify              → Validação do Magic Link
/dashboard                 → Visão geral (KPIs + alertas + destaques)
/proposicoes               → Lista de proposições com filtros
/proposicoes/[id]          → Detalhe de proposição (análise IA + votos)
/votacao-popular            → Panorama geral de votos populares
/votacao-popular/por-tema   → Votos agrupados por tema
/votacao-popular/por-regiao → Mapa/tabela geográfica
/comparativos              → Lista de comparativos pop vs real
/comparativos/evolucao     → Gráfico temporal de alinhamento
/meu-mandato               → Dados do parlamentar logado
/meu-mandato/alinhamento   → Alinhamento pessoal com voto popular
/configuracoes             → Preferências, notificações, perfil
```

### 5.2 Dashboard Principal (`/dashboard`)

```
┌─────────────────────────────────────────────────────────────────┐
│  🏛️ Parlamentaria — Dashboard                    [Dep. Nome ▼] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ 142      │ │ 15.4K    │ │ 87.3K    │ │ 72%      │          │
│  │Proposiç. │ │Eleitores │ │Votos Pop.│ │Alinhamen.│          │
│  │ativas    │ │cadastr.  │ │registrad.│ │médio     │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                 │
│  ┌─────────────────────────────────┐ ┌─────────────────────────┐│
│  │ 📊 Votos por Tema (últimos 30d)│ │ 🔔 Alertas              ││
│  │                                 │ │                          ││
│  │  Saúde      ████████ 2.3K      │ │ • PL 1234 em votação    ││
│  │  Educação   ██████   1.8K      │ │ • 3 novos comparativos  ││
│  │  Economia   █████    1.5K      │ │ • 500 novos eleitores   ││
│  │  Segurança  ████     1.2K      │ │                          ││
│  │  Meio Amb.  ███       900      │ │                          ││
│  └─────────────────────────────────┘ └─────────────────────────┘│
│                                                                 │
│  ┌──────────────────────────────────────────────────────────────┤
│  │ 🏆 Proposições Mais Votadas                                  │
│  ├──────────────┬──────┬──────┬──────┬──────────────────────────│
│  │ Proposição   │ SIM  │ NÃO  │Total │ Alinhamento             │
│  ├──────────────┼──────┼──────┼──────┼──────────────────────────│
│  │ PL 1234/2026 │  73% │  21% │ 1247 │ ████████░░ 95%          │
│  │ PEC 45/2026  │  55% │  40% │  980 │ █████░░░░░ 55%          │
│  │ PL 789/2026  │  30% │  65% │  875 │ ███░░░░░░░ 30%          │
│  └──────────────┴──────┴──────┴──────┴──────────────────────────│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 Detalhe de Proposição (`/proposicoes/[id]`)

```
┌──────────────────────────────────────────────────────────────────┐
│  ← Voltar    PL 1234/2026 — Reforma Tributária                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📋 Ementa                              Situação: Em Tramitação │
│  Lorem ipsum ementa da proposição...    Temas: economia, tributos│
│  Autor(es): Dep. Fulano (PT-SP)         Apresentada: 15/01/2026 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ 🤖 Análise IA                                                ││
│  │ Resumo: Esta proposição visa simplificar o sistema...        ││
│  │ Impacto: Afeta arrecadação de estados e municípios...        ││
│  │ ✅ A favor: Simplificação, redução de burocracia...          ││
│  │ ❌ Contra: Possível perda de receita para estados...          ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌────────────────────────┐  ┌──────────────────────────────────┐│
│  │ 🗳️ Voto Popular        │  │ 📈 Evolução dos Votos            ││
│  │                        │  │                                   ││
│  │  SIM  ████████  73%    │  │  ^                                ││
│  │  NÃO  ██████    21%    │  │  |    ___/                        ││
│  │  ABS. ██         6%    │  │  |___/                            ││
│  │                        │  │  |                                ││
│  │  Total: 1.247 votos    │  │  +------>  tempo                  ││
│  │  (1.050 oficiais)      │  │              (últimos 30 dias)    ││
│  └────────────────────────┘  └──────────────────────────────────┘│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ 🗺️ Votos por UF                                              ││
│  │  SP: 320 | RJ: 180 | MG: 150 | BA: 95 | ...                 ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ ⚖️ Comparativo Pop vs Real                                    ││
│  │  Resultado Câmara: APROVADO (SIM: 350, NÃO: 120)            ││
│  │  Voto Popular: 73% SIM                                       ││
│  │  Alinhamento: 95% ████████████████████░░                     ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  [📥 Exportar CSV] [📄 Exportar PDF]                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Estrutura do Frontend (Next.js)

```
dashboard/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── .env.local.example
├── public/
│   └── logo.svg
├── src/
│   ├── app/
│   │   ├── layout.tsx                # Root layout (Sidebar + TopBar)
│   │   ├── page.tsx                  # Redirect → /dashboard
│   │   ├── globals.css
│   │   ├── (auth)/                   # Auth group (sem sidebar)
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── login/verify/
│   │   │       └── page.tsx
│   │   ├── (app)/                    # App group (com sidebar)
│   │   │   ├── layout.tsx            # Sidebar layout
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx          # Dashboard principal
│   │   │   ├── proposicoes/
│   │   │   │   ├── page.tsx          # Lista com filtros
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx      # Detalhe
│   │   │   ├── votacao-popular/
│   │   │   │   ├── page.tsx          # Panorama geral
│   │   │   │   ├── por-tema/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── por-regiao/
│   │   │   │       └── page.tsx
│   │   │   ├── comparativos/
│   │   │   │   ├── page.tsx          # Lista
│   │   │   │   └── evolucao/
│   │   │   │       └── page.tsx
│   │   │   ├── meu-mandato/
│   │   │   │   ├── page.tsx          # Resumo
│   │   │   │   └── alinhamento/
│   │   │   │       └── page.tsx
│   │   │   └── configuracoes/
│   │   │       └── page.tsx
│   │   └── api/                      # Next.js API routes (BFF proxy, se necessário)
│   │       └── auth/
│   │           └── [...nextauth]/
│   │               └── route.ts
│   ├── components/
│   │   ├── ui/                       # shadcn/ui components
│   │   ├── charts/                   # Componentes de gráfico
│   │   │   ├── bar-chart.tsx
│   │   │   ├── line-chart.tsx
│   │   │   ├── donut-chart.tsx
│   │   │   └── uf-heatmap.tsx
│   │   ├── dashboard/
│   │   │   ├── kpi-card.tsx
│   │   │   ├── alertas-panel.tsx
│   │   │   └── proposicoes-ranking.tsx
│   │   ├── proposicoes/
│   │   │   ├── proposicao-card.tsx
│   │   │   ├── analise-ia-panel.tsx
│   │   │   ├── voto-popular-chart.tsx
│   │   │   └── comparativo-badge.tsx
│   │   ├── layout/
│   │   │   ├── sidebar.tsx
│   │   │   ├── topbar.tsx
│   │   │   └── breadcrumbs.tsx
│   │   └── shared/
│   │       ├── data-table.tsx
│   │       ├── filtros-toolbar.tsx
│   │       ├── loading-skeleton.tsx
│   │       └── empty-state.tsx
│   ├── lib/
│   │   ├── api-client.ts             # Fetch wrapper com auth headers
│   │   ├── auth.ts                   # NextAuth config
│   │   ├── utils.ts                  # Helpers (cn, formatters)
│   │   └── constants.ts              # URLs, enums, temas
│   ├── hooks/
│   │   ├── use-dashboard.ts          # React Query: dados do dashboard
│   │   ├── use-proposicoes.ts        # React Query: proposições
│   │   ├── use-votos.ts              # React Query: votação popular
│   │   └── use-comparativos.ts       # React Query: comparativos
│   └── types/
│       ├── api.ts                    # Tipos de resposta da API
│       ├── proposicao.ts
│       ├── votacao.ts
│       └── auth.ts
└── tests/
    ├── e2e/                          # Playwright E2E tests
    └── components/                   # Vitest component tests
```

---

## 7. Stack Técnica Completa

### Frontend (dashboard/)

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Framework | Next.js (App Router) | 15.x |
| Linguagem | TypeScript | 5.x |
| UI Components | shadcn/ui | latest |
| Styling | Tailwind CSS | 4.x |
| Charts | Recharts | 2.x |
| Data Fetching | TanStack Query | 5.x |
| Auth | NextAuth.js (Auth.js) | 5.x (beta) |
| Tables | TanStack Table | 8.x |
| Forms | React Hook Form + Zod | latest |
| Icons | Lucide React | latest |
| Date handling | date-fns | 3.x |
| Testes unitários | Vitest + Testing Library | latest |
| Testes E2E | Playwright | latest |
| Deploy | Vercel | — |

### Backend (novas adições)

| Camada | Tecnologia | Notas |
|--------|-----------|-------|
| JWT Auth | PyJWT ou python-jose | Access + Refresh + Magic Link tokens |
| Email | Resend API ou SMTP (aiosmtplib) | Envio de Magic Links |
| CORS | FastAPI CORSMiddleware | Permitir domínio Vercel |
| Agregações SQL | SQLAlchemy + raw SQL | Queries analíticas performáticas |

---

## 8. CORS e Comunicação Frontend ↔ Backend

```python
# backend/app/main.py — adicionar ao lifespan ou startup
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",                    # Dev local
        "https://parlamentaria.vercel.app",         # Produção Vercel
        settings.dashboard_url,                     # Configurável
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## 9. Segurança

| Aspecto | Implementação |
|---------|---------------|
| **Autenticação** | JWT (access 15min + refresh 7d) via NextAuth.js ↔ Backend |
| **Magic Link** | Token JWT uso-único, 15min expiração, enviado por email |
| **Convite** | Código gerado pelo admin, vinculado a deputado_id, uso único |
| **CORS** | Whitelist de origens (Vercel + localhost dev) |
| **Rate Limiting** | slowapi no backend, por user_id (não por IP) |
| **Refresh Token** | Armazenado em httpOnly cookie, rotação automática |
| **CSRF** | Protegido por SameSite cookie + validation |
| **Input** | Zod no frontend + Pydantic no backend (validação dupla) |
| **Dados sensíveis** | Dashboard não exibe CPF/título — apenas dados agregados |

---

## 10. Variáveis de Ambiente Novas

### Backend (.env)
```bash
# Dashboard Parlamentar
DASHBOARD_URL=https://parlamentaria.vercel.app
JWT_SECRET_KEY=<random-64-chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
MAGIC_LINK_EXPIRE_MINUTES=15
MAGIC_LINK_BASE_URL=https://parlamentaria.vercel.app/login/verify

# Email (para Magic Links)
EMAIL_PROVIDER=resend              # resend | smtp
RESEND_API_KEY=re_...              # Se usar Resend
SMTP_HOST=smtp.gmail.com           # Se usar SMTP
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@parlamentaria.app
```

### Frontend (dashboard/.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<random-32-chars>
```

---

## 11. Plano de Implementação — Fases

### Fase 1 — Fundação (2-3 semanas)

```
1.1 Setup do projeto Next.js
    ├── Inicializar com create-next-app (App Router, TypeScript, Tailwind)
    ├── Configurar shadcn/ui
    ├── Estrutura de pastas conforme seção 6
    ├── ESLint + Prettier config
    └── Deploy inicial na Vercel (skeleton)

1.2 Autenticação Backend
    ├── Modelo ParlamentarUser + migration Alembic
    ├── ParlamentarAuthService (JWT, Magic Link)
    ├── Router /parlamentar/auth/* (login, verify, refresh, me)
    ├── Dependency get_current_parlamentar (injeção de auth)
    ├── CORS middleware configurado
    └── Testes unitários

1.3 Autenticação Frontend  
    ├── NextAuth.js configuração (custom provider → Magic Link)
    ├── Página /login (email + código convite)
    ├── Página /login/verify (callback do Magic Link)
    ├── Middleware de proteção de rotas
    ├── Context de auth (user logado)
    └── Testes
```

### Fase 2 — Dashboard Core (2-3 semanas)

```
2.1 API de Agregações (Backend)
    ├── GET /parlamentar/dashboard/resumo (KPIs)
    ├── GET /parlamentar/proposicoes (listagem enriquecida + paginação)
    ├── GET /parlamentar/proposicoes/{id} (detalhe completo)
    ├── Services com queries analíticas (GROUP BY, COUNT, séries temporais)
    └── Testes

2.2 Dashboard Principal (Frontend)
    ├── Layout com sidebar + topbar
    ├── KPI Cards (proposições, eleitores, votos, alinhamento)
    ├── Gráfico de votos por tema (bar chart)
    ├── Ranking de proposições mais votadas (data table)
    ├── Painel de alertas
    ├── TanStack Query hooks
    └── Loading skeletons + empty states
```

### Fase 3 — Proposições e Votos (2-3 semanas)

```
3.1 API de Votos Analíticos (Backend)
    ├── GET /parlamentar/votos/por-tema
    ├── GET /parlamentar/votos/por-uf
    ├── GET /parlamentar/votos/timeline
    ├── GET /parlamentar/votos/ranking
    └── Testes

3.2 Páginas de Proposições (Frontend)
    ├── /proposicoes — Lista com filtros (tipo, tema, ano, ordenação)
    ├── /proposicoes/[id] — Detalhe com análise IA + votos + comparativo
    ├── Componentes: ProposicaoCard, AnaliseIAPanel, VotoPopularChart
    └── Testes

3.3 Votação Popular (Frontend)
    ├── /votacao-popular — Panorama geral
    ├── /votacao-popular/por-tema — Gráficos por tema
    ├── /votacao-popular/por-regiao — Heatmap por UF
    ├── Componentes de chart (bar, donut, heatmap)
    └── Testes
```

### Fase 4 — Comparativos e Meu Mandato (2-3 semanas)

```
4.1 API Comparativos e Mandato (Backend)
    ├── GET /parlamentar/comparativos (com filtros)
    ├── GET /parlamentar/comparativos/evolucao
    ├── GET /parlamentar/meu-mandato/resumo
    ├── GET /parlamentar/meu-mandato/alinhamento
    └── Testes

4.2 Comparativos (Frontend)
    ├── /comparativos — Lista com filtros de alinhamento
    ├── /comparativos/evolucao — Gráfico de evolução temporal
    ├── ComparativoBadge, AlinhamentoGauge
    └── Testes

4.3 Meu Mandato (Frontend)
    ├── /meu-mandato — Resumo personalizado do deputado logado
    ├── /meu-mandato/alinhamento — Evolução pessoal
    ├── Comparação com outros do partido/UF
    └── Testes
```

### Fase 5 — Polimento (1-2 semanas)

```
5.1 Exportação
    ├── Backend: endpoints CSV + PDF (reportlab ou weasyprint)
    ├── Frontend: botões de download, loading states
    └── Testes

5.2 UX & Performance
    ├── Responsive design (tablet, mobile)
    ├── Dark mode (Tailwind)
    ├── Polling automático com TanStack Query (refetchInterval)
    ├── Prefetch em hover/focus de links
    ├── SEO meta tags
    └── Lighthouse audit

5.3 Configurações
    ├── /configuracoes — Perfil, temas acompanhados, notificações email
    ├── Backend: PUT /parlamentar/auth/me (atualizar preferências)
    └── Testes

5.4 Testes E2E
    ├── Playwright: fluxo completo login → dashboard → detalhe → export
    ├── CI pipeline: lint + test + build + e2e
    └── Deploy pipeline para Vercel
```

---

## 12. Docker Compose (Atualização)

```yaml
# docker-compose.yaml — adicionar serviço do dashboard (dev)
services:
  # ... serviços existentes ...

  dashboard:
    build: ./dashboard
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXTAUTH_URL=http://localhost:3000
    depends_on: [backend]
    volumes:
      - ./dashboard/src:/app/src  # Hot-reload
```

---

## 13. Estimativa de Esforço

| Fase | Duração | Backend | Frontend | Total |
|------|---------|---------|----------|-------|
| 1 — Fundação | 2-3 sem | Auth + JWT + Magic Link | Setup + Auth pages | ~80h |
| 2 — Dashboard Core | 2-3 sem | API KPIs + agregações | Dashboard + layout | ~80h |
| 3 — Proposições + Votos | 2-3 sem | API votos analíticos | 4 páginas + charts | ~80h |
| 4 — Comparativos + Mandato | 2-3 sem | API mandato | 4 páginas + charts | ~80h |
| 5 — Polimento | 1-2 sem | Export + email | UX + E2E + config | ~50h |
| **Total** | **9-14 sem** | | | **~370h** |

---

## 14. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Volume de dados insuficiente para dashboards úteis | Média | Alto | Seed data + sync agressivo antes do launch |
| Parlamentares não adotam a ferramenta | Alta | Alto | UX excelente + onboarding com assessores + mobile-friendly |
| Magic Link não chega (email filtrado) | Média | Médio | Fallback para código OTP manual + whitelist domínio |
| Performance de queries analíticas | Baixa | Médio | Materializar views, cache Redis para KPIs |
| Integração gov.br complexa | Alta | Baixo (fase futura) | Manter Magic Link como opção primária permanente |

---

## 15. Decisões Ainda Pendentes

1. **Monorepo tooling**: usar Turborepo para gerenciar backend + dashboard, ou manter independentes? Manter Independentes
2. **Email provider**: Resend (mais simples, API-first) vs SMTP genérico (mais controle)? Resend
3. **Assessores**: permitir que assessores tenham contas separadas vinculadas ao deputado? Sim
4. **Dados públicos vs restritos**: todo dado do dashboard é público, ou tem níveis de acesso? Público
5. **Real-time**: usar WebSockets/SSE para atualizar dashboard em tempo real, ou polling é suficiente? WebSockets/SSE
6. **i18n**: dashboard apenas em pt-BR, ou preparar para inglês (accountability internacional)? pt-BR
