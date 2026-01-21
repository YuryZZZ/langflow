from .model_metadata import create_model_metadata

# Unified model metadata - single source of truth
# Updated to approved models list 2026-01-17
GROQ_MODELS_DETAILED = [
    # Approved Production Models
    create_model_metadata(provider="Groq", name="llama-3.3-70b-versatile", icon="Groq", tool_calling=True),
    create_model_metadata(provider="Groq", name="llama-3.1-8b-instant", icon="Groq", tool_calling=True),
    create_model_metadata(provider="Groq", name="moonshotai/kimi-k2-instruct-0905", icon="Groq", tool_calling=True),
    create_model_metadata(provider="Groq", name="openai/gpt-oss-120b", icon="Groq", tool_calling=True),
    # Deprecated Models (kept for backwards compatibility)
    create_model_metadata(provider="Groq", name="gemma2-9b-it", icon="Groq", tool_calling=True, deprecated=True),
    create_model_metadata(provider="Groq", name="gemma-7b-it", icon="Groq", tool_calling=True, deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-70b-8192", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-8b-8192", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-guard-3-8b", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-groq-70b-8192-tool-use-preview", icon="Groq", tool_calling=True, deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-groq-8b-8192-tool-use-preview", icon="Groq", tool_calling=True, deprecated=True),
    create_model_metadata(provider="Groq", name="llama-3.1-70b-versatile", icon="Groq", tool_calling=True, deprecated=True),
    create_model_metadata(provider="Groq", name="mixtral-8x7b-32768", icon="Groq", tool_calling=True, deprecated=True),
    # Unsupported Models
    create_model_metadata(provider="Groq", name="mistral-saba-24b", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="playai-tts", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="playai-tts-arabic", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="whisper-large-v3", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="whisper-large-v3-turbo", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="distil-whisper-large-v3-en", icon="Groq", not_supported=True),
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
