"""Extension points for premium plugin registration.

This module is one of only TWO files in the core allowed to reference
the premium package (the other is plan_gate.py). It uses ImportError-safe
loading so the core runs perfectly standalone without premium installed.
"""

import structlog

logger = structlog.get_logger(__name__)


def load_premium_plugin(app) -> bool:
    """Try to load and register the premium plugin.

    The premium package is optional. If not installed, the core
    runs standalone with all free features.

    Args:
        app: FastAPI application instance.

    Returns:
        True if premium was loaded, False otherwise.
    """
    try:
        from premium.plugin import register_premium_plugin
        register_premium_plugin(app)
        logger.info("premium.plugin.loaded")
        return True
    except ImportError:
        logger.info("premium.plugin.not_installed", msg="Running in open-source mode")
        return False
