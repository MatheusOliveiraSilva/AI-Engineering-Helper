import time
import json
import requests
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessageChunk, AIMessage
from langchain_core.output_parsers import StrOutputParser

from llm_config.llm_model_config import LLMModelConfig

model_config = LLMModelConfig(provider="openai")
summary_llm = model_config.get_llm_model(model_name="gpt-4o-mini-2024-07-18")

API_URL = "http://localhost:5005"

# def stream_assistant_response(prompt, graph, memory_config) -> str:
#     """
#     Stream assistant answer displaying thoughts in real time and, when the final
#     answer starts, replacing thoughts with an expander. Returns the final generated
#     answer.
#     """
#     final_response = ""
#     streaming_thoughts = ""
#     thinking_expander_created = False
#
#     # Reinicia os pensamentos para a interação atual (não acumula com interações anteriores)
#     st.session_state.thoughts = ""
#
#     # Placeholders para atualização em tempo real
#     final_placeholder = st.empty()
#     thinking_placeholder = st.empty()
#
#     for response in graph.stream(
#             {"messages": [HumanMessage(content=prompt)]},
#             stream_mode="messages",
#             config=memory_config
#     ):
#         if isinstance(response, tuple):
#             for item in response:
#                 if isinstance(item, AIMessageChunk) and item.content:
#
#                     chunk = item.content[0]
#                     if "type" in chunk:
#                         if chunk["type"] == "thinking" and "thinking" in chunk:
#                             if not thinking_expander_created:
#                                 streaming_thoughts += chunk["thinking"]
#                                 thinking_placeholder.markdown(
#                                     f"**Model is thinking...**\n\n{streaming_thoughts}"
#                                 )
#                         elif chunk["type"] == "text" and "text" in chunk:
#                             if not thinking_expander_created:
#                                 thinking_placeholder.empty()
#                                 st.session_state.thoughts = streaming_thoughts
#                                 st.expander("🤖 Model's Thoughts", expanded=False).markdown(
#                                     st.session_state.thoughts
#                                 )
#                                 thinking_expander_created = True
#                             final_response += chunk["text"]
#                             final_placeholder.markdown(final_response)
#         time.sleep(0.3)
#
#     return final_response

def stream_assistant_response(prompt, memory_config) -> str:
    # make a post request to the API
    response = requests.post(f"{API_URL}/chat/query", json={"input": prompt, "memory_config": memory_config})
    return response.json()["answer"]

def get_chat_history(memory_config) -> list:
    """
    Get the chat history from the API.
    """
    response = requests.get(f"{API_URL}/chat/history", json={"memory_config": memory_config})
    return response.json()["messages"]

def summary_conversation_theme(prompt: str) -> str:
    """
    Summarize the conversation theme based on the user's first message.
    """

    summary_prompt = "Take the user input prompt and resume it in a few words as the main theme of the conversation. Try to use less min2 max5 words. User prompt: {prompt}"

    chain = summary_llm | StrOutputParser()

    theme = chain.invoke(summary_prompt.format(prompt=prompt))

    return theme if theme else "General Chat"

if __name__ == "__main__":
    print(summary_conversation_theme("Talk about HyDE"))