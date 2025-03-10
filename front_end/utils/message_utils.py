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
    Realiza uma chamada ao endpoint de streaming (/chat/query_stream) e atualiza a interface
    em tempo real. Dependendo do tipo de mensagem (tool call, resultado de tool ou resposta final),
    atualiza os placeholders correspondentes.
    """
    url = f"{API_URL}/chat/query_stream"
    final_response = ""
    tool_result = ""
    tool_message_displayed = False

    # Placeholders para atualização em tempo real na UI
    final_placeholder = st.empty()       # para a resposta final do modelo
    tool_placeholder = st.empty()        # para mensagens de tool (status e resultado)

    with requests.post(url, json={"input": prompt, "memory_config": memory_config}, stream=True) as response:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                # O padrão SSE envia linhas no formato "data: <json>\n\n"
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    try:
                        payload = json.loads(data_str)
                    except Exception as e:
                        st.error("Erro ao processar chunk: " + str(e))
                        continue

                    content = payload.get("content", "")
                    meta = payload.get("meta", {})

                    # Se for mensagem do nó "assistant" indicando início da chamada de uma tool
                    if meta.get("langgraph_node") == "assistant" and \
                       meta.get("langgraph_triggers") and "start:assistant" in meta.get("langgraph_triggers"):
                        # Aqui, você pode tentar extrair o nome da tool (caso a informação esteja disponível)
                        tool_name = "desconhecida"
                        if not tool_message_displayed:
                            tool_placeholder.info(f"Executando tool {tool_name}...")
                            tool_message_displayed = True

                    # Se for mensagem do nó "tools", trata como resultado da ferramenta
                    elif meta.get("langgraph_node") == "tools":
                        tool_result += content
                        # Atualiza um expander via HTML com tag <details> para exibir o resultado da tool
                        tool_placeholder.markdown(
                            f"**Resultado da ferramenta (clique para expandir):**\n\n"
                            f"<details><summary>Clique para ver</summary>\n\n{tool_result}\n\n</details>",
                            unsafe_allow_html=True,
                        )
                    else:
                        # Caso contrário, trata como parte da resposta final do modelo
                        final_response += content
                        final_placeholder.markdown(final_response)
                    # Pequena pausa para suavizar a atualização (opcional)
                    time.sleep(0.1)
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