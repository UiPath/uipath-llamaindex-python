from enum import Enum


class OpenAIModel(Enum):
    GPT_4_1_2025_04_14 = "gpt-4.1-2025-04-14"
    GPT_4_1_MINI_2025_04_14 = "gpt-4.1-mini-2025-04-14"
    GPT_4_1_NANO_2025_04_14 = "gpt-4.1-nano-2025-04-14"
    GPT_4O_2024_05_13 = "gpt-4o-2024-05-13"
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"
    GPT_4O_2024_11_20 = "gpt-4o-2024-11-20"
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"
    O3_MINI_2025_01_31 = "o3-mini-2025-01-31"
    TEXT_DAVINCI_003 = "text-davinci-003"


class GeminiModel:
    """Supported Google Gemini model identifiers."""

    gemini_2_5_pro = "gemini-2.5-pro"
    gemini_2_5_flash = "gemini-2.5-flash"
    gemini_2_0_flash_001 = "gemini-2.0-flash-001"


class BedrockModel:
    """Supported AWS Bedrock model identifiers."""

    # Claude 3.7 models
    anthropic_claude_3_7_sonnet = "anthropic.claude-3-7-sonnet-20250219-v1:0"

    # Claude 4 models
    anthropic_claude_sonnet_4 = "anthropic.claude-sonnet-4-20250514-v1:0"
    anthropic_claude_sonnet_4_5 = "anthropic.claude-sonnet-4-5-20250929-v1:0"
    anthropic_claude_haiku_4_5 = "anthropic.claude-haiku-4-5-20251001-v1:0"
