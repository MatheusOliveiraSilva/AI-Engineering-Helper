import streamlit as st
import os
import uuid
from streamlit_javascript import st_javascript
from chatbot.graph.chatbot_graph import graph
from front_end.utils.message_utils import stream_assistant_response

# -------------------------------------------------------------------
# 1. Configuração da página (deve ser o primeiro comando Streamlit)
# -------------------------------------------------------------------
st.set_page_config(layout="wide")

# -------------------------------------------------------------------
# 2. CSS para ajustar a largura da barra lateral
# -------------------------------------------------------------------
sidebar_style = """
<style>
/* Força a largura da barra lateral */
[data-testid="stSidebar"] > div:first-child {
    width: 200px; /* Ajuste conforme desejar */
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
# 3. CSS de login (carregado de um arquivo externo, opcional)
# -------------------------------------------------------------------
css_path = os.path.join(os.path.dirname(__file__), "styles", "login_style.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 4. Lógica de login via cookie "sub"
# -------------------------------------------------------------------
API_URL = "http://localhost:8000"

raw_cookies = st_javascript("document.cookie")
cookies_dict = {}
if raw_cookies:
    for cookie_pair in raw_cookies.split(";"):
        key_value = cookie_pair.strip().split("=")
        if len(key_value) == 2:
            key, value = key_value
            cookies_dict[key] = value

user_sub = cookies_dict.get("sub")

if not user_sub:
    # Caso não esteja logado, exibe tela de login
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
# 5. Barra Lateral: Conversas e botão "New Chat"
# -------------------------------------------------------------------
st.sidebar.title("Conversations")

# Botão para criar um novo chat
if st.sidebar.button("New Chat"):
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.session_state.thoughts = ""
    st.rerun()

# -------------------------------------------------------------------
# 6. Lógica Principal da Aplicação
# -------------------------------------------------------------------
st.title("AI Engineering Q&A")

# Inicializa estados se não existirem
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "thoughts" not in st.session_state:
    st.session_state.thoughts = ""

# Exibe histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Exibe Model Thoughts se houver
if st.session_state.thoughts:
    with st.expander("Model Thoughts", expanded=False):
        st.markdown(st.session_state.thoughts)

# Captura a entrada do usuário
prompt = st.chat_input("Chat with me")

if prompt:
    # Se ainda não tiver thread_id, gera um
    if st.session_state.thread_id is None:
        st.session_state.thread_id = str(uuid.uuid4())

    # Config de memória (exemplo)
    #memory_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    memory_config = {"configurable": {"thread_id": "front1"}}

    # Mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Resposta do LLM
    with st.chat_message("assistant"):
        final_response = stream_assistant_response(prompt, graph, memory_config)

    # Armazena no histórico
    st.session_state.messages.append({"role": "assistant", "content": final_response})
