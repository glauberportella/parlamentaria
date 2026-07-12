"""ParlamentarAgent — Root agent (Coordinator/Dispatcher pattern).

This is the main entry point for the ADK multi-agent system.
It receives all messages from voters and delegates to specialized
sub-agents based on the conversation context.

Follows Google ADK conventions:
- Exports `root_agent` variable (required by ADK)
- Uses LlmAgent with sub_agents for Coordinator pattern
- LLM-driven delegation via transfer_to_agent()
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import ROOT_AGENT_INSTRUCTION
from agents.parlamentar.sub_agents.proposicao_agent import proposicao_agent
from agents.parlamentar.sub_agents.votacao_agent import votacao_agent
from agents.parlamentar.sub_agents.deputado_agent import deputado_agent
from agents.parlamentar.sub_agents.eleitor_agent import eleitor_agent
from agents.parlamentar.sub_agents.publicacao_agent import publicacao_agent
from agents.parlamentar.tools.camara_tools import buscar_eventos_pauta, consultar_agenda_votacoes
from agents.parlamentar.extensions import get_premium_sub_agents

root_agent = LlmAgent(
    name="ParlamentarAgent",
    description="Parlamentar de IA — assistente que conecta eleitores às decisões legislativas.",
    model=settings.agent_model,
    instruction=ROOT_AGENT_INSTRUCTION,
    sub_agents=[
        proposicao_agent,
        votacao_agent,
        deputado_agent,
        eleitor_agent,
        publicacao_agent,
        *get_premium_sub_agents(),
    ],
    # Root agent also has direct tools for agenda/events
    tools=[buscar_eventos_pauta, consultar_agenda_votacoes],
    output_key="last_response",
)
