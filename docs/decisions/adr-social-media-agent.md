# ADR: SocialMediaAgent — Agente de Publicação em Redes Sociais

> **Status**: Proposta  
> **Data**: 2026-03-14  
> **Autor**: Design Parlamentaria  

---

## 1. Contexto e Motivação

A Parlamentaria já possui um ciclo completo de democracia participativa: eleitores
votam via Telegram, votos são consolidados, comparativos são gerados e publicados via
RSS/Webhooks. Porém, o **alcance atual é limitado a quem já está no Telegram ou assinou
o RSS**.

Para ampliar a visibilidade e engajamento da plataforma, precisamos de **presença ativa
em redes sociais** — onde milhões de brasileiros já estão. O agente deve publicar
automaticamente conteúdo relevante sobre a atividade legislativa, comparativos de
votação e resumos semanais, **incluindo imagens** que maximizem o engajamento.

### Objetivos

1. **Ampliar alcance** — levar dados legislativos para onde as pessoas estão (X, Facebook, Instagram, LinkedIn).
2. **Gerar engajamento** — posts com imagens/infográficos que viralizam.
3. **Transparência legislativa** — mostrar como o povo votou vs como a Câmara votou.
4. **Atrair novos eleitores** — CTA nos posts direcionando para o bot do Telegram.
5. **Automação completa** — posts gerados e publicados sem intervenção humana.

---

## 2. Tipos de Conteúdo

### 2.1 Resumo Semanal (`post_resumo_semanal`)

**Frequência**: Segunda-feira, 10h (logo após o digest semanal dos eleitores).  
**Trigger**: Celery Beat schedule.

Conteúdo:
- KPIs da semana: novas proposições, total de votos, novos eleitores.
- Top 3 proposições mais votadas.
- Comparativos publicados na semana (alinhamento pop vs real).
- Agenda da semana: votações previstas.

**Imagem**: Card infográfico com os números da semana (template visual).

### 2.2 Alerta de Votação Relevante (`post_votacao_relevante`)

**Frequência**: Tempo real (quando sync detecta votação importante).  
**Trigger**: Evento `nova_votacao_sincronizada` ou threshold de votos populares.

Conteúdo:
- Proposição em votação/votada (tipo, número, ementa resumida).
- Resultado da votação popular (SIM X% / NÃO Y%).
- CTA: "Você concorda? Vote no Telegram!"

**Imagem**: Barra de progresso visual SIM vs NÃO com percentuais.

### 2.3 Comparativo Pop vs Real (`post_comparativo`)

**Frequência**: Quando um comparativo é gerado.  
**Trigger**: Evento da task `gerar_comparativos_task` (já existente).

Conteúdo:
- Proposição votada na Câmara.
- Resultado popular (SIM X% / NÃO Y%) vs resultado real (APROVADA/REJEITADA).
- Índice de alinhamento (0-100%).
- Análise: "O povo e a Câmara concordaram" ou "Divergência: o povo queria X, a Câmara decidiu Y".

**Imagem**: Infográfico comparativo lado a lado (POVO vs CÂMARA).

### 2.4 Destaque de Proposição (`post_destaque_proposicao`)

**Frequência**: Quando proposição atinge threshold de votos ou é trending.  
**Trigger**: Threshold configurável (ex: 100+ votos em 24h).

Conteúdo:
- Resumo acessível da proposição (do `AnaliseIA`).
- Áreas afetadas (saúde, educação, economia, etc.).
- Status atual e resultado parcial da votação popular.
- CTA para votar.

**Imagem**: Card com ementa, áreas e barras de votação.

### 2.5 Filtro de Tipos de Proposição Relevantes

Nem todo tipo de proposição legislativa tem relevância direta para o cidadão comum.
O agente **filtra automaticamente** os tipos que merecem posts nas redes sociais,
evitando poluição com requerimentos internos e atos procedurais.

**Tipos RELEVANTES** (geram posts):

| Sigla | Nome Completo | Por quê |
|-------|---------------|----------|
| **PEC** | Proposta de Emenda à Constituição | Altera a Constituição — impacto máximo na vida do cidadão |
| **MPV** | Medida Provisória | Força de lei imediata, precisa de aprovação parlamentar |
| **PL** | Projeto de Lei | Principal veículo legislativo, cria/altera leis ordinárias |
| **PLP** | Projeto de Lei Complementar | Regulamenta artigos constitucionais — impacto estrutural |
| **PDL** | Projeto de Decreto Legislativo | Ratifica tratados, susta atos — impacto direto |

**Tipos NÃO RELEVANTES** (ignorados para posts — processamento interno apenas):

| Sigla | Nome | Razão para excluir |
|-------|------|--------------------|
| REQ | Requerimento | Ato procedimental interno |
| RIC | Requerimento de Informação | Pedido de informação ao Executivo |
| INC | Indicação | Sugestão não vinculante |
| RCP | Requerimento de CPI | Relevante, mas raro — pode ser adicionado futuramente |
| PFC | Proposta de Fiscalização e Controle | Técnico, pouco compreensível ao público geral |
| EMC | Emenda de Comissão | Fragmento de proposição maior |
| SBT | Substitutivo | Geralmente coberto pelo PL/PEC original |

**Configuração** (variável de ambiente):
```bash
SOCIAL_RELEVANT_TYPES=PEC,MPV,PL,PLP,PDL
```

O filtro é aplicado em todas as tasks de publicação (comparativo, votação, destaque,
educativo) antes de consultar dados e gerar posts.

**Implementação no código:**
```python
TIPOS_RELEVANTES: set[str] = set(settings.social_relevant_types.split(","))

def is_proposicao_relevante(tipo: str) -> bool:
    """Verifica se o tipo de proposição merece post nas redes sociais."""
    return tipo.upper().strip() in TIPOS_RELEVANTES
```

### 2.6 Explicativo Educativo (`post_explicativo_educativo`)

**Frequência**: Quando nova proposição relevante é sincronizada e analisada pela IA.  
**Trigger**: Pós `generate_embeddings_task` ou pós `analise_service` — quando `AnaliseIA` é gerada.

Conteúdo educativo em linguagem acessível que explica a proposição ao cidadão:
- O que é a proposição (em uma frase simples).
- O que muda na prática para o cidadão.
- Quem é afetado.
- Argumentos a favor e contra (do `AnaliseIA`).
- CTA: "Concorda? Vote no Telegram!"

**Tom**: Didático e acessível — como se explicasse para alguém que não conhece jargão legislativo.
O agente deve evitar termos como "ementa", "tramitação", "relator" sem explicá-los.

**Filtro**: Apenas proposições com tipo em `TIPOS_RELEVANTES` (ver seção 2.5).

**Imagem**: Card com título da proposição, resumo visual de "o que muda" e áreas afetadas.
Template `explicativo.html` — design focado em legibilidade (fonte maior, menos dados,
mais texto explicativo).

**Textos por rede**:
- **Twitter/X**: Thread 1/3, 2/3, 3/3 — (1) O que é, (2) O que muda, (3) CTA para votar.
- **Facebook**: Post longo com parágrafos curtos — abre com pergunta retórica.
- **Instagram**: Caption didática com bullet points e emojis.
- **LinkedIn**: Análise estruturada com contexto legislativo para profissionais.
- **Discord**: Embed com fields estruturados — leitura rápida, imagem embarcada.
- **Reddit**: Self-post em Markdown com headers, listas e links. Tom comunitário.

---

## 3. Arquitetura

### 3.1 Posição no Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│  Triggers                                                       │
│  ├── Celery Beat (resumo semanal)                               │
│  ├── gerar_comparativos_task → evento comparativo_gerado        │
│  ├── sync_votacoes_task → evento nova_votacao                   │
│  └── Threshold de votos populares                               │
├─────────────────────────────────────────────────────────────────┤
│  SocialMediaService (Orquestrador)                              │
│  ├── Consulta dados (ComparativoService, VotoPopularRepo, etc.) │
│  ├── Gera texto via LLM (SocialMediaAgent - Google ADK)         │
│  ├── Gera imagem (ImageGenerationService)                       │
│  └── Publica via SocialPublisher (adapter por rede)             │
├─────────────────────────────────────────────────────────────────┤
│  SocialPublisher (Channel Adapter Pattern)                      │
│  ├── TwitterPublisher (X API v2)                                │
│  ├── FacebookPublisher (Graph API)                              │
│  ├── InstagramPublisher (Graph API)                             │
│  ├── LinkedInPublisher (LinkedIn API)                           │
│  ├── DiscordPublisher (Webhook — servidor próprio)              │
│  └── RedditPublisher (PRAW — r/parlamentaria)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Diagrama de Fluxo

```
Trigger (Celery/Evento)
    │
    ▼
SocialMediaService.generate_and_publish(tipo, dados)
    │
    ├─→ Coleta dados (repos/services existentes)
    │
    ├─→ SocialMediaAgent (ADK LlmAgent)
    │   └─→ Gera texto adaptado por rede
    │       ├── X (280 chars, hashtags, thread se necessário)
    │       ├── Facebook (mais longo, emojis, engajamento)
    │       ├── Instagram (caption com hashtags, CTA)
    │       ├── LinkedIn (tom profissional, dados, análise)
    │       ├── Discord (embed rico com campos + imagem)
    │       └── Reddit (post r/parlamentaria, markdown)
    │
    ├─→ ImageGenerationService
    │   └─→ Gera infográfico/card visual
    │       ├── Templates HTML/CSS → PNG (Playwright headless Chromium)
    │       └── Opcional futuro: backgrounds IA (Flux/SDXL) compostos em camada
    │
    ├─→ Fila de Moderação (opcional, configurável)
    │   └─→ review_queue (Redis) — admin aprova antes de postar
    │
    └─→ SocialPublisher.publish(rede, texto, imagem)
        ├── Twitter → tweepy / httpx
        ├── Facebook → httpx (Graph API)
        ├── Instagram → httpx (Graph API)
        ├── LinkedIn → httpx (LinkedIn API)
        ├── Discord → httpx (Webhook URL)
        └── Reddit → praw (r/parlamentaria)
```

