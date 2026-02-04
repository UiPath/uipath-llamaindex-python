"""Tests for context type detection and handling."""

from typing import Any

import pytest
from pydantic import BaseModel

from uipath_openai_agents.runtime.context import (
    parse_input_to_context,
)


class UserContext(BaseModel):
    """Context model with user info."""

    user_id: str
    tier: str = "standard"


class OptionalContext(BaseModel):
    """Context model with all optional fields."""

    session_id: str | None = None
    metadata: dict[str, Any] | None = None


class TestParseInputToContext:
    """Tests for parse_input_to_context function."""

    def test_parse_context_excludes_messages(self) -> None:
        """Test that 'messages' field is excluded from context."""
        input_dict = {
            "messages": "Hello world",
            "user_id": "user_123",
            "tier": "premium",
        }
        context = parse_input_to_context(input_dict, UserContext)
        assert isinstance(context, UserContext)

        assert context.user_id == "user_123"
        assert context.tier == "premium"
        assert not hasattr(context, "messages")

    def test_parse_context_with_defaults(self) -> None:
        """Test parsing with default values."""
        input_dict = {"messages": "Hello", "user_id": "user_456"}
        context = parse_input_to_context(input_dict, UserContext)
        assert isinstance(context, UserContext)

        assert context.user_id == "user_456"
        assert context.tier == "standard"  # default value

    def test_parse_all_optional_context(self) -> None:
        """Test parsing context with all optional fields."""
        input_dict = {"messages": "Test message"}
        context = parse_input_to_context(input_dict, OptionalContext)
        assert isinstance(context, OptionalContext)

        assert context.session_id is None
        assert context.metadata is None

    def test_parse_empty_input(self):
        """Test parsing empty input with required fields fails."""
        with pytest.raises(ValueError):
            parse_input_to_context({}, UserContext)

    def test_parse_none_input(self):
        """Test parsing None input with required fields fails."""
        with pytest.raises(ValueError):
            parse_input_to_context(None, UserContext)

    def test_parse_messages_only_input(self):
        """Test that messages-only input fails when context has required fields."""
        with pytest.raises(ValueError):
            parse_input_to_context({"messages": "Hello"}, UserContext)


class TestIntegration:
    """Integration tests for context handling."""

    def test_full_flow_with_context(self) -> None:
        """Test the full flow: messages separate from context."""
        input_dict = {
            "messages": "What are my features?",
            "user_id": "user_789",
            "tier": "enterprise",
        }

        # Messages should be extracted separately (done by runtime)
        messages = input_dict.get("messages", "")
        assert messages == "What are my features?"

        # Context should exclude messages
        context = parse_input_to_context(input_dict, UserContext)
        assert isinstance(context, UserContext)
        assert context.user_id == "user_789"
        assert context.tier == "enterprise"
