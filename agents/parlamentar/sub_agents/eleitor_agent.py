"""EleitorAgent — Sub-agent for voter registration and profile management.

Handles voter sign-up, profile updates, interest themes, and notifications.
"""

from google.adk.agents import LlmAgent

from app.config import settings
from agents.parlamentar.prompts import ELEITOR_AGENT_INSTRUCTION
from agents.parlamentar.tools.db_tools import (
    consultar_perfil_eleitor,
    cadastrar_eleitor,
    atualizar_temas_interesse,
)
from agents.parlamentar.tools.notification_tools import verificar_notificacoes

eleitor_agent = LlmAgent(
    name="EleitorAgent",
    description=(
        "Responsável pelo cadastro e perfil do eleitor. "
        "Registra novos eleitores, atualiza dados pessoais e gerencia "
        "temas de interesse para notificações proativas. "
        "Use quando o eleitor quiser se cadastrar, atualizar perfil ou "
        "configurar notificações."
    ),
    model=settings.agent_model,
    instruction=ELEITOR_AGENT_INSTRUCTION,
    tools=[
        consultar_perfil_eleitor,
        cadastrar_eleitor,
        atualizar_temas_interesse,
        verificar_notificacoes,
    ],
)
