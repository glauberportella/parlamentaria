"""PublicacaoAgent — Sub-agent for comparative analysis and publication status.

Handles comparison between popular and parliamentary votes, provides
information about RSS feeds and webhook publication channels, and gives
voters access to their voting history with comparison results.
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import PUBLICACAO_AGENT_INSTRUCTION
from agents.parlamentar.tools.publicacao_tools import (
    obter_comparativo,
    status_publicacao,
    consultar_assinaturas_ativas,
    disparar_evento_publicacao,
    listar_comparativos_recentes,
    consultar_historico_votos,
)

publicacao_agent = LlmAgent(
    name="PublicacaoAgent",
    description=(
        "Especialista em comparativos e publicação de resultados. "
        "Compara como os eleitores votaram versus o resultado parlamentar real, "
        "mostrando índice de alinhamento. Também informa sobre RSS e Webhooks. "
        "Use quando o eleitor perguntar sobre resultados, comparativos, histórico "
        "de votos ou como parlamentares podem acompanhar a opinião popular."
    ),
    model=settings.agent_model,
    instruction=PUBLICACAO_AGENT_INSTRUCTION,
    tools=[
        obter_comparativo,
        status_publicacao,
        consultar_assinaturas_ativas,
        disparar_evento_publicacao,
        listar_comparativos_recentes,
        consultar_historico_votos,
    ],
)
