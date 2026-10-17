"""Shared chat-model configuration for generation and RAG."""

import os
from importlib import import_module


# provider: (integration module, client class, key variable, pip package)
PROVIDERS = {
    "mistral": ("langchain_mistralai", "ChatMistralAI", "MISTRAL_API_KEY", "langchain-mistralai"),
    "gemini": ("langchain_google_genai", "ChatGoogleGenerativeAI", "GOOGLE_API_KEY", "langchain-google-genai"),
    "groq": ("langchain_groq", "ChatGroq", "GROQ_API_KEY", "langchain-groq"),
    "openai": ("langchain_openai", "ChatOpenAI", "OPENAI_API_KEY", "langchain-openai"),
    "anthropic": ("langchain_anthropic", "ChatAnthropic", "ANTHROPIC_API_KEY", "langchain-anthropic"),
    "openai_compatible": ("langchain_openai", "ChatOpenAI", "LLM_API_KEY", "langchain-openai"),
}


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.lower().startswith("your_"):
        raise ValueError(f"Set {name} in .env, then restart the app.")
    return value


def get_llm(temperature: float = 0.3):
    """Create only the selected provider's client; never fall back to another."""
    provider = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Choose: {', '.join(PROVIDERS)}."
        )

    module_name, class_name, key_name, package = PROVIDERS[provider]
    model = os.getenv("LLM_MODEL", "").strip()
    if not model:
        # Preserve existing Mistral-only .env files.
        model = "mistral-small-latest" if provider == "mistral" else _required("LLM_MODEL")

    kwargs = {"model": model, "temperature": temperature}
    key = _required(key_name)
    kwargs["mistral_api_key" if provider == "mistral" else "api_key"] = key
    if provider == "gemini":
        # Use the Gemini Developer API, regardless of ambient Vertex settings.
        kwargs["vertexai"] = False
    if provider == "openai_compatible":
        kwargs["base_url"] = _required("LLM_BASE_URL")

    try:
        client_class = getattr(import_module(module_name), class_name)
    except ImportError as exc:
        raise ImportError(
            f"The {provider} integration is unavailable. Install it with: "
            f"python -m pip install {package}"
        ) from exc
    return client_class(**kwargs)
