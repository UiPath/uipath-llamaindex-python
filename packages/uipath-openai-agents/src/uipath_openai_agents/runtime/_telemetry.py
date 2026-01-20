"""OpenInference tracing integration for OpenAI Agents."""

try:
    from opentelemetry import trace

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False


if TELEMETRY_AVAILABLE:

    def get_current_span_wrapper():
        """Wrapper to get the current span from OpenTelemetry.

        Returns:
            The current OpenTelemetry span if available, None otherwise
        """
        return trace.get_current_span()

else:

    def get_current_span_wrapper():
        """Stub function when OpenTelemetry is not available.

        Returns:
            None since telemetry dependencies are not available
        """
        return None


__all__ = ["get_current_span_wrapper"]
