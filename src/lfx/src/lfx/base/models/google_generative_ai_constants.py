from .model_metadata import create_model_metadata

# User-approved Google models ONLY
GOOGLE_GENERATIVE_AI_MODELS_DETAILED = [
    create_model_metadata(
        provider="Google Generative AI",
        name="gemini-3-flash-preview",
        icon="GoogleGenerativeAI",
        tool_calling=True,
        preview=True,
    ),
    create_model_metadata(
        provider="Google Generative AI",
        name="gemini-3-pro-preview",
        icon="GoogleGenerativeAI",
        tool_calling=True,
        preview=True,
    ),
]

GOOGLE_GENERATIVE_AI_MODELS = [metadata["name"] for metadata in GOOGLE_GENERATIVE_AI_MODELS_DETAILED]
