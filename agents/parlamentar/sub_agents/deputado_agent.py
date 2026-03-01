"""DeputadoAgent — Sub-agent for deputy profile and transparency queries.

Handles searching deputies, viewing profiles, expenses, and voting records.
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import DEPUTADO_AGENT_INSTRUCTION
from agents.parlamentar.tools.camara_tools import (
    buscar_deputado,
    obter_perfil_deputado,
    obter_despesas_deputado,
    obter_votos_parlamentares,
)

deputado_agent = LlmAgent(
    name="DeputadoAgent",
    description=(
        "Especialista em deputados federais. "
        "Busca informações sobre deputados, seus perfis, despesas da cota "
        "parlamentar e como votaram. "
        "Use quando o eleitor perguntar sobre deputados, gastos parlamentares "
        "ou transparência."
    ),
    model=settings.agent_model,
    instruction=DEPUTADO_AGENT_INSTRUCTION,
    tools=[
        buscar_deputado,
        obter_perfil_deputado,
        obter_despesas_deputado,
        obter_votos_parlamentares,
    ],
)