### 3.3 Novo Sub-Agent: SocialMediaAgent

```python
# agents/parlamentar/sub_agents/social_media_agent.py

social_media_agent = LlmAgent(
    name="SocialMediaAgent",
    model=settings.agent_model,
    instruction=SOCIAL_MEDIA_AGENT_INSTRUCTION,
    tools=[
        gerar_texto_post_social,
        gerar_imagem_post,
        publicar_post,
        listar_posts_recentes,
        obter_metricas_posts,
    ],
)
```

**Nota**: O `SocialMediaAgent` NÃO é um sub-agent do `ParlamentarAgent` (Root Agent do
eleitor). Ele opera de forma **autônoma via Celery tasks**, sem interação conversacional
direta. O agente usa o LLM para gerar textos otimizados por rede social, mas não conversa
com eleitores.

---

## 4. Componentes Novos

### 4.1 Estrutura de Arquivos

```
agents/parlamentar/
├── sub_agents/
│   └── social_media_agent.py        # LlmAgent para geração de texto
├── tools/
│   └── social_media_tools.py        # FunctionTools do agente

backend/app/
├── domain/
│   └── social_post.py               # Modelo ORM SocialPost
├── schemas/
│   └── social_post.py               # DTOs Pydantic
├── repositories/
│   └── social_post_repo.py          # Data access
├── services/
│   ├── social_media_service.py      # Orquestração: dados → texto → imagem → publish
│   └── image_generation_service.py  # Geração de imagens (HTML/CSS → PNG via Playwright)
├── templates/
│   └── social/                      # Templates HTML/CSS Jinja2 para imagens
│       ├── base.html                # Layout base (branding, fontes, paleta)
│       ├── comparativo.html         # POVO vs CÂMARA lado a lado
│       ├── resumo_semanal.html      # Card KPIs da semana
│       ├── votacao.html             # Barras SIM/NÃO/ABSTENÇÃO
│       ├── destaque.html            # Card destaque proposição
│       └── explicativo.html         # Card educativo — "o que muda para você"
├── integrations/
│   ├── social_publisher.py          # ABC + Factory
│   ├── twitter_publisher.py         # X API v2
│   ├── facebook_publisher.py        # Graph API (Facebook + Instagram)
│   ├── linkedin_publisher.py        # LinkedIn Marketing API
│   ├── discord_publisher.py         # Discord Webhook (embed + imagem)
│   └── reddit_publisher.py          # Reddit via PRAW (r/parlamentaria)
├── tasks/
│   └── social_media_tasks.py        # Celery tasks de publicação
└── routers/
    └── social_admin.py              # Endpoints admin para gerenciar posts
```

### 4.2 Modelo de Domínio: SocialPost

```python
class RedesSociais(str, Enum):
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    DISCORD = "discord"
    REDDIT = "reddit"

class TipoPostSocial(str, Enum):
    RESUMO_SEMANAL = "resumo_semanal"
    VOTACAO_RELEVANTE = "votacao_relevante"
    COMPARATIVO = "comparativo"
    DESTAQUE_PROPOSICAO = "destaque_proposicao"
    EXPLICATIVO_EDUCATIVO = "explicativo_educativo"

class StatusPost(str, Enum):
    RASCUNHO = "rascunho"           # Gerado, aguardando moderação
    APROVADO = "aprovado"           # Aprovado para publicação
    PUBLICADO = "publicado"         # Publicado com sucesso
    FALHOU = "falhou"               # Publicação falhou
    CANCELADO = "cancelado"         # Cancelado pelo admin

class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[uuid.UUID]                  # PK
    tipo: Mapped[TipoPostSocial]           # Tipo do post
    rede: Mapped[RedesSociais]             # Rede social destino
    proposicao_id: Mapped[int | None]       # FK proposicao (se aplicável)
    comparativo_id: Mapped[uuid.UUID | None] # FK comparativo (se aplicável)

    # Conteúdo
    texto: Mapped[str]                     # Texto do post
    imagem_url: Mapped[str | None]         # URL da imagem gerada (storage local/S3)
    imagem_path: Mapped[str | None]        # Path local da imagem

    # Publicação
    status: Mapped[StatusPost]             # Status do post
    rede_post_id: Mapped[str | None]       # ID do post na rede social (após publicação)
    publicado_em: Mapped[datetime | None]  # Quando foi publicado
    erro: Mapped[str | None]               # Mensagem de erro (se falhou)

    # Métricas (atualizadas periodicamente)
    likes: Mapped[int]                     # Default 0
    shares: Mapped[int]                    # Default 0 (retweets, compartilhamentos)
    comments: Mapped[int]                  # Default 0
    impressions: Mapped[int]              # Default 0

    # Metadata
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Unique: 1 post por tipo+rede+proposição (evita duplicatas)
    __table_args__ = (
        UniqueConstraint("tipo", "rede", "proposicao_id", "comparativo_id",
                         name="uq_social_post_unique"),
    )
```

### 4.3 SocialPublisher — Channel Adapter Pattern

```python
# backend/app/integrations/social_publisher.py

class SocialPublisher(ABC):
    """Interface abstrata para publicação em redes sociais."""

    @abstractmethod
    async def publish_text(self, text: str) -> PublishResult:
        """Publica post apenas com texto."""
        ...

    @abstractmethod
    async def publish_with_image(self, text: str, image_path: str) -> PublishResult:
        """Publica post com texto e imagem."""
        ...

    @abstractmethod
    async def delete_post(self, post_id: str) -> bool:
        """Remove post publicado."""
        ...

    @abstractmethod
    async def get_metrics(self, post_id: str) -> PostMetrics:
        """Obtém métricas de um post."""
        ...

@dataclass
class PublishResult:
    success: bool
    post_id: str | None        # ID na rede social
    url: str | None            # URL pública do post
    error: str | None          # Mensagem se falhou

@dataclass
class PostMetrics:
    likes: int
    shares: int
    comments: int
    impressions: int
```

### 4.4 ImageGenerationService — Geração de Imagens (HTML → PNG via Playwright)

A estratégia de imagens é **template-based com HTML/CSS renderizado via Playwright** (headless
Chromium), priorizando:
- **Qualidade profissional** — HTML/CSS permite gradientes, sombras, fontes, gráficos CSS, SVG.
- **Texto 100% preciso** — números, percentuais e nomes renderizados como texto real (sem alucinação).
- **Consistência visual** — branding Parlamentaria via CSS (paleta, tipografia, logo).
- **Facilidade de manutenção** — templates HTML/Jinja2 são editáveis por qualquer dev.
- **Custo zero, sem GPU** — Playwright roda em qualquer servidor (~200-500ms por imagem).
- **Adaptação por rede** — mudar viewport = mudar dimensão de saída.

#### Arquitetura de Templates

Templates HTML usam **Jinja2** para injeção de dados e **CSS inline** (sem dependências externas):

```
backend/app/templates/social/
├── base.html                 # Layout base: <head> com fontes, CSS vars, branding
├── comparativo.html          # extends base — POVO vs CÂMARA lado a lado
├── resumo_semanal.html       # extends base — KPIs, ranking, agenda
├── votacao.html              # extends base — barras SIM/NÃO/ABSTENÇÃO
├── destaque.html             # extends base — card proposição com resumo
└── explicativo.html          # extends base — card educativo didático
```

#### Service

```python
# backend/app/services/image_generation_service.py

from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader

# Dimensões otimizadas por rede social
SOCIAL_DIMENSIONS: dict[str, dict[str, tuple[int, int]]] = {
    "twitter":   {"landscape": (1200, 675)},   # 16:9
    "facebook":  {"landscape": (1200, 630)},
    "instagram": {"square": (1080, 1080)},      # 1:1 (obrigatório)
    "linkedin":  {"landscape": (1200, 627)},
}

class ImageGenerationService:
    """Gera infográficos e cards visuais para posts sociais.

    Renderiza templates HTML/CSS via Playwright (headless Chromium)
    e exporta como PNG. Garante texto pixel-perfect e branding
    consistente em todas as imagens.
    """

    def __init__(self, templates_dir: str = "app/templates/social"):
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True,
        )
        self._browser = None

    async def _get_browser(self):
        """Reutiliza instância do browser (connection pool)."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch()
        return self._browser

    async def _render_template(
        self,
        template_name: str,
        context: dict,
        width: int,
        height: int,
        output_path: str,
    ) -> str:
        """Renderiza template HTML como PNG.

        Args:
            template_name: Nome do template Jinja2 (ex: 'comparativo.html').
            context: Dados para injetar no template.
            width: Largura em pixels.
            height: Altura em pixels.
            output_path: Caminho do arquivo PNG de saída.

        Returns:
            Caminho absoluto do arquivo PNG gerado.
        """
        template = self.jinja_env.get_template(template_name)
        html = template.render(**context)

        browser = await self._get_browser()
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=output_path, type="png")
        await page.close()
        return output_path

    async def generate_comparativo_image(
        self,
        proposicao: str,
        voto_popular_sim: float,
        voto_popular_nao: float,
        resultado_camara: str,
        alinhamento: float,
        rede: str = "twitter",
    ) -> str:
        """Gera imagem comparativa POVO vs CÂMARA."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "comparativo.html",
            {"proposicao": proposicao, "sim": voto_popular_sim,
             "nao": voto_popular_nao, "resultado": resultado_camara,
             "alinhamento": alinhamento},
            width, height, self._output_path("comparativo", rede),
        )

    async def generate_resumo_semanal_image(
        self,
        total_proposicoes: int,
        total_votos: int,
        total_eleitores: int,
        top_proposicoes: list[dict],
        periodo: str,
        rede: str = "twitter",
    ) -> str:
        """Gera card com resumo semanal."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "resumo_semanal.html",
            {"total_proposicoes": total_proposicoes, "total_votos": total_votos,
             "total_eleitores": total_eleitores, "top": top_proposicoes,
             "periodo": periodo},
            width, height, self._output_path("resumo_semanal", rede),
        )

    async def generate_votacao_image(
        self,
        proposicao: str,
        sim_pct: float,
        nao_pct: float,
        abstencao_pct: float,
        total_votos: int,
        temas: list[str],
        rede: str = "twitter",
    ) -> str:
        """Gera barra de progresso visual da votação popular."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "votacao.html",
            {"proposicao": proposicao, "sim": sim_pct, "nao": nao_pct,
             "abstencao": abstencao_pct, "total": total_votos, "temas": temas},
            width, height, self._output_path("votacao", rede),
        )

    async def generate_destaque_proposicao_image(
        self,
        proposicao: str,
        ementa_resumida: str,
        areas: list[str],
        sim_pct: float,
        nao_pct: float,
        rede: str = "twitter",
    ) -> str:
        """Gera card de destaque com resumo e votação."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "destaque.html",
            {"proposicao": proposicao, "ementa": ementa_resumida,
             "areas": areas, "sim": sim_pct, "nao": nao_pct},
            width, height, self._output_path("destaque", rede),
        )

    async def generate_explicativo_image(
        self,
        proposicao: str,
        o_que_muda: str,
        areas: list[str],
        argumentos_favor: list[str],
        argumentos_contra: list[str],
        rede: str = "twitter",
    ) -> str:
        """Gera card educativo — foco em legibilidade e linguagem acessível."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "explicativo.html",
            {"proposicao": proposicao, "o_que_muda": o_que_muda,
             "areas": areas, "favor": argumentos_favor[:3],
             "contra": argumentos_contra[:3]},
            width, height, self._output_path("explicativo", rede),
        )

    def _dimensions_for(self, rede: str) -> tuple[int, int]:
        dims = SOCIAL_DIMENSIONS.get(rede, SOCIAL_DIMENSIONS["twitter"])
        return list(dims.values())[0]

    def _output_path(self, tipo: str, rede: str) -> str:
        from app.config import get_settings
        import uuid
        settings = get_settings()
        filename = f"{tipo}_{rede}_{uuid.uuid4().hex[:8]}.png"
        return f"{settings.social_images_dir}/{filename}"

    async def close(self):
        """Fecha o browser. Chamar no shutdown da aplicação."""
        if self._browser:
            await self._browser.close()
            await self._playwright.stop()
```

