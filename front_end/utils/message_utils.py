import time
import json
import requests
import streamlit as st
import re
from langchain_core.messages import HumanMessage, AIMessageChunk, AIMessage
from langchain_core.output_parsers import StrOutputParser

from llm_config.llm_model_config import LLMModelConfig

model_config = LLMModelConfig(provider="openai")
summary_llm = model_config.get_llm_model(model_name="gpt-4o-mini-2024-07-18")

API_URL = "http://localhost:5005"

def sanitize_tool_content(content: str) -> str:
    return content.replace("```", "")

def preprocess_tool_result(tool_result: str) -> str:
    # Remove todas as marcações de código (``` e ```json, ```sql, etc.)
    # O regex abaixo remove qualquer sequência ``` seguida de caracteres não-espaço (opcional)
    tool_result_no_fence = re.sub(r'```(\w+)?', '', tool_result).strip()

    # Remover linhas isoladas que sejam apenas "json", "sql", etc.
    # Você pode ajustar essa lista conforme necessário
    tool_result_no_fence = re.sub(
        r'^(json|sql|python)\s*$',
        '',
        tool_result_no_fence,
        flags=re.MULTILINE | re.IGNORECASE
    )

    # Agora prossegue com a mesma lógica anterior
    json_match = re.search(r'(\{.*\})$', tool_result_no_fence, re.DOTALL)
    if json_match:
        tool_result_json_str = json_match.group(1)
    else:
        tool_result_json_str = ""

    preceding = tool_result_no_fence[:json_match.start()] if json_match else tool_result_no_fence

    # Split nas linhas
    lines = preceding.splitlines()
    lines = [line.strip() for line in lines if line.strip()]

    # Se houver pelo menos 1 linha, a primeira consideramos como "Tool input"
    if lines:
        tool_input = lines[0].strip("[]\"'")
    else:
        tool_input = ""

    # As linhas seguintes até a próxima linha em branco (ou fim) consideramos como SQL
    sql_view_lines = []
    for line in lines[1:]:
        if not line.strip():
            break
        sql_view_lines.append(line)
    sql_view = "\n".join(sql_view_lines)

    # Tenta converter o JSON final para objeto
    try:
        # Substitui aspas simples por duplas para ser válido em JSON
        json_str = tool_result_json_str.replace("'", "\"")
        tool_result_json = json.loads(json_str)
        pretty_tool_result = json.dumps(tool_result_json, indent=4, ensure_ascii=False)
    except Exception:
        pretty_tool_result = tool_result_json_str

    output = f"**Tool input:** `{tool_input}`\n\n"
    output += f"**SQL View:**\n```\n{sql_view}\n```\n\n"
    output += f"**Tool Result:**\n```\n{pretty_tool_result}\n```"
    return output

def stream_assistant_response(prompt, memory_config) -> str:
    url = f"{API_URL}/chat/query_stream"

    final_response = ""
    tool_result = ""
    tool_in_progress = False
    tool_placeholder = None

    response_placeholder = st.empty()

    with requests.post(url, json={"input": prompt, "memory_config": memory_config}, stream=True) as response:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    try:
                        payload = json.loads(data_str)
                    except Exception as e:
                        st.error(f"Erro ao processar chunk SSE: {e}")
                        continue

                    content = payload.get("content", "")
                    meta = payload.get("meta", {})

                    node = meta.get("langgraph_node")

                    if node == "tools":
                        if not tool_in_progress:
                            tool_in_progress = True
                            tool_placeholder = st.info("Executando tool...")

                        tool_result += content

                    else:
                        if tool_in_progress:
                            if tool_placeholder:
                                tool_placeholder.empty()
                            tool_in_progress = False

                            if tool_result.strip():
                                formatted_tool_output = preprocess_tool_result(tool_result)
                                st.markdown(
                                    f"<details><summary>Resultado da ferramenta</summary>\n\n{formatted_tool_output}\n\n</details>",
                                    unsafe_allow_html=True
                                )
                            # Reseta as variáveis de tool
                            tool_result = ""
                            tool_placeholder = None

                        # Agora tratamos este chunk como texto normal do assistente
                        final_response += content
                        response_placeholder.markdown(final_response)

                    # Pequena pausa para permitir ao Streamlit renderizar gradualmente
                    time.sleep(0.03)

    return final_response

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