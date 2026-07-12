"""Extension point for premium agents.

This module allows the premium plugin to inject additional sub-agents
and tools into the root agent. When premium is not installed, these
functions return empty lists — no impact on core functionality.
"""


def get_premium_sub_agents() -> list:
    """Load premium sub-agents if the premium package is installed.

    Returns:
        List of ADK LlmAgent instances from premium, or empty list.
    """
    try:
        from premium.agents.billing_agent import billing_agent
        return [billing_agent]
    except ImportError:
        return []


def get_premium_tools() -> list:
    """Load premium tools if the premium package is installed.

    Returns:
        List of FunctionTool instances from premium, or empty list.
    """
    tools = []
    try:
        from premium.agents.premium_tools import PREMIUM_TOOLS
        tools.extend(PREMIUM_TOOLS)
    except ImportError:
        pass
    try:
        from premium.agents.gated_tools import GATED_PREMIUM_TOOLS
        tools.extend(GATED_PREMIUM_TOOLS)
    except ImportError:
        pass
    return tools
