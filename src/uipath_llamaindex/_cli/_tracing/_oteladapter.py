import logging
from typing import Any, Dict

from opentelemetry.sdk.trace.export import (
    SpanExportResult,
)
from uipath.tracing import CommonSpanProcessor, LlmOpsHttpExporter

logger = logging.getLogger(__name__)


class LlamaIndexExporter(LlmOpsHttpExporter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._processor = CommonSpanProcessor()

    def _send_with_retries(
        self, url: str, payload: list[Dict[str, Any]], max_retries: int = 4
    ) -> SpanExportResult:
        processed_payload = [self._processor.process_span(span) for span in payload]
        return super()._send_with_retries(
            url=url,
            payload=processed_payload,
            max_retries=max_retries,
        )

