import streamlit as st
import os
import uuid
from streamlit_javascript import st_javascript
import requests

# Import do LangGraph ou do seu fluxo
from chatbot.graph.chatbot_graph import graph
# Import da função que converte HumanMessage / AIMessage em [("user", "..."), ("assistant_thought", "..."), ...]
from front_end.utils.message_utils import stream_assistant_response, convert_messages_to_save

# 1. Configura a página como "wide" e define CSS para a barra lateral
st.set_page_config(layout="wide")

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

# 2. (Opcional) CSS de login externo (ajuste o caminho caso necessário)
css_path = os.path.join(os.path.dirname(__file__), "styles", "login_style.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

API_URL = "http://localhost:8000"

# 3. Lê cookies do navegador para saber se o usuário está logado
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

# Se não estiver logado, exibe a tela de login e para
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

# 4. Inicializa estados no session_state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
# Se quiser armazenar pensamentos fixos, mas aqui deixamos "thoughts" livre
if "thoughts" not in st.session_state:
    st.session_state.thoughts = ""

# -------------------------------------------------------------------
# 5. Função para carregar as conversas do usuário
# -------------------------------------------------------------------
def load_conversations():
    if session_token:
        resp = requests.get(f"{API_URL}/conversation?session_token={session_token}")
        if resp.status_code == 200:
            data = resp.json()
            return data["conversations"]  # lista de dicionários
        else:
            st.error("Erro ao carregar conversas.")
            return []
    return []

# -------------------------------------------------------------------
# 6. Barra Lateral: Conversas, Botão "New Chat" e listagem
# -------------------------------------------------------------------
st.sidebar.title("Conversations")

if st.sidebar.button("New Chat"):
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.session_state.thoughts = ""
    st.rerun()

conversations_list = load_conversations()

if conversations_list:
    for conv in conversations_list:
        # Cria um label p/ o botão
        label = f"Thread: {conv['thread_id'][:8]}..."
        # Define uma key única
        if st.sidebar.button(label, key=conv["thread_id"]):
            # Ao clicar, definimos thread_id e carregamos as mensagens
            st.session_state.thread_id = conv["thread_id"]
            st.session_state.messages = []
            # conv["messages"] é algo como: [["user","oi"],["assistant_thought","..."],["assistant_response","..."], ...]
            for role, content in conv["messages"]:
                st.session_state.messages.append({"role": role, "content": content})
            st.rerun()

# -------------------------------------------------------------------
# 7. Lógica Principal de Exibição do Chat
# -------------------------------------------------------------------
st.title("AI Engineering Q&A")

# Exibe o histórico que está localmente em st.session_state.messages
# mas com tratamento especial para "assistant_thought"
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]

    if role == "assistant_thought":
        # Exibe em expander "Model Thoughts"
        with st.expander("Model Thoughts", expanded=False):
            st.markdown(content)
    elif role == "assistant_response":
        # Exibe como assistente
        with st.chat_message("assistant"):
            st.markdown(content)
    elif role == "user":
        # Exibe como usuário
        with st.chat_message("user"):
            st.markdown(content)
    else:
        # Caso apareçam outros roles (assistant normal, etc.)
        with st.chat_message(role):
            st.markdown(content)

# -------------------------------------------------------------------
# 8. Captura de entrada do usuário e geração de resposta
# -------------------------------------------------------------------
prompt = st.chat_input("Chat with me")

if prompt:
    # Se não existir thread_id, criamos com POST /conversation
    if st.session_state.thread_id is None:
        st.session_state.thread_id = (session_token or "") + str(uuid.uuid4())
        payload_create = {
            "session_id": session_token,
            "thread_id": st.session_state.thread_id,
            "first_message_role": "user",
            "first_message_content": prompt
        }
        resp = requests.post(f"{API_URL}/conversation", json=payload_create)
        if resp.status_code != 200:
            st.error("Erro ao criar conversa no servidor.")

        # Localmente, adicionamos a mensagem
        st.session_state.messages.append({"role": "user", "content": prompt})
    else:
        # Se o thread_id já existe, só adicionamos localmente o "user"
        st.session_state.messages.append({"role": "user", "content": prompt})

    # Exibe no chat
    with st.chat_message("user"):
        st.markdown(prompt)

    # Chama o LLM
    memory_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    with st.chat_message("assistant"):
        final_response = stream_assistant_response(prompt, graph, memory_config)

    # Armazena a resposta no st.session_state
    st.session_state.messages.append({"role": "assistant_response", "content": final_response})

    # -------------------------------------------------------------------
    # 9. Sincroniza todo o histórico com o banco
    # -------------------------------------------------------------------
    # 9.1 Obtemos o histórico do LangChain Graph (contém user, assistant_thought, etc.)
    full_msg_objects = graph.get_state(memory_config).values["messages"]

    # 9.2 Convertemos p/ lista: [("user", "..."), ("assistant_thought","..."), ("assistant_response","...")]
    converted_history = convert_messages_to_save(full_msg_objects)

    # 9.3 PATCH /conversation
    update_payload = {
        "thread_id": st.session_state.thread_id,
        "messages": converted_history
    }
    patch_resp = requests.patch(f"{API_URL}/conversation", json=update_payload)
    if patch_resp.status_code != 200:
        st.error("Erro ao atualizar conversa no servidor.")

    # Rerun para exibir as novas mensagens
    st.rerun()
