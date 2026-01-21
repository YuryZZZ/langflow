from .model_metadata import create_model_metadata

# User-approved Groq models ONLY
GROQ_MODELS_DETAILED = [
    create_model_metadata(
        provider="Groq", name="llama-3.3-70b-versatile", icon="Groq", tool_calling=True
    ),
    create_model_metadata(
        provider="Groq", name="llama-3.1-8b-instant", icon="Groq", tool_calling=True
    ),
    create_model_metadata(
        provider="Groq", name="moonshotai/kimi-k2-instruct-0905", icon="Groq", tool_calling=True
    ),
    create_model_metadata(
        provider="Groq", name="openai/gpt-oss-120b", icon="Groq", tool_calling=True
    ),
]

# Generate backwards-compatible lists from the metadata
GROQ_PRODUCTION_MODELS = [
    metadata["name"]
    for metadata in GROQ_MODELS_DETAILED
    if not metadata.get("preview", False)
    and not metadata.get("deprecated", False)
    and not metadata.get("not_supported", False)
]

GROQ_PREVIEW_MODELS = [metadata["name"] for metadata in GROQ_MODELS_DETAILED if metadata.get("preview", False)]

DEPRECATED_GROQ_MODELS = [metadata["name"] for metadata in GROQ_MODELS_DETAILED if metadata.get("deprecated", False)]

UNSUPPORTED_GROQ_MODELS = [
    metadata["name"] for metadata in GROQ_MODELS_DETAILED if metadata.get("not_supported", False)
]

TOOL_CALLING_UNSUPPORTED_GROQ_MODELS = [
    metadata["name"]
    for metadata in GROQ_MODELS_DETAILED
    if not metadata.get("tool_calling", False)
    and not metadata.get("not_supported", False)
    and not metadata.get("deprecated", False)
]

# Combined list of all current models for backward compatibility
GROQ_MODELS = GROQ_PRODUCTION_MODELS + GROQ_PREVIEW_MODELS

# For reverse compatibility
MODEL_NAMES = GROQ_MODELS
