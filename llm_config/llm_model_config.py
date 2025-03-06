import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT_DIR / '.env')

class LLMModelConfig:
    def __init__(self,
                 provider: str
                 ) -> None:

        self.provider = provider
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

    def get_llm_model(self, model_name, temperature=0.7, max_tokens=1000, **kwargs):

        if 'thinking' in kwargs and kwargs['thinking']['type'] == 'enabled':
            temperature = 1

        if self.provider == 'openai':
            return ChatOpenAI(
                api_key=self.OPENAI_API_KEY,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

        if self.provider == 'anthropic':
            return ChatAnthropic(
                api_key=self.ANTHROPIC_API_KEY,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

if __name__ == "__main__":
    llm_config = LLMModelConfig('anthropic')
    llm = llm_config.get_llm_model(
        model_name="claude-3-7-sonnet-latest",
        max_tokens=2048,
        thinking={"type": "enabled", "budget_tokens": 1024}
    )

    print(llm.invoke("What is the meaning of life?"))
