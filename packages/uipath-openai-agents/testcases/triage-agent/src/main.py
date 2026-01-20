"""
Integration testcase for the triage/routing pattern.
The triage agent receives a message and hands off to the appropriate
agent based on the language of the request.

"""

import dotenv
from agents import Agent

dotenv.load_dotenv()

# Define specialized agents for different languages
# Explicitly set model to gpt-4o-2024-11-20 (OpenAI Agents SDK normalizes gpt-4.1 automatically)
MODEL = "gpt-4o-2024-11-20"

french_agent = Agent(
    name="french_agent",
    instructions="You only speak French",
    model=MODEL,
)

spanish_agent = Agent(
    name="spanish_agent",
    instructions="You only speak Spanish",
    model=MODEL,
)

english_agent = Agent(
    name="english_agent",
    instructions="You only speak English",
    model=MODEL,
)

# Triage agent routes to appropriate language agent
# Entry point - messages come in as JSON and are handled directly by the agent
agent = Agent(
    name="triage_agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",
    handoffs=[french_agent, spanish_agent, english_agent],
    model=MODEL,
)
