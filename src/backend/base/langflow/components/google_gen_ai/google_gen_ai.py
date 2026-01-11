from langflow.base.models.model import LCModelComponent
from langflow.field_typing import LanguageModel
from langflow.io import DropdownInput, Handle, MessageInput, SecretStrInput, StrInput
from langflow.schema.message import Message


class GoogleGenAIComponent(LCModelComponent):
    display_name = "Google GenAI"
    description = "Generates text using Google's Generative AI models."
    documentation = "https://ai.google.dev/docs"
    icon = "Google"

    inputs = [
        StrInput(name="project_id", display_name="Project ID", info="Your Google Cloud project ID."),
        SecretStrInput(name="api_key", display_name="API Key", info="Your Google GenAI API key."),
        DropdownInput(
            name="model_name",
            display_name="Model Name",
            options=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"],
            value="gemini-1.5-flash",
        ),
        MessageInput(name="input_value", display_name="Input"),
    ]

    outputs = [
        Handle(name="output", display_name="Output", is_list=False),
    ]

    def build_model(self) -> LanguageModel:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Could not import langchain_google_genai. Please install it with `pip install langchain-google-genai`.")

        return ChatGoogleGenerativeAI(
            project_id=self.project_id,
            google_api_key=self.api_key,
            model=self.model_name,
        )

    async def build(self, *args, **kwargs) -> list[Message]:
        model = self.build_model()
        result = await model.ainvoke(self.input_value)
        return [Message(text=result.content)]