#### Exemplo de Template HTML (comparativo.html)

```html
<!-- backend/app/templates/social/comparativo.html -->
<!DOCTYPE html>
<html>
<head>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      padding: 40px;
    }
    .card {
      width: 100%;
      max-width: 1100px;
      background: rgba(255,255,255,0.05);
      border-radius: 24px;
      padding: 48px;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.1);
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 32px;
    }
    .logo { font-size: 18px; font-weight: 700; color: #60a5fa; }
    .tag { font-size: 14px; color: #94a3b8; }
    .proposicao { font-size: 28px; font-weight: 800; margin-bottom: 40px; }
    .versus {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 32px;
      align-items: center;
    }
    .side { text-align: center; }
    .side-label { font-size: 14px; color: #94a3b8; margin-bottom: 8px; }
    .side-value { font-size: 48px; font-weight: 800; }
    .side-detail { font-size: 16px; color: #cbd5e1; margin-top: 8px; }
    .vs { font-size: 24px; color: #475569; font-weight: 700; }
    .povo .side-value { color: #60a5fa; }
    .camara .side-value { color: {{ '#4ade80' if resultado == 'APROVADO' else '#f87171' }}; }
    .alinhamento {
      margin-top: 40px;
      text-align: center;
      padding: 20px;
      background: rgba(255,255,255,0.05);
      border-radius: 16px;
    }
    .alinhamento-label { font-size: 14px; color: #94a3b8; }
    .alinhamento-value { font-size: 36px; font-weight: 800; color: #fbbf24; }
    .footer {
      margin-top: 32px;
      text-align: center;
      font-size: 14px;
      color: #64748b;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <span class="logo">🏛️ Parlamentaria</span>
      <span class="tag">Comparativo de Votação</span>
    </div>
    <div class="proposicao">{{ proposicao }}</div>
    <div class="versus">
      <div class="side povo">
        <div class="side-label">🗳️ VOTO POPULAR</div>
        <div class="side-value">{{ '%.0f' % sim }}% SIM</div>
        <div class="side-detail">{{ '%.0f' % nao }}% NÃO</div>
      </div>
      <div class="vs">VS</div>
      <div class="side camara">
        <div class="side-label">🏛️ CÂMARA</div>
        <div class="side-value">{{ resultado }}</div>
        <div class="side-detail">Votação oficial</div>
      </div>
    </div>
    <div class="alinhamento">
      <div class="alinhamento-label">Índice de Alinhamento</div>
      <div class="alinhamento-value">{{ '%.0f' % alinhamento }}%</div>
    </div>
    <div class="footer">parlamentaria.app — democracia participativa</div>
  </div>
</body>
</html>
```

#### Design Visual

- **Paleta**: Dark mode moderno (slate/navy) com acentos coloridos (azul, verde, vermelho, amarelo).
- **Tipografia**: Inter (Google Fonts, open source, carregada via import CSS).
- **Branding**: Logo "🏛️ Parlamentaria" no header de cada card.
- **Dimensões otimizadas por rede** (viewport do Playwright):
  - X/Twitter: 1200×675 px (16:9)
  - Facebook: 1200×630 px
  - Instagram: 1080×1080 px (quadrado)
  - LinkedIn: 1200×627 px

#### Evolução Futura: Backgrounds IA (Opcional)

Quando houver GPU disponível, é possível compor imagens em camadas:

```
[Background artístico via Flux.1-schnell (open-source)] + [Overlay dados HTML→PNG] = Imagem final
```

A IA geraria apenas backgrounds/texturas (sem texto), e os dados continuariam
vindo do HTML renderizado com Playwright. Isso é um enhancement futuro, não
requisito do MVP.

### 4.5 Geração de Texto via LLM (SocialMediaAgent)

O agente gera textos **otimizados por rede social** a partir dos dados estruturados:

```python
SOCIAL_MEDIA_AGENT_INSTRUCTION = """
Você é o redator de redes sociais do Parlamentaria — plataforma de democracia
participativa que conecta eleitores à Câmara dos Deputados.

Seu papel é transformar dados legislativos em posts ENGAJANTES para redes sociais.

REGRAS:
- Tom apartidário e informativo — NUNCA emita opinião política.
- Use dados concretos: percentuais, números, nomes de proposições.
- Cada rede tem formato diferente. Adapte o texto.
- Inclua CTA direcionando ao bot Telegram do Parlamentaria.
- Use emojis com moderação (2-4 por post).
- Hashtags relevantes: #Parlamentaria #DemocraciaParticipativa #CâmaraDosDeputados

FORMATOS POR REDE:
- Twitter/X: Máx 280 caracteres. Direto, impactante. Hashtags no final.
  Se necessário, gere thread (tweets numerados 1/N).
- Facebook: 1-3 parágrafos. Tom conversacional, pergunta ao final.
- Instagram: Caption com emojis. Hashtags separadas (30 max). CTA no primeiro parágrafo.
- LinkedIn: Tom profissional e analítico. Dados, contexto, insight. 2-4 parágrafos.

TIPO ESPECIAL — EXPLICATIVO EDUCATIVO:
- Explique a proposição como se falasse com alguém que NÃO entende política.
- Evite jargão: troque "ementa" por "resumo", "tramitação" por "andamento",
  "relator" por "deputado responsável".
- Estruture em: (1) O que é, (2) O que muda na sua vida, (3) Prós e contras.
- Twitter: Thread 1/3, 2/3, 3/3 (O que é → O que muda → Vote).
- Facebook: Abra com pergunta retórica ("Você sabia que...").
- Instagram: Bullet points com emojis — visual de "carrossel mental".
- LinkedIn: Análise estruturada com contexto para profissionais.
- Discord: Embed com campos "O que é", "O que muda", "Prós e contras".
- Reddit: Post markdown completo com ## headers e listas. Tom comunitário, sem CTA agressivo.
- Discord: Texto para embed — field "title" (curto) + field "description" (corpo).
  Markdown do Discord: **negrito**, *itálico*, [links](url). Sem hashtags.
- Reddit: Post completo em Markdown. Título direto (sem emoji). Corpo com headers ##,
  listas, links. Tom informativo, comunitário. Sem CTA agressivo.

NUNCA mencione detalhes técnicos internos (modelos IA, endpoints, banco de dados).
"""
```

### 4.6 Celery Tasks

```python
# backend/app/tasks/social_media_tasks.py

@celery_app.task(name="social.post_resumo_semanal")
def post_resumo_semanal_task():
    """Gera e publica resumo semanal em todas as redes. Rodada segundas 10h."""
    ...

@celery_app.task(name="social.post_comparativo")
def post_comparativo_task(comparativo_id: str):
    """Gera e publica post de comparativo. Triggered por gerar_comparativos_task."""
    ...

@celery_app.task(name="social.post_votacao_relevante")
def post_votacao_relevante_task(proposicao_id: int):
    """Publica quando proposição atinge threshold de votos."""
    ...

@celery_app.task(name="social.post_destaque_proposicao")
def post_destaque_proposicao_task(proposicao_id: int):
    """Publica destaque de proposição trending."""
    ...

@celery_app.task(name="social.post_explicativo_educativo")
def post_explicativo_educativo_task(proposicao_id: int):
    """Gera e publica post educativo explicando a proposição.
    Triggered quando AnaliseIA é gerada para proposição com tipo relevante.
    Filtra por TIPOS_RELEVANTES antes de processar."""
    ...

@celery_app.task(name="social.atualizar_metricas")
def atualizar_metricas_task():
    """Atualiza likes/shares/comments dos posts das últimas 48h. Rodada 4x/dia."""
    ...

@celery_app.task(name="social.publicar_post_aprovado")
def publicar_post_aprovado_task(post_id: str):
    """Publica um post que estava aguardando moderação e foi aprovado."""
    ...
```

