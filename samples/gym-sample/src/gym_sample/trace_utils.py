"""OpenTelemetry trace collection utilities for agent evaluation."""

import json
from collections.abc import Sequence
from typing import List

from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)


class InMemorySpanExporter(SpanExporter):
    """An OpenTelemetry span exporter that stores spans in memory for testing.

    Normalizes LlamaIndex-specific formats (unwraps kwargs) to keep evaluators
    framework-agnostic.
    """

    def __init__(self):
        self.spans: List[ReadableSpan] = []
        self.is_shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self.is_shutdown:
            return SpanExportResult.FAILURE

        # Normalize spans before storing
        for span in spans:
            self._normalize_and_store(span)

        return SpanExportResult.SUCCESS

    def _normalize_and_store(self, span: ReadableSpan) -> None:
        """Normalize span attributes and store."""
        if span.attributes and "input.value" in span.attributes:
            # Unwrap kwargs wrapper
            attrs = dict(span.attributes)
            input_val = attrs["input.value"]

            try:
                parsed = (
                    json.loads(input_val) if isinstance(input_val, str) else input_val
                )
                # Unwrap {"kwargs": {...}} wrapper (LlamaIndex format)
                if isinstance(parsed, dict) and "kwargs" in parsed and len(parsed) == 1:
                    parsed = parsed["kwargs"]
                attrs["input.value"] = json.dumps(parsed)
                span._attributes = attrs  # type: ignore
            except (json.JSONDecodeError, ValueError):
                pass  # Leave as-is if parsing fails

        self.spans.append(span)

    def get_exported_spans(self) -> List[ReadableSpan]:
        return self.spans

    def clear_exported_spans(self) -> None:
        self.spans = []

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return not self.is_shutdown

    def shutdown(self) -> None:
        self.is_shutdown = True


def setup_tracer() -> tuple[InMemorySpanExporter, TracerProvider]:
    """Set up OpenTelemetry tracing with LlamaIndex instrumentation.

    Returns:
        InMemorySpanExporter: Exporter that normalizes spans (unwraps kwargs).
        TracerProvider: The configured tracer provider.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Initialize LlamaIndex instrumentation (this creates the spans!)
    LlamaIndexInstrumentor().instrument()

    return exporter, provider
