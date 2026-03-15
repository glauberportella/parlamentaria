"""SocialMediaAgent — Autonomous agent for social media text generation.

This agent is NOT a sub-agent of ParlamentarAgent. It operates autonomously
via Celery tasks, generating optimized social media texts from structured data.
It does NOT interact with voters directly.
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import SOCIAL_MEDIA_AGENT_INSTRUCTION
from agents.parlamentar.tools.social_media_tools import (
    gerar_texto_post_social,
    listar_posts_recentes,
    obter_metricas_posts,
)

social_media_agent = LlmAgent(
    name="SocialMediaAgent",
    description=(
        "Redator de redes sociais. Gera textos otimizados por rede "
        "(Twitter, Facebook, Instagram, LinkedIn, Discord, Reddit) "
        "a partir de dados legislativos. Opera de forma autônoma via "
        "tasks agendadas, sem interação direta com eleitores."
    ),
    model=settings.agent_model,
    instruction=SOCIAL_MEDIA_AGENT_INSTRUCTION,
    tools=[
        gerar_texto_post_social,
        listar_posts_recentes,
        obter_metricas_posts,
    ],
)
