from .model_metadata import create_model_metadata

# Unified model metadata
# Updated to approved models list 2026-01-17
#
# NOTE: This file serves as a FALLBACK when the dynamic model discovery system
# (groq_model_discovery.py) cannot fetch fresh data from the Groq API.
#
GROQ_MODELS_DETAILED = [
    # ===== APPROVED PRODUCTION MODELS =====
    create_model_metadata(provider="Groq", name="llama-3.3-70b-versatile", icon="Groq", tool_calling=True),
    create_model_metadata(provider="Groq", name="llama-3.1-8b-instant", icon="Groq", tool_calling=True),
    create_model_metadata(provider="Groq", name="moonshotai/kimi-k2-instruct-0905", icon="Groq", tool_calling=True),
    create_model_metadata(provider="Groq", name="openai/gpt-oss-120b", icon="Groq", tool_calling=True),
    # ===== DEPRECATED MODELS =====
    # Keep these for backwards compatibility - users may have flows using them
    create_model_metadata(provider="Groq", name="gemma2-9b-it", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="gemma-7b-it", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-70b-8192", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-8b-8192", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-guard-3-8b", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-3.2-1b-preview", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-3.2-3b-preview", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-3.2-11b-vision-preview", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-3.2-90b-vision-preview", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-3.3-70b-specdec", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="qwen-qwq-32b", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="qwen-2.5-coder-32b", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="qwen-2.5-32b", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="deepseek-r1-distill-qwen-32b", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="deepseek-r1-distill-llama-70b", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-groq-70b-8192-tool-use-preview", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama3-groq-8b-8192-tool-use-preview", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="llama-3.1-70b-versatile", icon="Groq", deprecated=True),
    create_model_metadata(provider="Groq", name="mixtral-8x7b-32768", icon="Groq", deprecated=True),
    # ===== UNSUPPORTED MODELS =====
    create_model_metadata(provider="Groq", name="mistral-saba-24b", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="playai-tts", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="playai-tts-arabic", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="whisper-large-v3", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="whisper-large-v3-turbo", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="distil-whisper-large-v3-en", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="meta-llama/llama-guard-4-12b", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="meta-llama/llama-prompt-guard-2-86m", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="meta-llama/llama-prompt-guard-2-22m", icon="Groq", not_supported=True),
    create_model_metadata(provider="Groq", name="openai/gpt-oss-safeguard-20b", icon="Groq", not_supported=True),
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
