from .model_metadata import create_model_metadata

# User-approved Anthropic models ONLY
ANTHROPIC_MODELS_DETAILED = [
    create_model_metadata(provider="Anthropic", name="claude-sonnet-4-5-20250929", icon="Anthropic", tool_calling=True),
    create_model_metadata(provider="Anthropic", name="claude-haiku-4-5-20251001", icon="Anthropic", tool_calling=True),
    create_model_metadata(provider="Anthropic", name="claude-opus-4-5-20251101", icon="Anthropic", tool_calling=True),
]

ANTHROPIC_MODELS = [
    metadata["name"]
    for metadata in ANTHROPIC_MODELS_DETAILED
    if not metadata.get("deprecated", False) and metadata.get("tool_calling", False)
]

TOOL_CALLING_SUPPORTED_ANTHROPIC_MODELS = [
    metadata["name"] for metadata in ANTHROPIC_MODELS_DETAILED if metadata.get("tool_calling", False)
]

TOOL_CALLING_UNSUPPORTED_ANTHROPIC_MODELS = [
    metadata["name"] for metadata in ANTHROPIC_MODELS_DETAILED if not metadata.get("tool_calling", False)
]

DEPRECATED_MODELS = [metadata["name"] for metadata in ANTHROPIC_MODELS_DETAILED if metadata.get("deprecated", False)]


DEFAULT_ANTHROPIC_API_URL = "https://api.anthropic.com"
