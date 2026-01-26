"""
UiPath OpenAI Agents SDK.

NOTE: This module uses lazy imports via __getattr__ to avoid loading heavy
dependencies (openai SDK) at import time. This significantly improves CLI
startup performance.

Do NOT add eager imports like:
    from .chat import UiPathChatOpenAI  # BAD - loads openai SDK immediately

Instead, all exports are loaded on-demand when first accessed.
"""


def __getattr__(name):
    if name == "UiPathChatOpenAI":
        from .chat import UiPathChatOpenAI

        return UiPathChatOpenAI
    if name == "register_middleware":
        from .middlewares import register_middleware

        return register_middleware
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "0.1.0"
__all__ = ["register_middleware", "UiPathChatOpenAI"]
