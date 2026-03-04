"""Runner integration module for Parlamentaria ADK agents.

Provides a managed Runner that handles:
- Session management (InMemory for dev, Database for prod)
- Running agent conversations with proper session lifecycle
- Extracting final response text from event streams
"""

from __future__ import annotations

from typing import AsyncGenerator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.genai.types import Content, Part

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)

# Application name used for all sessions
APP_NAME = "parlamentaria"

# Module-level session service (initialized lazily)
_session_service: InMemorySessionService | DatabaseSessionService | None = None
_runner: Runner | None = None


def get_session_service() -> InMemorySessionService | DatabaseSessionService:
    """Get or create the session service.

    Uses InMemorySessionService for development and DatabaseSessionService
    for production (when DATABASE_URL is configured).

    Returns:
        Configured session service instance.
    """
    global _session_service
    if _session_service is not None:
        return _session_service

    if settings.is_production:
        # Production: persistent sessions via database
        # ADK DatabaseSessionService uses create_async_engine internally,
        # so postgresql+asyncpg:// is the correct driver for PostgreSQL.
        _session_service = DatabaseSessionService(db_url=settings.database_url)
        logger.info("agent.session_service", type="database")
    else:
        # Development: in-memory sessions
        _session_service = InMemorySessionService()
        logger.info("agent.session_service", type="in_memory")

    return _session_service


def get_runner() -> Runner:
    """Get or create the ADK Runner.

    The Runner orchestrates agent execution, handling session management
    and event processing.

    Returns:
        Configured Runner instance.
    """
    global _runner
    if _runner is not None:
        return _runner

    from agents.parlamentar.agent import root_agent

    _runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=get_session_service(),
    )
    logger.info("agent.runner.created", app_name=APP_NAME, model=settings.agent_model)
    return _runner


async def run_agent(
    user_id: str,
    session_id: str,
    message: str,
) -> str:
    """Run the agent for a single user message and return the final response.

    This is the main entry point for channel adapters (Telegram, WhatsApp).
    Handles creating sessions if needed and extracting the response text.

    Args:
        user_id: Unique user identifier (e.g., Telegram chat_id).
        session_id: Session identifier (can be same as user_id for 1:1 chats).
        message: The user's text message.

    Returns:
        The agent's text response.
    """
    runner = get_runner()
    session_service = get_session_service()

    # Ensure session exists
    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={
                "user:chat_id": user_id,
            },
        )
        logger.info("agent.session.created", user_id=user_id, session_id=session_id)

    # Build the user message
    user_content = Content(
        role="user",
        parts=[Part(text=message)],
    )

    # Run the agent and collect the final response
    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                response_text = "".join(
                    part.text for part in event.content.parts if part.text
                )

    if not response_text:
        response_text = (
            "Desculpe, não consegui processar sua mensagem. "
            "Pode tentar novamente?"
        )

    logger.info(
        "agent.response",
        user_id=user_id,
        session_id=session_id,
        response_length=len(response_text),
    )
    return response_text


async def reset_session(user_id: str, session_id: str) -> bool:
    """Delete and recreate a user's session.

    Useful when the user wants to start a fresh conversation.

    Args:
        user_id: User identifier.
        session_id: Session identifier.

    Returns:
        True if session was reset successfully.
    """
    session_service = get_session_service()
    try:
        await session_service.delete_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        logger.info("agent.session.reset", user_id=user_id, session_id=session_id)
        return True
    except Exception as e:
        logger.warning("agent.session.reset_failed", user_id=user_id, error=str(e))
        return False
