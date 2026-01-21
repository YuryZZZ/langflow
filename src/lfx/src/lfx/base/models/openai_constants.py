from .model_metadata import create_model_metadata

# User-approved OpenAI models ONLY
OPENAI_MODELS_DETAILED = [
    create_model_metadata(provider="OpenAI", name="gpt-5.2", icon="OpenAI", tool_calling=True),
    create_model_metadata(provider="OpenAI", name="gpt-5.2-chat-latest", icon="OpenAI", tool_calling=True),
    create_model_metadata(provider="OpenAI", name="gpt-5.1", icon="OpenAI", tool_calling=True),
]

OPENAI_CHAT_MODEL_NAMES = [
    metadata["name"]
    for metadata in OPENAI_MODELS_DETAILED
    if not metadata.get("not_supported", False)
    and not metadata.get("reasoning", False)
    and not metadata.get("search", False)
]

OPENAI_REASONING_MODEL_NAMES = [
    metadata["name"]
    for metadata in OPENAI_MODELS_DETAILED
    if metadata.get("reasoning", False) and not metadata.get("not_supported", False)
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

# Embedding models as detailed metadata
OPENAI_EMBEDDING_MODELS_DETAILED = [
    create_model_metadata(
        provider="OpenAI",
        name=name,
        icon="OpenAI",
        model_type="embeddings",
    )
    for name in OPENAI_EMBEDDING_MODEL_NAMES
]

# Backwards compatibility
MODEL_NAMES = OPENAI_CHAT_MODEL_NAMES
OPENAI_MODEL_NAMES = OPENAI_CHAT_MODEL_NAMES
