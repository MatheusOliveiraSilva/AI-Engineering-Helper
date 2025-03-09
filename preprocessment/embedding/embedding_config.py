import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / '.env')

class EmbeddingConfig:
    def __init__(self,
                 embedding_model: str,
                 provider: str = "openai"
                 ) -> None:
        """
        Class used to manage with embedding configuration we are using in the project.
        """
        self.check_provider(provider)
        self.provider = provider

        self.check_model_name(embedding_model)
        self.embedding_model_name = embedding_model

        self.instanced_model = self.instance_embedding_model(self.embedding_model_name)

    @staticmethod
    def check_provider(provider: str) -> None:
        if provider not in ["azure", "openai"]:
            raise ValueError("The provider must be 'azure' or 'openai'.")

    @staticmethod
    def check_model_name(model_name: str) -> None:
        if model_name not in ["text-embedding-ada-002", "text-embedding-3-large"]:
            raise ValueError("The model name must be 'text-embedding-ada-002' or 'text-embedding-3-large'.")

    def instance_embedding_model(self, embedding_model: str):
        instanced_model = None
        if self.provider == "azure":
            instanced_model = AzureOpenAIEmbeddings(
                model=embedding_model,
                openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                openai_api_base=os.getenv("AZURE_OPENAI_BASE_URL")
            )
        if self.provider == "openai":
            instanced_model = OpenAIEmbeddings(
                model=embedding_model,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )

        # Setup more models if needed (and add the providers and the models in check functions).

        return instanced_model

    def get_embedding_model(self):
        return self.instanced_model

if __name__ == "__main__":
    embedding_config = EmbeddingConfig(embedding_model="text-embedding-ada-002", provider="azure")
    embedding_model = embedding_config.get_embedding_model()  # If run with no errors, all gucci
