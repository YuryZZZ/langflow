from .model_metadata import create_model_metadata

# Unified model metadata - single source of truth
# Updated to approved models list 2026-01-17
OPENAI_MODELS_DETAILED = [
    # GPT-5 Series (Approved)
    create_model_metadata(provider="OpenAI", name="gpt-5.2", icon="OpenAI", tool_calling=True),
    create_model_metadata(provider="OpenAI", name="gpt-5.2-chat-latest", icon="OpenAI", tool_calling=True),
    create_model_metadata(provider="OpenAI", name="gpt-5.1", icon="OpenAI", tool_calling=True),
    # Legacy Models (kept for backwards compatibility)
    create_model_metadata(provider="OpenAI", name="gpt-4o-mini", icon="OpenAI", tool_calling=True, deprecated=True),
    create_model_metadata(provider="OpenAI", name="gpt-4o", icon="OpenAI", tool_calling=True, deprecated=True),
    create_model_metadata(provider="OpenAI", name="gpt-4-turbo", icon="OpenAI", tool_calling=True, deprecated=True),
    create_model_metadata(provider="OpenAI", name="gpt-4", icon="OpenAI", tool_calling=True, deprecated=True),
    create_model_metadata(provider="OpenAI", name="gpt-3.5-turbo", icon="OpenAI", tool_calling=True, deprecated=True),
    # Reasoning Models (legacy)
    create_model_metadata(provider="OpenAI", name="o1", icon="OpenAI", reasoning=True, deprecated=True),
]

OPENAI_MODEL_NAMES = [
    metadata["name"]
    for metadata in OPENAI_MODELS_DETAILED
    if not metadata.get("reasoning", False)
    and not metadata.get("search", False)
    and not metadata.get("not_supported", False)
    and not metadata.get("deprecated", False)
]

OPENAI_REASONING_MODEL_NAMES = [
    metadata["name"]
    for metadata in OPENAI_MODELS_DETAILED
    if metadata.get("reasoning", False) and not metadata.get("not_supported", False) and not metadata.get("deprecated", False)
]

OPENAI_SEARCH_MODEL_NAMES = [
    metadata["name"]
    for metadata in OPENAI_MODELS_DETAILED
    if metadata.get("search", False) and not metadata.get("not_supported", False)
]

NOT_SUPPORTED_MODELS = [metadata["name"] for metadata in OPENAI_MODELS_DETAILED if metadata.get("not_supported", False)]

OPENAI_EMBEDDING_MODEL_NAMES = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
]

# Backwards compatibility
MODEL_NAMES = OPENAI_MODEL_NAMES
