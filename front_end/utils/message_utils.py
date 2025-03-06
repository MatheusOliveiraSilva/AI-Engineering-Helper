import time
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessageChunk

def stream_assistant_response(prompt, graph, memory_config) -> str:
    """
    Stream assistant answer displaying thoughts in real time and, when the final
    answer starts, replacing thoughts with an expander. Returns the final generated
    answer.

    :param
      - prompt: string with users input.
      - graph: compiled langgraph's graph object.
      - memory_config: memory configuration.

    :return
      - final_response: String with final answer
    """
    final_response = ""
    streaming_thoughts = ""
    thinking_expander_created = False

    # Reinicia os pensamentos para a interação atual (não acumula com interações anteriores)
    st.session_state.thoughts = ""

    # Placeholders para atualização em tempo real
    final_placeholder = st.empty()
    thinking_placeholder = st.empty()

    for response in graph.stream(
            {"messages": [HumanMessage(content=prompt)]},
            stream_mode="messages",
            config=memory_config
    ):
        if isinstance(response, tuple):
            for item in response:
                if isinstance(item, AIMessageChunk) and item.content:

                    chunk = item.content[0]
                    if "type" in chunk:
                        if chunk["type"] == "thinking" and "thinking" in chunk:
                            if not thinking_expander_created:
                                streaming_thoughts += chunk["thinking"]
                                thinking_placeholder.markdown(
                                    f"**Model is thinking...**\n\n{streaming_thoughts}"
                                )
                        elif chunk["type"] == "text" and "text" in chunk:
                            if not thinking_expander_created:
                                thinking_placeholder.empty()
                                st.session_state.thoughts = streaming_thoughts
                                st.expander("🤖 Model's Thoughts", expanded=False).markdown(
                                    st.session_state.thoughts
                                )
                                thinking_expander_created = True
                            final_response += chunk["text"]
                            final_placeholder.markdown(final_response)
        time.sleep(0.3)

    return final_response
