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

def stream_assistant_response(prompt, memory_config) -> str:
    """
    Faz a requisição em streaming e atualiza a interface do Streamlit em tempo real.
    """
    url = f"{API_URL}/chat/query_stream"
    final_response = ""
    tool_result = ""

    # Apenas um placeholder para exibir o conteúdo à medida que chega
    message_placeholder = st.empty()

    with requests.post(url, json={"input": prompt, "memory_config": memory_config}, stream=True) as response:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    try:
                        payload = json.loads(data_str)
                    except Exception as e:
                        st.error(f"Erro ao processar chunk: {e}")
                        continue

                    content = payload.get("content", "")
                    meta = payload.get("meta", {})

                    # Se for resultado de tool
                    if meta.get("langgraph_node") == "tools":
                        tool_result += content
                        message_placeholder.markdown(
                            f"**[Resultado da ferramenta]**\n\n```\n{tool_result}\n```"
                        )
                    else:
                        final_response += content
                        message_placeholder.markdown(final_response)

                    time.sleep(0.05)

    return final_response


# def stream_assistant_response(prompt, memory_config) -> str:
#     # make a post request to the API
#     response = requests.post(f"{API_URL}/chat/query", json={"input": prompt, "memory_config": memory_config})
#     return response.json()["answer"]

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