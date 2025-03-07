import streamlit as st
import os
import uuid
from streamlit_javascript import st_javascript
import requests

from chatbot.graph.chatbot_graph import graph
from front_end.utils.message_utils import stream_assistant_response, convert_messages_to_save

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

css_path = os.path.join(os.path.dirname(__file__), "styles", "login_style.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

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
session_token = cookies_dict.get("session_token")

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

# ---------------------- STATES ----------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "thoughts" not in st.session_state:
    st.session_state.thoughts = ""

# ----------------------------------------------------
def load_conversations():
    if session_token:
        resp = requests.get(f"{API_URL}/conversation?session_token={session_token}")
        if resp.status_code == 200:
            data = resp.json()
            return data["conversations"]
        else:
            st.error("Erro ao carregar conversas.")
            return []
    return []

st.sidebar.title("Conversations")

if st.sidebar.button("New Chat"):
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.session_state.thoughts = ""
    st.rerun()

conversations_list = load_conversations()
if conversations_list:
    for conv in conversations_list:
        label = f"Thread: {conv['thread_id'][:8]}..."
        if st.sidebar.button(label, key=conv["thread_id"]):
            st.session_state.thread_id = conv["thread_id"]
            st.session_state.messages = []
            for role, content in conv["messages"]:
                st.session_state.messages.append({"role": role, "content": content})
            st.rerun()

st.title("AI Engineering Q&A")

# ------------------ Exibição Principal --------------------
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    if role == "assistant_thought":
        with st.expander("Model Thoughts", expanded=False):
            st.markdown(content)
    elif role == "assistant_response":
        with st.chat_message("assistant"):
            st.markdown(content)
    elif role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message(role):
            st.markdown(content)

prompt = st.chat_input("Chat with me")

# ---------- Função de merge -----------
def merge_local_with_graph(local_msgs, graph_msgs):
    """
    local_msgs -> [{"role":"assistant_thought","content":"Pensamento..."}, ...]
    graph_msgs -> [("assistant_response","Resposta final"), ...]

    Queremos uma lista final do tipo [("assistant_thought","..."),("assistant_response","..."),...].
    """

    # Converte local_msgs p/ tuplas
    local_tuples = []
    for m in local_msgs:
        local_tuples.append((m["role"], m["content"]))

    final_list = list(graph_msgs)

    # Se o `assistant_thought` de local não estiver no final_list, adiciona
    for tup in local_tuples:
        if tup not in final_list:
            final_list.append(tup)

    return final_list

if prompt:
    # Se não existir thread_id, cria com POST /conversation
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
        st.session_state.messages.append({"role": "user", "content": prompt})
    else:
        # Se já existe
        st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Chama o LLM
    memory_config = {"configurable": {"thread_id": st.session_state.thread_id}}
    with st.chat_message("assistant"):
        final_response = stream_assistant_response(prompt, graph, memory_config)

    st.session_state.messages.append({"role": "assistant_response", "content": final_response})

    # --- PEGA O ESTADO FINAL DO GRAPH ---
    full_msg_objects = graph.get_state(memory_config).values["messages"]

    # Converte p/ ex: [("user","..."), ("assistant_thought","..."), ("assistant_response","...")]
    final_converted = convert_messages_to_save(full_msg_objects)

    # MERGE: local (incluindo assistant_thought) + final do graph
    merged_list = merge_local_with_graph(st.session_state.messages, final_converted)
    print("DEBUG merged_list:", merged_list)  # ou st.write(merged_list)

    # Patch
    update_payload = {
        "thread_id": st.session_state.thread_id,
        "messages": merged_list
    }
    patch_resp = requests.patch(f"{API_URL}/conversation", json=update_payload)
    if patch_resp.status_code != 200:
        st.error("Erro ao atualizar conversa no servidor.")