**Celery Beat Schedule (novos entries):**

| Task                        | Schedule                        | Config                             |
|-----------------------------|---------------------------------|------------------------------------|
| `post_resumo_semanal`       | Segundas, `SOCIAL_WEEKLY_HOUR` | `social_weekly_hour` (default 10)  |
| `atualizar_metricas`        | A cada 6h                       | Fixo                               |

---

## 5. APIs Externas — Requisitos por Rede

### 5.1 X (Twitter) — API v2

**Requisitos**:
- Conta Developer (Free tier: 1.500 tweets/mês — suficiente).
- App com permissão "Read and Write".
- OAuth 1.0a User Context (para postar como a conta @Parlamentaria).

**Biblioteca**: `tweepy>=4.14` (suporte nativo a X API v2 + upload de media).

**Endpoints**:
- `POST /2/tweets` — Criar tweet (texto + media_ids).
- `POST /1.1/media/upload` — Upload de imagem (até 5MB).
- `GET /2/tweets/:id` — Métricas públicas.

**Limites Free Tier**:
- 1.500 tweets/mês (criação).
- 50 requests/15min (leitura).
- Upload de mídia ilimitado via v1.1.

### 5.2 Facebook — Graph API

**Requisitos**:
- Facebook App com Page Token de longa duração.
- Permissões: `pages_manage_posts`, `pages_read_engagement`.
- Página do Parlamentaria (não perfil pessoal).

**Biblioteca**: `httpx` (chamadas diretas à Graph API — mais leve que SDK).

**Endpoints**:
- `POST /{page-id}/feed` — Post com texto + link.
- `POST /{page-id}/photos` — Post com imagem.
- `GET /{post-id}?fields=likes.summary(true),shares,comments.summary(true)` — Métricas.

**Limites**: 200 calls/hora/user (amplo para o uso).

### 5.3 Instagram — Graph API (via Facebook)

**Requisitos**:
- Conta Instagram Business vinculada à Facebook Page.
- Mesmas permissões da Facebook App + `instagram_basic`, `instagram_content_publish`.
- **Imagem obrigatória** — Instagram não aceita posts só-texto.

**Endpoints** (Container-based publishing):
1. `POST /{ig-user-id}/media` — Criar container (image_url + caption).
2. `POST /{ig-user-id}/media_publish` — Publicar o container.
3. `GET /{media-id}/insights` — Métricas.

**Restrição importante**: A imagem precisa estar acessível via URL pública (não aceita
upload direto). Solução: usar storage público temporário (presigned URL S3 ou servir via
endpoint estático do FastAPI).

### 5.4 LinkedIn — Marketing API

**Requisitos**:
- LinkedIn Page (Organization) do Parlamentaria.
- App com produto "Share on LinkedIn" e "Marketing Developer Platform".
- OAuth 2.0 com scope `w_organization_social`.

**Biblioteca**: `httpx` (chamadas diretas).

**Endpoints**:
- `POST /rest/posts` — Criar post com texto + imagem.
- Upload de imagem: `POST /rest/images?action=initializeUpload` (obter upload URL) →
  `PUT {uploadUrl}` (enviar bytes) → usar `image URN` no post.
- `GET /rest/organizationalEntityShareStatistics` — Métricas.

**Limites**: 100 posts/dia por Organization (amplo).

### 5.5 Discord — Webhooks

**Requisitos**:
- Servidor Discord do Parlamentaria (criação gratuita).
- Webhook URL por canal (criado em Server Settings → Integrations → Webhooks).
- Sem app, sem OAuth, sem aprovação — **pronto para usar em minutos**.

**Biblioteca**: `httpx` (POST simples com JSON).

**Endpoint**:
- `POST {webhook_url}` — Envia mensagem com embed rico.

**Estrutura do Embed**:
```python
# Payload Discord Webhook
{
    "embeds": [{
        "title": "PL 1234/2026 — Reforma Tributária",
        "description": "73% dos eleitores votaram SIM...",
        "color": 0x60a5fa,  # Azul Parlamentaria
        "fields": [
            {"name": "🗳️ Voto Popular", "value": "73% SIM / 21% NÃO", "inline": True},
            {"name": "🏛️ Câmara", "value": "APROVADO", "inline": True},
            {"name": "Alinhamento", "value": "95%", "inline": True},
        ],
        "image": {"url": "https://parlamentaria.app/images/comparativo_123.png"},
        "footer": {"text": "parlamentaria.app — democracia participativa"},
        "timestamp": "2026-03-14T10:00:00-03:00",
    }]
}
```

**Canais sugeridos no servidor**:
- `#votações` — comparativos e votações relevantes
- `#resumo-semanal` — resumo semanal automático
- `#educativo` — posts explicativos de proposições
- `#geral` — destaques e alertas

**Limites**: 30 mensagens/minuto por webhook (mais que suficiente).

**Vantagens**:
- Zero autenticação complexa — apenas 1 URL por canal.
- Rich embeds nativos — cores, campos, imagens, timestamps.
- Notificações push — membros recebem alertas automaticamente.
- Comunidade própria — sem risco de moderação externa.

### 5.6 Reddit — API via PRAW

**Requisitos**:
- Conta Reddit dedicada (u/ParlamentariaBot).
- Reddit App (tipo "script") registrada em https://www.reddit.com/prefs/apps.
- Subreddit próprio **r/parlamentaria** (criado e moderado pela conta).

**Biblioteca**: `praw>=7.7` (Python Reddit API Wrapper — síncrono, rodar em thread).

**Endpoints utilizados** (via PRAW):
- `subreddit.submit()` — Post de texto (self post) com Markdown.
- `subreddit.submit_image()` — Post com imagem.
- `submission.reply()` — Adicionar comentário ao post (para complementar info).

**Estratégia — Subreddit Próprio (r/parlamentaria)**:

O agente publica **exclusivamente no r/parlamentaria** (subreddit próprio), evitando
riscos de ban em subs externos. Vantagens:
- Conta é moderadora — sem restrições de karma, idade ou anti-spam.
- Controle total de regras, flairs e sidebar.
- Comunidade pode crescer organicamente.
- Cross-posts para r/brasil, r/politica podem ser feitos **manualmente** por humanos.

**Flairs automáticos**:
- `Comparativo` — posts de comparativo pop vs real
- `Votação Popular` — resultados de votação
- `Explicativo` — posts educativos
- `Resumo Semanal` — resumo da semana

**Limites API Reddit Free Tier**:
- 100 requests/minuto (autenticado).
- Sem limite de posts no subreddit próprio.
- Rate limit de 10 min entre posts para contas novas (desaparece com karma).

**Restrições importantes**:
- **NÃO postar automaticamente em subs externos** (r/brasil, r/politica, etc.) —
  risco alto de ban por spam/autopromoção.
- PRAW é síncrono — wrappear com `asyncio.to_thread()` nas tasks Celery.
- Conta precisa de karma mínimo — construir manualmente nos primeiros dias.

---

## 6. Variáveis de Ambiente (Novas)

```bash
# === Redes Sociais ===

# Geral
SOCIAL_ENABLED=true                        # Habilita/desabilita publicação social
SOCIAL_MODERATION_ENABLED=false            # Se true, posts ficam em "rascunho" até admin aprovar
SOCIAL_NETWORKS=twitter,facebook,instagram,linkedin,discord,reddit  # Redes ativas (CSV)
SOCIAL_WEEKLY_HOUR=10                      # Hora do resumo semanal (0-23)
SOCIAL_VOTE_THRESHOLD=50                   # Votos para disparar post de destaque
SOCIAL_RELEVANT_TYPES=PEC,MPV,PL,PLP,PDL     # Tipos de proposição que geram posts (CSV)
SOCIAL_EDUCATIONAL_ENABLED=true               # Habilita posts educativos/explicativos
SOCIAL_CTA_URL=https://t.me/ParlamentariaBot  # URL no CTA dos posts

# Twitter/X
TWITTER_API_KEY=                           # API Key (Consumer Key)
TWITTER_API_SECRET=                        # API Secret (Consumer Secret)
TWITTER_ACCESS_TOKEN=                      # Access Token (conta @Parlamentaria)
TWITTER_ACCESS_TOKEN_SECRET=               # Access Token Secret
TWITTER_ENABLED=true                       # Habilitar/desabilitar Twitter

# Facebook
FACEBOOK_PAGE_ID=                          # ID da Página
FACEBOOK_PAGE_ACCESS_TOKEN=                # Long-lived Page Token
FACEBOOK_ENABLED=true

# Instagram
INSTAGRAM_USER_ID=                         # ID da conta Business
INSTAGRAM_ACCESS_TOKEN=                    # Token (mesma app Facebook)
INSTAGRAM_ENABLED=true

# LinkedIn
LINKEDIN_ORGANIZATION_ID=                  # URN da Organization
LINKEDIN_ACCESS_TOKEN=                     # OAuth 2.0 token
LINKEDIN_ENABLED=true

# Discord
DISCORD_WEBHOOK_VOTACOES=                   # Webhook URL do canal #votações
DISCORD_WEBHOOK_RESUMO=                     # Webhook URL do canal #resumo-semanal
DISCORD_WEBHOOK_EDUCATIVO=                  # Webhook URL do canal #educativo
DISCORD_WEBHOOK_GERAL=                      # Webhook URL do canal #geral
DISCORD_ENABLED=true

# Reddit
REDDIT_CLIENT_ID=                           # App client ID (tipo "script")
REDDIT_CLIENT_SECRET=                       # App client secret
REDDIT_USERNAME=ParlamentariaBot            # Username da conta Reddit
REDDIT_PASSWORD=                            # Password da conta Reddit
REDDIT_SUBREDDIT=parlamentaria              # Subreddit próprio (sem r/)
REDDIT_ENABLED=true

# Imagens
SOCIAL_IMAGES_DIR=/app/data/social_images  # Diretório para imagens geradas
SOCIAL_IMAGES_PUBLIC_URL=                  # URL base pública para imagens (necessário p/ Instagram)
```

