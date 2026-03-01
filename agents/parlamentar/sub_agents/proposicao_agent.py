"""ProposicaoAgent — Sub-agent for legislative proposition search and analysis.

Handles searching, explaining, and analyzing propositions from the
Câmara dos Deputados using both the live API and local database.
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import PROPOSICAO_AGENT_INSTRUCTION
from agents.parlamentar.tools.camara_tools import (
    buscar_proposicoes,
    obter_detalhes_proposicao,
    listar_tramitacoes_proposicao,
)
from agents.parlamentar.tools.db_tools import (
    consultar_proposicao_local,
    listar_proposicoes_local,
    obter_analise_ia,
)

proposicao_agent = LlmAgent(
    name="ProposicaoAgent",
    description=(
        "Especialista em proposições legislativas (PLs, PECs, MPVs). "
        "Busca, explica e analisa projetos de lei da Câmara dos Deputados. "
        "Use quando o eleitor perguntar sobre proposições, projetos de lei, "
        "PECs, medidas provisórias ou legislação em tramitação."
    ),
    model=settings.agent_model,
    instruction=PROPOSICAO_AGENT_INSTRUCTION,
    tools=[
        buscar_proposicoes,
        obter_detalhes_proposicao,
        listar_tramitacoes_proposicao,
        consultar_proposicao_local,
        listar_proposicoes_local,
        obter_analise_ia,
    ],
)
