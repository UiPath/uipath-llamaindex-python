"""UiPath OpenAI Agents SDK."""

from .chat import UiPathChatOpenAI
from .middlewares import register_middleware

__version__ = "0.1.0"
__all__ = ["register_middleware", "UiPathChatOpenAI"]
