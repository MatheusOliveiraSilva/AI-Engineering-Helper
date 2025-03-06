from chatbot.states.chatbot_states import ChatbotState
from chatbot.prompts.prompt_v0 import CHATBOT_PROMPT
from llm_config.llm_model_config import LLMModelConfig
from langchain_core.messages import SystemMessage
from vector_database.hybrid_retrieval import HybridSearchRetriever

class ChatbotsNodes:
    def __init__(self) -> None:

        llm_config = LLMModelConfig('anthropic')

        self.llm = llm_config.get_llm_model(
            model_name="claude-3-7-sonnet-latest",
            max_tokens=2048,
            thinking={"type": "enabled", "budget_tokens": 1024}
        )

        self.retriever = HybridSearchRetriever(
            index_name="ca-contextualemb-dotp-3large",
            embedding_model_name="text-embedding-3-large",
            embedding_provider="openai"
        ).retriever

    def retrieval(self, state: ChatbotState):
        """
        Retrieval node
        """
        state["context"] = self.retriever.invoke(
            state["messages"][-1].content   # Query on retriever with last message
        )
        return state

    def assistant(self, state: ChatbotState):
        """
        Assistant node
        """
        sys_msg = SystemMessage(
            content=CHATBOT_PROMPT.format(
                relevant_documents=state["context"],
                message=state["messages"][-1].content
            ),
            additional_kwargs={"cache-control": {"type": "ephemeral"}}
        )

        response = self.llm.invoke(
            [sys_msg] + state["messages"]
        )

        return {"response": response.content}
