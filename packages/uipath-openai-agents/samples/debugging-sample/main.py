"""Simple agent with tools for demonstrating breakpoint debugging."""

import dotenv
from agents import Agent, function_tool

dotenv.load_dotenv()


@function_tool
def calculate_sum(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    result = a + b
    print(f"Calculating: {a} + {b} = {result}")
    return result


@function_tool
def calculate_product(a: int, b: int) -> int:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Product of a and b
    """
    result = a * b
    print(f"Calculating: {a} * {b} = {result}")
    return result


@function_tool
def get_weather(city: str) -> str:
    """Get weather information for a city.

    Args:
        city: Name of the city

    Returns:
        Weather description
    """
    # Simulated weather data
    weather_data = {
        "New York": "Sunny, 72°F",
        "London": "Cloudy, 15°C",
        "Tokyo": "Rainy, 20°C",
        "Paris": "Partly cloudy, 18°C",
    }

    result = weather_data.get(city, f"Weather data not available for {city}")
    print(f"Weather in {city}: {result}")
    return result


# Create the main agent with tools
main = Agent(
    name="MathWeatherAgent",
    model="gpt-4o-2024-11-20",  # Use specific version supported by UiPath LLM Gateway
    instructions="""You are a helpful assistant that can:
    1. Perform mathematical calculations (addition and multiplication)
    2. Provide weather information for cities

    When asked to perform calculations, use the calculate_sum and calculate_product tools.
    When asked about weather, use the get_weather tool.

    Always be friendly and explain what you're doing.""",
    tools=[calculate_sum, calculate_product, get_weather],
)
