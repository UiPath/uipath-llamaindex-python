"""Supported OpenAI model definitions for UiPath LLM Gateway."""


class OpenAIModels:
    """OpenAI model names supported by UiPath LLM Gateway.

    These are specific model versions required by UiPath.
    Generic names like "gpt-4o" are not supported - use specific versions.
    """

    # GPT-4o Models (recommended)
    gpt_4o_2024_11_20 = "gpt-4o-2024-11-20"
    gpt_4o_2024_08_06 = "gpt-4o-2024-08-06"
    gpt_4o_2024_05_13 = "gpt-4o-2024-05-13"
    gpt_4o_mini_2024_07_18 = "gpt-4o-mini-2024-07-18"

    # GPT-4.1 Models
    gpt_4_1_2025_04_14 = "gpt-4.1-2025-04-14"
    gpt_4_1_mini_2025_04_14 = "gpt-4.1-mini-2025-04-14"
    gpt_4_1_nano_2025_04_14 = "gpt-4.1-nano-2025-04-14"

    # GPT-4 Models
    gpt_4 = "gpt-4"
    gpt_4_32k = "gpt-4-32k"
    gpt_4_turbo_2024_04_09 = "gpt-4-turbo-2024-04-09"
    gpt_4_1106_preview = "gpt-4-1106-Preview"
    gpt_4_vision_preview = "gpt-4-vision-preview"

    # GPT-3.5 Models
    gpt_35_turbo = "gpt-35-turbo"
    gpt_35_turbo_0125 = "gpt-35-turbo-0125"
    gpt_35_turbo_1106 = "gpt-35-turbo-1106"
    gpt_35_turbo_16k = "gpt-35-turbo-16k"

    # GPT-5 Models
    gpt_5_2025_08_07 = "gpt-5-2025-08-07"
    gpt_5_chat_2025_08_07 = "gpt-5-chat-2025-08-07"
    gpt_5_mini_2025_08_07 = "gpt-5-mini-2025-08-07"
    gpt_5_nano_2025_08_07 = "gpt-5-nano-2025-08-07"
    gpt_5_1_2025_11_13 = "gpt-5.1-2025-11-13"
    gpt_5_2_2025_12_11 = "gpt-5.2-2025-12-11"

    # o3 Models
    o3_mini_2025_01_31 = "o3-mini-2025-01-31"

    # Other Models
    computer_use_preview_2025_03_11 = "computer-use-preview-2025-03-11"
    text_davinci_003 = "text-davinci-003"

    # Embedding Models
    text_embedding_3_large = "text-embedding-3-large"
    text_embedding_3_large_community_ecs = "text-embedding-3-large-community-ecs"
    text_embedding_ada_002 = "text-embedding-ada-002"

    # Model aliases - maps generic names to specific versions
    MODEL_ALIASES = {
        # Map gpt-4.1 variants to gpt-4o (most capable available model)
        "gpt-4.1": gpt_4o_2024_11_20,
        "gpt-4.1-mini": gpt_4o_mini_2024_07_18,
        "gpt-4.1-nano": gpt_4o_mini_2024_07_18,
        "gpt-4.1-2025-04-14": gpt_4o_2024_11_20,  # Map invalid model to valid one
        "gpt-4.1-mini-2025-04-14": gpt_4o_mini_2024_07_18,
        "gpt-4.1-nano-2025-04-14": gpt_4o_mini_2024_07_18,
        # Generic model mappings
        "gpt-4o": gpt_4o_2024_11_20,
        "gpt-4o-mini": gpt_4o_mini_2024_07_18,
        "gpt-5": gpt_5_2025_08_07,
        "gpt-5-mini": gpt_5_mini_2025_08_07,
        "gpt-5-nano": gpt_5_nano_2025_08_07,
        "gpt-5.1": gpt_5_1_2025_11_13,
        "gpt-5.2": gpt_5_2_2025_12_11,
        "o3-mini": o3_mini_2025_01_31,
    }

    @classmethod
    def normalize_model_name(cls, model_name: str) -> str:
        """Normalize a model name to UiPath-specific version."""
        return cls.MODEL_ALIASES.get(model_name, model_name)