---

## 7. Fila de Moderação (Opcional)

O sistema suporta dois modos de operação configuráveis via `SOCIAL_MODERATION_ENABLED`:

### Modo Automático (`false` — default)
- Posts são gerados e publicados imediatamente.
- Ideal para operação estável após período de testes.

### Modo Moderado (`true`)
- Posts são gerados com status `RASCUNHO`.
- Admin revisa e aprova via endpoint ou futuro painel admin.
- Aprovação dispara `publicar_post_aprovado_task`.

**Recomendação**: iniciar com moderação habilitada nas primeiras semanas, depois migrar
para automático quando a qualidade do conteúdo estiver validada.

---

## 8. Endpoints Admin (Novos)

```
# Social Media Admin
GET    /admin/social/posts                   # Lista posts (filtro: rede, tipo, status)
GET    /admin/social/posts/{id}              # Detalhes do post
POST   /admin/social/posts/{id}/aprovar      # Aprovar post em rascunho
POST   /admin/social/posts/{id}/cancelar     # Cancelar post
POST   /admin/social/posts/{id}/republicar   # Re-publicar post que falhou
GET    /admin/social/metricas                # Métricas agregadas (likes, shares, impressions)
POST   /admin/social/preview                 # Preview: gera texto+imagem sem publicar
```

---

## 9. Integração com Tasks Existentes

### 9.1 gerar_comparativos_task (já existe)

Adicionar chamada ao final da geração bem-sucedida de cada comparativo:

```python
# Em backend/app/tasks/gerar_comparativos.py — após gerar comparativo:
if settings.social_enabled:
    post_comparativo_task.delay(str(comparativo.id))
```

### 9.2 sync_votacoes_task (já existe)

Adicionar verificação de threshold de votos populares ao sincronizar votações:

```python
# Quando proposição atinge threshold de votos:
if settings.social_enabled and total_votos >= settings.social_vote_threshold:
    post_votacao_relevante_task.delay(proposicao_id)
```

### 9.3 analise_service (novo trigger para educativos)

Adicionar chamada quando uma `AnaliseIA` é gerada com sucesso:

```python
# Em backend/app/services/analise_service.py — após gerar análise:
from app.services.social_media_service import is_proposicao_relevante

if settings.social_enabled and settings.social_educational_enabled:
    if is_proposicao_relevante(proposicao.tipo):
        post_explicativo_educativo_task.delay(proposicao.id)
```

### 9.4 Celery Beat (adicionar novos schedules)

```python
# Em celery_app.py — beat_schedule:
"social-resumo-semanal": {
    "task": "social.post_resumo_semanal",
    "schedule": crontab(
        hour=settings.social_weekly_hour,
        minute=0,
        day_of_week=settings.digest_weekly_day,  # Reutiliza config existente (0=segunda)
    ),
},
"social-atualizar-metricas": {
    "task": "social.atualizar_metricas",
    "schedule": crontab(hour="*/6", minute=30),  # A cada 6h
},
```

---

## 10. Dependências Novas

```toml
# pyproject.toml — novas dependências
[project.dependencies]
# ... existentes ...
tweepy = ">=4.14.0"              # Twitter/X API v2 (posting + media upload)
playwright = ">=1.44.0"          # Headless Chromium para renderizar HTML→PNG
Jinja2 = ">=3.1.0"              # Templates HTML para imagens (já dep. transitiva do FastAPI)
praw = ">=7.7.0"                 # Reddit API (PRAW — Python Reddit API Wrapper)
```

**Nota sobre Playwright no Docker**: Adicionar `playwright install chromium --with-deps`
no Dockerfile (ou usar imagem base `mcr.microsoft.com/playwright/python:v1.44.0-jammy`).
Tamanho adicional da imagem: ~300MB (Chromium headless).

**Não precisamos de:**
- **Pillow** — Playwright gera imagens de qualidade superior via HTML/CSS.
- **SDKs para Facebook/Instagram/LinkedIn/Discord** — `httpx` (já no projeto) é suficiente.
- **GPU ou modelos de IA generativa** — templates HTML garantem dados precisos e visuais profissionais.

---

## 11. Plano de Implementação (Fases)

### Fase 1 — Fundação (Semana 1-2)

| #  | Tarefa                                                  | Deps         |
|----|---------------------------------------------------------|--------------|
| 1  | Modelo `SocialPost` + migration Alembic                 | —            |
| 2  | `SocialPostRepo` (CRUD + queries)                       | #1           |
| 3  | Schemas Pydantic (`SocialPostCreate`, `SocialPostRead`)  | #1           |
| 4  | Config: novas variáveis em `config.py`                  | —            |
| 5  | `SocialPublisher` ABC + `PublishResult` dataclass       | —            |
| 6  | Testes unitários da base                                | #1-5         |

### Fase 2 — Geração de Imagens (Semana 2-3)

| #  | Tarefa                                                  | Deps         |
|----|---------------------------------------------------------|--------------|
| 7  | `ImageGenerationService` com Playwright + Jinja2        | —            |
| 8  | Template HTML: `base.html` (layout, branding, CSS)      | #7           |
| 9  | Template HTML: `comparativo.html` (POVO vs CÂMARA)      | #8           |
| 10 | Template HTML: `resumo_semanal.html` (KPIs)             | #8           |
| 11 | Template HTML: `votacao.html` (barras SIM/NÃO)          | #8           |
| 12 | Template HTML: `destaque.html` (card proposição)        | #8           |
| 13 | Template HTML: `explicativo.html` (card educativo)      | #8           |
| 14 | Adaptar dimensões por rede via viewport Playwright      | #9-13        |
| 15 | Testes: validar geração de imagens PNG                  | #9-14        |

### Fase 3 — Agente de Texto (Semana 3-4)

| #  | Tarefa                                                  | Deps         |
|----|---------------------------------------------------------|--------------|
| 16 | `SocialMediaAgent` (LlmAgent ADK) + prompts             | —            |
| 17 | `social_media_tools.py` (FunctionTools)                 | #16          |
| 18 | `SocialMediaService` (orquestrador + filtro TIPOS_RELEVANTES) | #5, #7, #16 |
| 19 | Testes: geração de texto por rede                       | #16-18       |

### Fase 4 — Publishers por Rede (Semana 4-5)

| #  | Tarefa                                                  | Deps         |
|----|---------------------------------------------------------|--------------|
| 20 | `TwitterPublisher` (tweepy + media upload)               | #5           |
| 21 | `FacebookPublisher` (httpx + Graph API)                 | #5           |
| 22 | `InstagramPublisher` (httpx + container publishing)      | #5           |
| 23 | `LinkedInPublisher` (httpx + image upload)               | #5           |
| 24 | `DiscordPublisher` (httpx + webhook embed)               | #5           |
| 25 | `RedditPublisher` (praw + r/parlamentaria)               | #5           |
| 26 | Factory pattern para selecionar publisher por rede       | #20-25       |
| 27 | Testes: mock de publicação por rede                     | #20-26       |

### Fase 5 — Celery Tasks + Integração (Semana 5-6)

| #  | Tarefa                                                  | Deps         |
|----|---------------------------------------------------------|--------------|
| 28 | `social_media_tasks.py` (todas as tasks Celery)         | #18          |
| 29 | Integrar `gerar_comparativos_task` → `post_comparativo` | #28          |
| 30 | Integrar Celery Beat (resumo semanal + métricas)        | #28          |
| 31 | Integrar threshold de votos → post destaque             | #28          |
| 32 | Integrar `analise_service` → `post_explicativo_educativo` | #28        |
| 33 | Testes de integração end-to-end                         | #28-32       |

### Fase 6 — Admin + Moderação (Semana 6-7)

| #  | Tarefa                                                  | Deps         |
|----|---------------------------------------------------------|--------------|
| 34 | Router `social_admin.py` (endpoints admin)              | #2           |
| 35 | Fila de moderação (modo rascunho → aprovação)           | #34          |
| 36 | Endpoint preview (gerar sem publicar)                   | #18          |
| 37 | Testes admin                                            | #34-36       |

### Fase 7 — Polimento + Docker (Semana 7-8)

| #  | Tarefa                                                  | Deps         |
|----|---------------------------------------------------------|--------------|
| 38 | Dockerfile: adicionar Playwright + Chromium             | #7           |
| 39 | Rate limiting por rede (evitar bans)                    | #20-25       |
| 40 | Circuit breaker (desativar rede após N falhas)          | #20-25       |
| 41 | Logging estruturado (métricas de publicação)            | #28          |
| 42 | Setup servidor Discord (canais + webhooks)              | #24          |
| 43 | Setup r/parlamentaria (flairs + sidebar + regras)       | #25          |
| 44 | Documentação (AGENTS.md atualizado)                     | Todos        |
| 45 | Testes de carga (verificar limites das APIs)            | #33          |

---

## 12. Riscos e Mitigações

