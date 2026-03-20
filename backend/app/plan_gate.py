"""Plan-based feature gating — works with or without premium plugin.

This module is one of only TWO files in the core allowed to reference
the premium package (the other is extensions.py). When premium is not
installed, all gates pass freely (open-source mode has no restrictions).
"""

from functools import wraps
from typing import Any, Callable

# Registry populated by the premium plugin (if installed)
_plan_checker: Callable | None = None


def set_plan_checker(checker_fn: Callable) -> None:
    """Called by premium plugin to register the plan verification function.

    Args:
        checker_fn: Async callable(args, kwargs, min_plan) -> bool
    """
    global _plan_checker
    _plan_checker = checker_fn


def require_plan(min_plan: str, fallback: dict[str, Any] | None = None) -> Callable:
    """Decorator that gates a function behind a minimum plan.

    If premium plugin is not installed, the function executes freely
    (open-source mode has no plan restrictions).

    Args:
        min_plan: Minimum plan required ("PREMIUM", "PRO", "ENTERPRISE", etc.)
        fallback: Value to return if plan check fails. If None, returns
                  a standard upgrade-required dict.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _plan_checker is None:
                # No premium plugin → all features available (open-source mode)
                return await fn(*args, **kwargs)

            # Premium installed → check plan
            has_access = await _plan_checker(args, kwargs, min_plan)
            if not has_access:
                return fallback or {
                    "status": "upgrade_required",
                    "required_plan": min_plan,
                    "message": f"Esta funcionalidade requer o plano {min_plan}.",
                }
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
