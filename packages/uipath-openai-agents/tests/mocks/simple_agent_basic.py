"""Simple OpenAI agent for testing - basic configuration."""

from agents import Agent

# Simple agent without output type (uses default behavior)
agent = Agent(
    name="echo_agent",
    instructions="You are a helpful assistant. Respond to the user's message.",
)