| Risco                                     | Probabilidade | Impacto | Mitigação                                        |
|-------------------------------------------|---------------|---------|--------------------------------------------------|
| Twitter Free Tier muito limitado (1500/mês)| Média        | Baixo   | Priorizar posts mais impactantes; upgrade $100/mês se necessário |
| Facebook/Instagram App Review demorado     | Alta          | Médio   | Submeter review durante Fase 1; testar com Test Users |
| LLM gera texto com viés político           | Baixa         | Alto    | Prompt rígido + moderação inicial + testes eval |
| Templates HTML ficam genéricos              | Baixa         | Baixo   | CSS dark-mode moderno + designer review; fácil iterar HTML  |
| Instagram exige URL pública para imagem    | Certa         | Baixo   | Servir imagens via endpoint estático ou signed URL |
| Rate limit das APIs de redes sociais       | Baixa         | Médio   | Rate limiter por rede + retry com backoff       |
| LinkedIn API requer aprovação especial     | Alta          | Médio   | Aplicar cedo; usar Marketing Developer Platform |
| Reddit: ban por spam em subs externos      | Alta          | Alto    | Postar APENAS em r/parlamentaria (sub próprio); cross-posts manuais |
| Reddit: conta nova com rate limit          | Certa         | Baixo   | Construir karma manualmente nos primeiros dias; rate limit some com karma |
| Discord: servidor precisa de membros       | Média         | Baixo   | Divulgar link de convite nos posts de outras redes; crescimento orgânico |
| Docker image cresce ~300MB (Chromium)       | Certa         | Baixo   | Usar multi-stage build; imagem Playwright oficial; Chromium apenas no worker Celery |

---

## 13. Estimativa de Custos

| Item                        | Custo              | Frequência       |
|-----------------------------|--------------------|------------------|
| Twitter/X API Free Tier     | $0                 | Gratuito         |
| Twitter/X Basic (se escalar)| $100/mês           | Opcional         |
| Facebook/Instagram Graph API| $0                 | Gratuito         |
| LinkedIn Marketing API      | $0                 | Gratuito         |
| Discord Webhooks            | $0                 | Gratuito         |
| Reddit API (Free Tier)      | $0                 | Gratuito         |
| LLM (Gemini Flash)          | ~$0.01-0.05/post   | ~80 posts/mês   |
| Storage imagens              | ~$0.10/mês         | ~200 imagens/mês |
| **Total estimado**          | **~$1-5/mês**      | Modo gratuito    |

---

## 14. Métricas de Sucesso

| Métrica                        | Meta (3 meses)         |
|--------------------------------|------------------------|
| Followers totais (todas redes)  | 1.000+                |
| Engajamento médio por post     | 2%+ (likes+shares/impressões) |
| Novos eleitores via social     | 100+ (tracking via CTA)|
| Posts publicados/semana        | 15-25                  |
| Uptime de publicação           | 95%+                   |

---

## 15. Decisões Técnicas

| Decisão                          | Escolha                      | Alternativa Descartada     | Razão                                    |
|----------------------------------|------------------------------|---------------------------|------------------------------------------|
| Geração de imagem                | HTML→PNG via Playwright       | Pillow, DALL-E, Stable Diffusion, Flux | Qualidade profissional (CSS), texto preciso, custo zero, sem GPU, fácil manutenção (HTML editável) |
| Templates de imagem              | Jinja2 + CSS inline          | React/Satori, Canvas API  | Sem dependência de Node.js; Jinja2 já é dep. transitiva do FastAPI |
| IA generativa para imagens       | Futuro (backgrounds apenas)   | Core da geração           | Modelos não renderizam texto/dados com precisão; composição em camadas é enhancement |
| SDK Twitter                      | tweepy                       | httpx direto              | Media upload complexo sem tweepy         |
| SDK Facebook/Instagram/LinkedIn  | httpx direto                  | SDKs oficiais             | Chamadas simples, sem dependência pesada |
| Discord                          | httpx (Webhook)               | discord.py (bot)          | Webhook é POST simples — bot full é overengineering para publicação unidirecional |
| Reddit                           | PRAW (sub próprio)            | httpx direto / asyncpraw  | PRAW é maduro, auth robusta; sub próprio evita bans; asyncpraw é menos mantido |
| Reddit: sub externo              | NÃO automatizar               | Postar em r/brasil etc.   | Risco altíssimo de ban por spam — regra 90/10 inviável para bot |
| Texto dos posts                  | LLM via SocialMediaAgent      | Templates estáticos        | Variabilidade natural, adaptação por rede |
| Moderação                        | Opcional (config flag)        | Sempre obrigatória        | Flexibilidade — começa moderado, escala para automático |
| Storage de imagens               | Filesystem local + URL pública| S3 / GCS                  | Simplicidade; migrar para S3 quando necessário |
| Agente como sub-agent do Root    | NÃO — agente autônomo via tasks| Sub-agent do ParlamentarAgent | Não é conversacional; opera via Celery |

---

## 16. Exemplo de Posts Gerados

### Comparativo (Twitter/X)
```
📊 PL 1234/2026 — Reforma Tributária

🗳️ Voto Popular: 73% SIM
🏛️ Câmara: APROVADO (310 a 152)

Alinhamento: 95% ✅

O povo e a Câmara concordaram desta vez.

Vote você também → t.me/ParlamentariaBot

#Parlamentaria #DemocraciaParticipativa
```

### Comparativo (LinkedIn)
```
Comparativo de Votação — PL 1234/2026 (Reforma Tributária)

Na plataforma Parlamentaria, 1.247 eleitores expressaram sua opinião sobre
esta proposição. O resultado popular: 73% a favor, 21% contra, 6% abstenção.

Na Câmara dos Deputados, a proposição foi aprovada por 310 votos a 152.

Índice de alinhamento entre voto popular e parlamentar: 95%.

Dados como este ajudam a mensurar o quanto as decisões legislativas refletem
a vontade dos eleitores. Acompanhe mais comparativos em parlamentaria.app.

#DemocraciaParticipativa #TransparênciaLegislativa #CâmaraDosDeputados
```

### Explicativo Educativo (Twitter/X — Thread)
```
🧵 1/3 — PEC 45/2026: O que é a Reforma Tributária?

Essa proposta quer SIMPLIFICAR os impostos no Brasil.
Hoje existem 5 tributos diferentes sobre consumo.
A PEC unifica tudo em 1 só: o IBS.

#Parlamentaria #ReformaTributária
```
```
2/3 — O que muda na SUA vida?

✅ Preços mais transparentes (imposto visível na nota)
✅ Fim da guerra fiscal entre estados
⚠️ Transição de 7 anos — efeitos graduais
❌ Possível aumento em serviços (educação, saúde privada)
```
```
3/3 — E aí, concorda?

🗳️ 68% dos eleitores no Parlamentaria votaram SIM

Vote você também → t.me/ParlamentariaBot

#DemocraciaParticipativa #CâmaraDosDeputados
```

### Explicativo Educativo (Facebook)
```
📚 Você sabia que existe uma proposta para mudar TODOS os impostos do Brasil?

A PEC 45/2026 (Reforma Tributária) quer simplificar o sistema tributário:
ao invés de 5 impostos diferentes sobre consumo, teríamos apenas 1.

🔍 Na prática, o que muda?
• O preço dos produtos mostraria o imposto real (sem "imposto escondido")
• Estados não poderiam mais competir dando isenção fiscal
• Serviços como educação e saúde privada podem ficar mais caros
• A transição levaria 7 anos para ser completa

👍 A favor: simplifica, desburocratiza, mais transparência
👎 Contra: pode encarecer serviços, transição longa e complexa

🗳️ 68% dos eleitores no Parlamentaria apoiam. E você?
Opine no nosso bot: t.me/ParlamentariaBot
```

### Resumo Semanal (Instagram caption)
```
📊 Semana Legislativa — 10 a 14 de Março

🔢 Os números:
• 12 novas proposições em tramitação
• 2.340 votos populares registrados
• 89 novos eleitores participando
• 3 comparativos publicados

🏆 Mais votada da semana:
PL 5678/2026 — Educação Integral (892 votos!)

🗳️ Quer participar? Link na bio!

.
.
.
#Parlamentaria #DemocraciaParticipativa #CâmaraDosDeputados
#PolíticaBrasileira #Transparência #VotoPopular #Legislativo
#Cidadania #Brasil #Democracia
```

### Comparativo (Discord Embed)
```json
{
  "embeds": [{
    "title": "📊 PL 1234/2026 — Reforma Tributária",
    "description": "O povo e a Câmara concordaram desta vez.\n\nVote você também no [Telegram](https://t.me/ParlamentariaBot)!",
    "color": 4302714,
    "fields": [
      {"name": "🗳️ Voto Popular", "value": "**73% SIM** / 21% NÃO", "inline": true},
      {"name": "🏛️ Câmara", "value": "**APROVADO**\n310 a 152", "inline": true},
      {"name": "📈 Alinhamento", "value": "**95%** ✅", "inline": true}
    ],
    "image": {"url": "https://parlamentaria.app/images/comparativo_abc123.png"},
    "footer": {"text": "parlamentaria.app — democracia participativa"},
    "timestamp": "2026-03-14T10:00:00-03:00"
  }]
}
```

### Explicativo Educativo (Reddit — r/parlamentaria)
```markdown
**Título:** PEC 45/2026: O que é a Reforma Tributária e o que muda para você

**Corpo:**

## O que é essa proposição?

A PEC 45/2026 propõe simplificar o sistema tributário brasileiro, unificando
5 impostos sobre consumo (ICMS, ISS, IPI, PIS, COFINS) em um único imposto:
o IBS (Imposto sobre Bens e Serviços).

## O que muda na prática?

- **Preços mais transparentes** — o imposto aparece separado na nota fiscal
- **Fim da guerra fiscal** — estados não podem mais competir com isenções
- **Transição de 7 anos** — mudanças graduais até 2033
- **Possível impacto** em serviços (educação e saúde privada podem ficar mais caros)

## Argumentos

**A favor:** simplificação, desburocratização, mais transparência fiscal

**Contra:** possível encarecimento de serviços, transição longa e complexa

## O que os eleitores acham?

No Parlamentaria, 68% dos eleitores votaram **SIM** nesta proposição.

---

*Dados do [Parlamentaria](https://t.me/ParlamentariaBot) — plataforma de democracia participativa.*

*Flair: Explicativo*
```

---

## 17. Guia de Configuração por Rede Social

> Passo a passo prático para configurar cada rede social e obter as credenciais
> necessárias para os adapters (publishers). Ao final de cada seção, as variáveis
> de ambiente correspondentes estão listadas — preencha-as no `.env`.

