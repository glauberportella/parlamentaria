"""VotacaoAgent — Sub-agent for popular voting operations.

Handles voter registration of votes on propositions, result display,
and vote history management.
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import VOTACAO_AGENT_INSTRUCTION
from agents.parlamentar.tools.camara_tools import (
    buscar_votacoes_recentes,
    obter_votos_parlamentares,
)
from agents.parlamentar.tools.votacao_tools import (
    registrar_voto,
    obter_resultado_votacao,
    consultar_meu_voto,
    historico_votos_eleitor,
)

votacao_agent = LlmAgent(
    name="VotacaoAgent",
    description=(
        "Especialista em votação popular. "
        "Registra votos de eleitores sobre proposições (SIM, NÃO, ABSTENÇÃO), "
        "mostra resultados consolidados e histórico de votos. "
        "Use quando o eleitor quiser votar, ver resultados ou saber como votou."
    ),
    model=settings.agent_model,
    instruction=VOTACAO_AGENT_INSTRUCTION,
    tools=[
        registrar_voto,
        obter_resultado_votacao,
        consultar_meu_voto,
        historico_votos_eleitor,
        buscar_votacoes_recentes,
        obter_votos_parlamentares,
    ],
)
