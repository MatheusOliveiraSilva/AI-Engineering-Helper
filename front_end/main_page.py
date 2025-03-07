import streamlit as st
import os
import uuid
from streamlit_javascript import st_javascript
import requests

from chatbot.graph.chatbot_graph import graph
from front_end.utils.message_utils import stream_assistant_response, convert_messages_to_save

# -------------------------------------------------------------------
# 1. Configuração da página
# -------------------------------------------------------------------
st.set_page_config(layout="wide")

# -------------------------------------------------------------------
# 2. CSS para ajustar a largura da barra lateral
# -------------------------------------------------------------------
sidebar_style = """
<style>
[data-testid="stSidebar"] > div:first-child {
    width: 200px;
}
[data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
    width: 200px;
}
[data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
    margin-left: -200px;
}
</style>
"""
st.markdown(sidebar_style, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 3. (Opcional) CSS de login externo
# -------------------------------------------------------------------
css_path = os.path.join(os.path.dirname(__file__), "styles", "login_style.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 4. Variáveis e Lógica de Login
# -------------------------------------------------------------------
API_URL = "http://localhost:8000"

# Lê cookies via JavaScript
raw_cookies = st_javascript("document.cookie")
cookies_dict = {}
if raw_cookies:
    for cookie_pair in raw_cookies.split(";"):
        key_value = cookie_pair.strip().split("=")
        if len(key_value) == 2:
            key, value = key_value
            cookies_dict[key] = value

user_sub = cookies_dict.get("sub")
session_token = cookies_dict.get("session_token")

# Se não estiver logado, exibe tela de login
if not user_sub:
    st.markdown(
        f"""
        <div class="centered">
            <h1>AI Engineering Q&A</h1>
            <h3>You need to login first</h3>
            <a href="{API_URL}/auth/login" class="login-button">Login</a>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()

# -------------------------------------------------------------------
# 5. Barra Lateral: "Conversations" e Botão "New Chat"
# -------------------------------------------------------------------
st.sidebar.title("Conversations")

if st.sidebar.button("New Chat"):
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.session_state.thoughts = ""
    st.rerun()

# -------------------------------------------------------------------
# 6. Lógica Principal do Chat
# -------------------------------------------------------------------
st.title("AI Engineering Q&A")

# Inicializa estados
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "thoughts" not in st.session_state:
    st.session_state.thoughts = ""

# Exibe histórico de mensagens atual (local)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Exibe Model Thoughts (se existirem)
if st.session_state.thoughts:
    with st.expander("Model Thoughts", expanded=False):
        st.markdown(st.session_state.thoughts)

# Caixa de input do usuário
prompt = st.chat_input("Chat with me")

if prompt:
    # Se ainda não existe thread_id, cria a conversa no back-end c/ a primeira mensagem
    if st.session_state.thread_id is None:
        # Gera um thread_id único
        st.session_state.thread_id = (session_token or "") + str(uuid.uuid4())

        # Envia para POST /conversation com a 1ª mensagem
        payload_create = {
            "session_id": session_token,
            "thread_id": st.session_state.thread_id,
            "first_message_role": "user",
            "first_message_content": prompt
        }
        resp = requests.post(f"{API_URL}/conversation", json=payload_create)
        if resp.status_code != 200:
            st.error("Erro ao criar conversa no servidor.")
    else:
        # Apenas adiciona localmente a msg do user
        st.session_state.messages.append({"role": "user", "content": prompt})

    # Exibe a mensagem no chat
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gera a resposta do LLM
    memory_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    with st.chat_message("assistant"):
        final_response = stream_assistant_response(prompt, graph, memory_config)

    # Salva a resposta no histórico local
    st.session_state.messages.append({"role": "assistant", "content": final_response})

    # -------------------------------------------------------------------
    # Agora salvamos TODO o histórico no back-end
    # -------------------------------------------------------------------

    # 1) Obtemos o histórico completo da Graph
    full_msg_objects = graph.get_state(memory_config).values["messages"]
    converted_history = convert_messages_to_save(full_msg_objects)

    # 3) PATCH /conversation, enviando a lista completa
    update_payload = {
        "thread_id": st.session_state.thread_id,
        "messages": converted_history
    }
    resp2 = requests.patch(f"{API_URL}/conversation", json=update_payload)
    if resp2.status_code != 200:
        st.error("Erro ao atualizar conversa no servidor.")
