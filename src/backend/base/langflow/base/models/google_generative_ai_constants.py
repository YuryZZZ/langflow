from .model_metadata import create_model_metadata

# Unified model metadata - single source of truth
# Updated to approved models list 2026-01-17
GOOGLE_GENERATIVE_AI_MODELS_DETAILED = [
    # Approved Gemini 3 models
    create_model_metadata(
        provider="Google Generative AI", name="gemini-3-flash-preview", icon="GoogleGenerativeAI", tool_calling=True
    ),
    create_model_metadata(
        provider="Google Generative AI", name="gemini-3-pro-preview", icon="GoogleGenerativeAI", tool_calling=True
    ),
    # Legacy models (kept for backwards compatibility)
    create_model_metadata(
        provider="Google Generative AI", name="gemini-2.0-flash", icon="GoogleGenerativeAI", tool_calling=True, deprecated=True
    ),
    create_model_metadata(
        provider="Google Generative AI", name="gemini-1.5-pro", icon="GoogleGenerativeAI", tool_calling=True, deprecated=True
    ),
    create_model_metadata(
        provider="Google Generative AI", name="gemini-1.5-flash", icon="GoogleGenerativeAI", tool_calling=True, deprecated=True
    ),
    create_model_metadata(
        provider="Google Generative AI", name="gemini-1.5-flash-8b", icon="GoogleGenerativeAI", tool_calling=True, deprecated=True
    ),
    # GEMMA (kept for local/edge use)
    create_model_metadata(
        provider="Google Generative AI", name="gemma-2-2b", icon="GoogleGenerativeAI", tool_calling=True, deprecated=True
    ),
    create_model_metadata(
        provider="Google Generative AI", name="gemma-2-9b", icon="GoogleGenerativeAI", tool_calling=True, deprecated=True
    ),
    create_model_metadata(
        provider="Google Generative AI", name="gemma-2-27b", icon="GoogleGenerativeAI", tool_calling=True, deprecated=True
    ),
]

GOOGLE_GENERATIVE_AI_MODELS = [
    metadata["name"] for metadata in GOOGLE_GENERATIVE_AI_MODELS_DETAILED
    if not metadata.get("deprecated", False)
]
