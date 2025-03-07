import streamlit as st
from streamlit_javascript import st_javascript
import time
from chatbot.graph.chatbot_graph import graph
from front_end.utils.message_utils import stream_assistant_response

# URL da API de autenticação (ajuste conforme necessário)
API_URL = "http://localhost:8000"

# --- Leitura do Cookie "sub" ---
raw_cookies = st_javascript("document.cookie")

# Parse da string de cookies
cookies_dict = {}
if raw_cookies:
    for cookie_pair in raw_cookies.split(";"):
        key_value = cookie_pair.strip().split("=")
        if len(key_value) == 2:
            key, value = key_value
            cookies_dict[key] = value

user_sub = cookies_dict.get("sub")

# Se não estiver logado, exibe tela de login
if not user_sub:
    st.title("Login Necessário")
    st.write("Você precisa fazer login para acessar o app.")
    st.markdown(f"[Fazer Login]({API_URL}/auth/login)")
    st.stop()

# --- Se o cookie 'sub' existe, prossegue para a aplicação principal ---
st.title("AI Engineering Q&A")
st.write(f"Bem-vindo!")

# Exemplo de configuração de memória e thread
memory_config = {"configurable": {"thread_id": "1"}}

# Inicializa históricos, se necessário
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "thoughts" not in st.session_state:
    st.session_state["thoughts"] = ""

# Exibe o histórico de mensagens no chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Se já houver pensamentos salvos, exibe-os em um expander (colapsado)
if st.session_state.thoughts:
    with st.expander("Model Thoughts", expanded=False):
        st.markdown(st.session_state.thoughts)

# Captura a entrada do usuário
if prompt := st.chat_input("Chat with me"):
    # Adiciona a mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Cria o container de mensagem do assistente e chama a função de streaming
    with st.chat_message("assistant"):
        final_response = stream_assistant_response(prompt, graph, memory_config)

    # Armazena a resposta final no histórico
    st.session_state.messages.append({"role": "assistant", "content": final_response})