### 17.1 Twitter / X

#### Pré-requisitos
- Conta X (Twitter) que será a identidade pública do projeto (ex: `@Parlamentaria`).
- Email e telefone verificados na conta.

#### Passo a Passo

1. **Criar conta de desenvolvedor**
   - Acesse [developer.x.com](https://developer.x.com/) e clique em "Sign up for Free Account".
   - Faça login com a conta `@Parlamentaria`.
   - Descreva o uso: _"Automated posting of legislative transparency data — vote results, comparisons between popular opinion and parliamentary votes, and educational content about Brazilian legislation."_
   - Aceite os termos de uso da API.

2. **Criar um App no Developer Portal**
   - Em **Projects & Apps → + Create App**, dê um nome ao app (ex: `parlamentaria-social`).
   - O portal gera automaticamente:
     - `API Key` → variável `TWITTER_API_KEY`
     - `API Key Secret` → variável `TWITTER_API_SECRET`

3. **Configurar permissões do App**
   - Na aba **Settings → User authentication settings**, clique em **Set up**.
   - Selecione **Read and Write** (necessário para postar tweets e fazer upload de mídia).
   - Em **Type of App**, selecione **Web App, Automated App or Bot**.
   - Preencha os campos obrigatórios de callback URL (ex: `https://parlamentaria.app/callback` — não será usado, mas é obrigatório).
   - Salve.

4. **Gerar Access Token e Secret**
   - Na aba **Keys and Tokens**, seção **Authentication Tokens**, clique em **Generate** para:
     - `Access Token` → variável `TWITTER_ACCESS_TOKEN`
     - `Access Token Secret` → variável `TWITTER_ACCESS_TOKEN_SECRET`
   - **Importante**: esses tokens dão permissão de leitura E escrita na conta. Guarde-os em local seguro.

5. **Validar configuração**
   - O `TwitterPublisher` usa tweepy com OAuth 1.0a User Context (v1.1 para media upload) e tweepy.Client (v2 para criação de tweets).
   - Teste com o endpoint admin: `POST /admin/social/preview` (gera post sem publicar).

#### Limites do Free Tier
- **1.500 tweets/mês** (criação) — suficiente para ~50/dia.
- **50 requests/15min** (leitura de métricas).
- Upload de mídia **ilimitado** via API v1.1.
- Se precisar escalar: Basic Tier a $100/mês → 3.000 tweets/mês + App-only auth.

#### Variáveis de Ambiente

```bash
TWITTER_ENABLED=true
TWITTER_API_KEY=<API Key do App>
TWITTER_API_SECRET=<API Key Secret do App>
TWITTER_ACCESS_TOKEN=<Access Token da conta @Parlamentaria>
TWITTER_ACCESS_TOKEN_SECRET=<Access Token Secret>
```

---

### 17.2 Facebook

#### Pré-requisitos
- Conta pessoal do Facebook (admin) vinculada à **Página** do projeto.
- Página do Facebook criada (ex: "Parlamentaria — Democracia Participativa").

#### Passo a Passo

1. **Criar Facebook App**
   - Acesse [developers.facebook.com](https://developers.facebook.com/) e clique em **My Apps → Create App**.
   - Selecione **Business** como tipo de app.
   - Dê um nome (ex: `Parlamentaria Social`) e associe a uma Business Account (ou crie uma).

2. **Adicionar o produto "Facebook Login for Business"**
   - No dashboard do app, em **Add Products**, adicione **Facebook Login**.
   - Configure o redirect URI (ex: `https://parlamentaria.app/auth/facebook/callback`).

3. **Obter permissões necessárias**
   - Na seção **App Review → Permissions and Features**, solicite:
     - `pages_manage_posts` — postar na página.
     - `pages_read_engagement` — ler métricas de engajamento.
   - **Importante**: essas permissões requerem aprovação da Meta. Submeta o pedido com descrição clara do uso (publicação automatizada de dados legislativos).
   - Enquanto a aprovação não sai, use **Test Users** (em Roles → Test Users) para desenvolvimento.

4. **Gerar Page Access Token de longa duração**
   - No [Graph API Explorer](https://developers.facebook.com/tools/explorer/):
     - Selecione o app criado.
     - Em **User or Page**, selecione a Página.
     - Gere um **User Token** com permissões `pages_manage_posts` e `pages_read_engagement`.
   - Converta para **Long-Lived Token** (60 dias):
     ```bash
     curl -G "https://graph.facebook.com/v21.0/oauth/access_token" \
       -d "grant_type=fb_exchange_token" \
       -d "client_id=<APP_ID>" \
       -d "client_secret=<APP_SECRET>" \
       -d "fb_exchange_token=<SHORT_LIVED_TOKEN>"
     ```
   - Converta para **Page Token permanente** (nunca expira):
     ```bash
     curl -G "https://graph.facebook.com/v21.0/me/accounts" \
       -d "access_token=<LONG_LIVED_USER_TOKEN>"
     ```
     O `access_token` retornado para a página é **permanente** (não expira enquanto as permissões forem válidas).
   - Copie o valor → variável `FACEBOOK_PAGE_ACCESS_TOKEN`.

5. **Obter Page ID**
   - No mesmo resultado do passo anterior, copie o campo `id` da página.
   - Ou acesse a página, vá em **Sobre → Transparência da Página** → o ID numérico está na URL.
   - → variável `FACEBOOK_PAGE_ID`.

#### Limites
- **200 chamadas/hora/usuário** — mais que suficiente.
- Posts na página não possuem limite diário explícito.

#### Variáveis de Ambiente

```bash
FACEBOOK_ENABLED=true
FACEBOOK_PAGE_ID=<ID numérico da Página>
FACEBOOK_PAGE_ACCESS_TOKEN=<Page Token permanente>
```

---

### 17.3 Instagram

#### Pré-requisitos
- **Conta Instagram Business** (não pessoal) — converter em Configurações → Conta → Mudar para conta profissional.
- **Facebook Page** vinculada à conta Instagram (obrigatório pela Meta).
- **Facebook App** já criado (mesma app da Seção 17.2).
- **URL pública** para servir imagens — Instagram **não aceita upload direto**; a imagem deve estar acessível via HTTPS.

#### Passo a Passo

1. **Vincular Instagram à Facebook Page**
   - Na Facebook Page, vá em **Configurações → Instagram** e conecte a conta Instagram Business.

2. **Adicionar permissões ao Facebook App**
   - No app criado na Seção 17.2, solicite permissões adicionais:
     - `instagram_basic` — acesso básico ao perfil.
     - `instagram_content_publish` — publicar conteúdo.
   - Estas permissões **também requerem App Review** da Meta.

3. **Obter Instagram User ID**
   - Com o Page Token obtido na Seção 17.2, consulte:
     ```bash
     curl -G "https://graph.facebook.com/v21.0/<PAGE_ID>" \
       -d "fields=instagram_business_account" \
       -d "access_token=<PAGE_TOKEN>"
     ```
   - O campo `instagram_business_account.id` é o → variável `INSTAGRAM_USER_ID`.

4. **Reutilizar o Page Access Token**
   - O mesmo token permanente gerado na Seção 17.2 funciona para Instagram.
   - → variável `INSTAGRAM_ACCESS_TOKEN` (mesmo valor de `FACEBOOK_PAGE_ACCESS_TOKEN`).

5. **Configurar URL pública para imagens**
   - O `InstagramPublisher` usa Container-based Publishing (2 chamadas):
     1. `POST /{ig-user-id}/media` com `image_url` + `caption` → cria container.
     2. `POST /{ig-user-id}/media_publish` → publica o container.
   - A `image_url` deve ser HTTPS e acessível publicamente. Opções:
     - Endpoint estático do FastAPI servindo as imagens geradas (ex: `https://parlamentaria.app/images/xxx.png`).
     - Pre-signed URL de storage (S3, GCS).
   - Configure `SOCIAL_IMAGES_PUBLIC_URL` para o base URL público.

#### Limites
- **25 publicações por dia** (Container Publishing API).
- Apenas imagens e carrosséis — sem posts só-texto.

#### Variáveis de Ambiente

```bash
INSTAGRAM_ENABLED=true
INSTAGRAM_USER_ID=<Instagram Business Account ID>
INSTAGRAM_ACCESS_TOKEN=<mesmo Page Token permanente do Facebook>
SOCIAL_IMAGES_PUBLIC_URL=https://parlamentaria.app/images
```

---

### 17.4 LinkedIn

#### Pré-requisitos
- **LinkedIn Page** (Organization) do Parlamentaria — criada por um perfil pessoal que será admin.
- Conta pessoal com permissão de admin na Page.

#### Passo a Passo

1. **Criar LinkedIn Page (Organization)**
   - Acesse [linkedin.com/company/setup](https://www.linkedin.com/company/setup/new/) e crie a página como **Organização Sem Fins Lucrativos** ou **Empresa**.
   - Nome: "Parlamentaria — Democracia Participativa".

2. **Criar App no LinkedIn Developer Portal**
   - Acesse [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps) → **Create App**.
   - Vincule a app à LinkedIn Page criada.
   - Url do app: `https://parlamentaria.app`.

3. **Solicitar produtos de API**
   - Na aba **Products**, solicite:
     - **Share on LinkedIn** — permite postar como Organization.
     - **Marketing Developer Platform** — acesso completo à API de posts organizacionais.
   - **Atenção**: o Marketing Developer Platform **requer aprovação manual** do LinkedIn.
     O processo pode levar dias/semanas. Submeta cedo (durante a Fase 1 do projeto).

4. **Configurar OAuth 2.0**
   - Na aba **Auth**, anote:
     - `Client ID` → será usado no fluxo OAuth.
     - `Client Secret` → será usado no fluxo OAuth.
   - Em **OAuth 2.0 Scopes**, garanta que `w_organization_social` está disponível (vem com o produto Marketing Developer Platform).

5. **Obter Access Token (OAuth 2.0 3-legged)**
   - O LinkedIn exige fluxo OAuth 2.0 com interação do usuário (consent screen) para obter o token inicial.
   - Fluxo simplificado para obtenção única:
     ```
     1. Abra no navegador:
        https://www.linkedin.com/oauth/v2/authorization?response_type=code
          &client_id=<CLIENT_ID>
          &redirect_uri=https://parlamentaria.app/auth/linkedin/callback
          &scope=w_organization_social%20r_organization_social

     2. Autorize o app com a conta admin da Page.

     3. Copie o `code` da URL de callback.

     4. Troque por access token:
        curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
          -d "grant_type=authorization_code" \
          -d "code=<CODE>" \
          -d "client_id=<CLIENT_ID>" \
          -d "client_secret=<CLIENT_SECRET>" \
          -d "redirect_uri=https://parlamentaria.app/auth/linkedin/callback"
     ```
   - O token retornado dura **60 dias**. O `refresh_token` (se disponível com o produto aprovado) permite renovação automática.
   - → variável `LINKEDIN_ACCESS_TOKEN`.

6. **Obter Organization ID**
   - Na URL da LinkedIn Page, o slug é o nome da organização. Para obter o ID numérico:
     ```bash
     curl -G "https://api.linkedin.com/v2/organizations" \
       -d "q=vanityName" \
       -d "vanityName=parlamentaria" \
       -H "Authorization: Bearer <ACCESS_TOKEN>"
     ```
   - Ou consulte na aba **Admin** da Page → URL contém o ID.
   - → variável `LINKEDIN_ORGANIZATION_ID`.

#### Limites
- **100 posts/dia** por Organization — amplo.
- Rate limit geral: 100 requests/dia por app para certas APIs de leitura.

#### Variáveis de Ambiente

```bash
LINKEDIN_ENABLED=true
LINKEDIN_ORGANIZATION_ID=<ID numérico da Organization>
LINKEDIN_ACCESS_TOKEN=<OAuth 2.0 Access Token>
```

**Nota sobre renovação**: o token expira em 60 dias. Implementar renovação automática
via `refresh_token` ou re-autenticação periódica manual. O `LinkedInPublisher` deve
tratar `401 Unauthorized` e logar alerta para renovação.

---

### 17.5 Discord

#### Pré-requisitos
- Conta Discord (gratuita).

#### Passo a Passo

1. **Criar servidor Discord**
   - No Discord, clique em **+** (Adicionar um servidor) → **Criar o meu**.
   - Nome: "Parlamentaria — Democracia Participativa".
   - Personalize com ícone e descrição do projeto.

2. **Criar canais temáticos**
   - Crie os canais de texto recomendados:
     - `#votações` — comparativos e votações relevantes.
     - `#resumo-semanal` — resumo semanal automático.
     - `#educativo` — posts explicativos de proposições.
     - `#geral` — destaques e alertas gerais.

3. **Criar Webhooks (um por canal)**
   - Para cada canal: clique com botão direito no canal → **Editar Canal** → **Integrações** → **Webhooks** → **Novo Webhook**.
   - Dê um nome ao webhook (ex: "Parlamentaria Bot").
   - Clique em **Copiar URL do Webhook** — este é o valor da variável de ambiente.
   - Repita para cada canal diferente.

4. **Configurar variáveis por canal**
   - O sistema suporta 4 webhooks independentes (um por tipo de conteúdo):
     - `DISCORD_WEBHOOK_URL_VOTACAO` — canal `#votações`
     - `DISCORD_WEBHOOK_URL_RESUMO` — canal `#resumo-semanal`
     - `DISCORD_WEBHOOK_URL_EDUCATIVO` — canal `#educativo`
     - `DISCORD_WEBHOOK_URL_GERAL` — canal `#geral`
   - Se quiser tudo no mesmo canal, use a mesma URL em todas as variáveis.

5. **Configurar link de convite permanente**
   - Vá em **Configurações do Servidor → Convites** → crie um link que nunca expira.
   - Divulgue o link nos posts de outras redes sociais como CTA.

#### Limites
- **30 mensagens/minuto** por webhook — mais que suficiente.
- Sem limite de embeds por mensagem (até 10 embeds por request).
- **Sem autenticação OAuth** — cada webhook é apenas uma URL secreta.

#### Variáveis de Ambiente

```bash
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL_VOTACAO=https://discord.com/api/webhooks/<id>/<token>
DISCORD_WEBHOOK_URL_RESUMO=https://discord.com/api/webhooks/<id>/<token>
DISCORD_WEBHOOK_URL_EDUCATIVO=https://discord.com/api/webhooks/<id>/<token>
DISCORD_WEBHOOK_URL_GERAL=https://discord.com/api/webhooks/<id>/<token>
```

**Segurança**: URLs de webhook do Discord são **secretas** — quem tem a URL pode postar
no canal. Nunca exponha em código público ou logs.

---

### 17.6 Reddit

#### Pré-requisitos
- Conta Reddit dedicada ao projeto (ex: `u/ParlamentariaBot`).
- A conta precisa de email verificado.

#### Passo a Passo

1. **Criar conta Reddit**
   - Crie a conta em [reddit.com/register](https://www.reddit.com/register).
   - Use um email dedicado do projeto e verifique-o.
   - **Nota sobre karma**: contas novas têm restrições de rate limit. Participe organicamente
     em alguns subreddits nos primeiros dias para acumular karma mínimo (~10 comment karma).

2. **Registrar Reddit App (Script)**
   - Com a conta logada, acesse [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
   - Clique em **"create another app..."** (no final da página).
   - Preencha:
     - **Name**: `parlamentaria-social`
     - **App type**: selecione **script** (para uso server-side autenticado como a própria conta).
     - **Description**: _"Automated publishing of Brazilian legislative transparency data."_
     - **About URL**: `https://parlamentaria.app`
     - **Redirect URI**: `http://localhost:8080` (obrigatório, mas não usado em apps tipo script).
   - Clique em **Create app**.
   - Anote:
     - O ID logo abaixo do nome do app (string alfanumérica) → variável `REDDIT_CLIENT_ID`.
     - O campo **secret** → variável `REDDIT_CLIENT_SECRET`.

3. **Criar subreddit r/parlamentaria**
   - Acesse [reddit.com/subreddits/create](https://www.reddit.com/subreddits/create).
   - Nome: `parlamentaria` (se disponível).
   - Tipo: **Public**.
   - Configure:
     - **Descrição**: _"Parlamentaria — Democracia participativa. Votos populares, comparativos legislativos e transparência."_
     - **Sidebar**: informações sobre o projeto, link para o bot Telegram e o site.
     - **Regras**: crie regras básicas (respeito, sem spam, sem discurso de ódio).
   - **Flairs de post** recomendados:
     - `📊 Comparativo` — posts de comparação popular vs Câmara.
     - `🗳️ Votação` — resultados de votação popular.
     - `📚 Explicativo` — posts educativos sobre proposições.
     - `📈 Resumo Semanal` — resumos periódicos.
     - `💬 Discussão` — posts gerados pela comunidade.
   - A conta `u/ParlamentariaBot` será automaticamente moderadora do sub.

4. **Configurar PRAW**
   - O `RedditPublisher` usa PRAW (síncrono) — roda em thread separada dentro do Celery worker.
   - As credenciais são: Client ID, Client Secret, username e password da conta Reddit.
   - O user agent deve seguir o formato recomendado: `parlamentaria:v1.0 (by u/ParlamentariaBot)`.

#### Limites
- **Contas novas**: ~1 post a cada 10 min (melhora com karma).
- **Contas com karma**: sem limite prático relevante para o volume esperado.
- **API rate limit**: 60 requests/minuto (OAuth2).
- **Imagens**: upload direto suportado via `subreddit.submit_image()`.

#### Variáveis de Ambiente

```bash
REDDIT_ENABLED=true
REDDIT_CLIENT_ID=<ID do App script>
REDDIT_CLIENT_SECRET=<Secret do App>
REDDIT_USERNAME=ParlamentariaBot
REDDIT_PASSWORD=<senha da conta Reddit>
REDDIT_SUBREDDIT=parlamentaria
```

**Segurança**: a senha da conta Reddit é armazenada em texto nas variáveis de ambiente.
Use secrets manager em produção (Docker secrets, Vault, etc.). Nunca commite no repositório.

---

### 17.7 Checklist Geral de Configuração

Tabela resumo para verificar se tudo está configurado antes de ativar cada rede:

| Rede       | Conta Criada | App/Webhook | Permissões Aprovadas | Tokens Gerados | `.env` Preenchido | Teste OK |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|
| Twitter/X  | ☐ | ☐ | ☐ (Read+Write) | ☐ | ☐ | ☐ |
| Facebook   | ☐ | ☐ | ☐ (App Review)  | ☐ | ☐ | ☐ |
| Instagram  | ☐ | ☐ | ☐ (App Review)  | ☐ | ☐ | ☐ |
| LinkedIn   | ☐ | ☐ | ☐ (Marketing Dev)| ☐ | ☐ | ☐ |
| Discord    | ☐ | ☐ | N/A              | N/A | ☐ | ☐ |
| Reddit     | ☐ | ☐ | N/A              | ☐ | ☐ | ☐ |

**Ordem recomendada de setup** (por complexidade):
1. **Discord** — pronto em 5 minutos, sem aprovação.
2. **Twitter/X** — Developer Account rápida, Free Tier imediato.
3. **Reddit** — App script simples, mas conta nova tem rate limits iniciais.
4. **Facebook** — App Review pode demorar dias/semanas.
5. **Instagram** — depende do Facebook App aprovado + URL pública para imagens.
6. **LinkedIn** — Marketing Developer Platform requer aprovação manual (mais demorado).

**Dica**: submeta as solicitações de App Review (Facebook, Instagram, LinkedIn) **na Fase 1**
do desenvolvimento, para que estejam aprovadas quando os publishers estiverem prontos na Fase 4.
