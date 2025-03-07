from typing_extensions import TypedDict
from typing import Annotated, List

from langgraph.graph.message import add_messages
from langchain_core.documents import Document

class ChatbotState(TypedDict):
    messages: List
    context: List[Document]

