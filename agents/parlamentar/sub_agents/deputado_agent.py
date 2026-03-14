"""DeputadoAgent — Sub-agent for deputy profile, transparency and Raio-X queries.

Handles searching deputies, viewing profiles, expenses, voting records,
committees, parliamentary fronts, and generating comprehensive Raio-X reports.
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import DEPUTADO_AGENT_INSTRUCTION
from agents.parlamentar.tools.camara_tools import (
    buscar_deputado,
    obter_perfil_deputado,
    obter_despesas_deputado,
    obter_votos_parlamentares,
    obter_comissoes_deputado,
    obter_frentes_deputado,
    obter_presenca_deputado,
    obter_raio_x_deputado,
)

deputado_agent = LlmAgent(
    name="DeputadoAgent",
    description=(
        "Especialista em deputados federais. "
        "Busca informações sobre deputados, seus perfis, despesas da cota "
        "parlamentar, como votaram, comissões, frentes parlamentares e "
        "presença em eventos. Gera Raio-X completo do deputado. "
        "Use quando o eleitor perguntar sobre deputados, gastos parlamentares, "
        "transparência ou quiser saber se o deputado o representa bem."
    ),
    model=settings.agent_model,
    instruction=DEPUTADO_AGENT_INSTRUCTION,
    tools=[
        buscar_deputado,
        obter_perfil_deputado,
        obter_despesas_deputado,
        obter_votos_parlamentares,
        obter_comissoes_deputado,
        obter_frentes_deputado,
        obter_presenca_deputado,
        obter_raio_x_deputado,
    ],
)
