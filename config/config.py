"""
LLM configuration and factory functions.

Centralizes model settings so all graphs use consistent configuration.
"""

from langchain_openai import ChatOpenAI

from config.secret_keys import OPENAI_API_KEY

MODEL_NAME = "gpt-4.1-mini-2025-04-14"
MODEL_TEMPERATURE = 0.3  # Low temperature for deterministic tool calling


def get_llm(
    temperature: float = MODEL_TEMPERATURE,
    model_name: str = MODEL_NAME,
) -> ChatOpenAI:
    """Create a ChatOpenAI instance with project defaults.

    Args:
        temperature: Sampling temperature. Lower = more deterministic.
        model_name: OpenAI model identifier.

    Returns:
        Configured ChatOpenAI instance with streaming enabled.
    """
    return ChatOpenAI(
        model=model_name,
        openai_api_key=OPENAI_API_KEY,
        temperature=temperature,
        streaming=True,
    )
