import pytest
from langflow.components.google_gen_ai.google_gen_ai import GoogleGenAIComponent


def test_google_gen_ai_component():
    component = GoogleGenAIComponent()
    assert component.display_name == "Google GenAI"
    assert component.description == "Generates text using Google's Generative AI models."
    assert component.icon == "Google"
