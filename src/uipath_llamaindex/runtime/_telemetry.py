"""OpenTelemetry SpanProcessor for normalizing LlamaIndex tool call attributes.

LlamaIndex wraps tool arguments in {"kwargs": {...}} which differs from other
frameworks like LangChain that use flat {"arg": value} format. This processor
normalizes the format at the span level before exporters or dev terminal read it.
"""

import json
import logging
from typing import Any, Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

logger = logging.getLogger(__name__)


class ToolCallAttributeNormalizer(SpanProcessor):
    """Normalizes LlamaIndex tool call attributes to match other frameworks.

    Unwraps {"kwargs": {...}} to flat {...} format for consistency with LangChain.
    """

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """Called when span starts - no action needed."""
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """Normalize tool call attributes before span is consumed by exporters/terminal."""
        # Access internal mutable attributes (BoundedAttributes at runtime)
        # ReadableSpan._attributes is typed as Mapping but mutable in practice
        attrs = getattr(span, "_attributes", None)
        if not attrs:
            return

        try:
            if attrs.get("openinference.span.kind", None) == "TOOL":
                for key in ("input.value", "output.value"):
                    if key in attrs:
                        original = attrs[key]
                        normalized = self._normalize_attribute(key, original)

                        if normalized != original:
                            attrs[key] = normalized
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(
                                    f"Normalized {key} in span '{span.name}': "
                                    f"{str(original)[:50]}... → {str(normalized)[:50]}..."
                                )

        except Exception as e:
            logger.debug(
                f"Failed to normalize span '{getattr(span, 'name', 'unknown')}': {e}"
            )

    def _normalize_attribute(self, key: str, value: Any) -> str:
        """Unwrap LlamaIndex's kwargs wrapper if present."""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                pass
        if isinstance(value, dict):
            if key == "input.value":
                if "kwargs" in value:
                    value = json.dumps(value["kwargs"])
            elif key == "output.value":
                value = json.dumps(
                    {
                        "content": value.get("raw_output"),
                        "status": "success"
                        if not value.get("is_error", False)
                        else "error",
                        "tool_call_id": value.get("tool_call_id"),
                    }
                )
        return str(value)

    def shutdown(self) -> None:
        """Called on processor shutdown - no cleanup needed."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush - always succeeds (nothing to flush)."""
        return True
