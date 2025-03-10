import sys
import os

# Get the base directory and append to sys.path to allow imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import streamlit as st
import os
import uuid
from streamlit_javascript import st_javascript
import requests

from front_end.utils.message_utils import (stream_assistant_response, summary_conversation_theme,
                                           get_chat_history)

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

API_URL = "http://localhost:5005"

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

# ------------------- Loading Chat History -------------------
def load_conversations():
    if session_token:
        resp = requests.get(f"{API_URL}/conversation?session_token={session_token}")
        if resp.status_code == 200:
            data = resp.json()
            return data["conversations"]
        else:
            st.error("Erro to load chats.")
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
        label = f"{conv['thread_name']}"
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
    if role == "tool_response":
        with st.expander("Tool Response:", expanded=False):
            st.markdown(content)
    elif role == "tool_call":
        with st.chat_message("assistant"):
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

if prompt:
    if st.session_state.thread_id is None:
        st.session_state.thread_id = (session_token or "") + str(uuid.uuid4())
        conversation_theme = summary_conversation_theme(prompt)
        payload_create = {
            "session_id": session_token,
            "thread_id": st.session_state.thread_id,
            "thread_name": conversation_theme,
            "first_message_role": "user",
            "first_message_content": prompt
        }
        resp = requests.post(f"{API_URL}/conversation", json=payload_create)
        if resp.status_code != 200:
            st.error("Error to create new conversation.")
        st.session_state.messages.append({"role": "user", "content": prompt})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    memory_config = {"configurable": {"thread_id": st.session_state.thread_id}}

    # Aqui usamos a nova função de streaming
    with st.chat_message("assistant"):
        final_response = stream_assistant_response(prompt, memory_config)
        # Se quiser, no final, você pode colocar algo fixo ou "fim da resposta"
        # st.markdown(final_response)

    st.session_state.messages.append({"role": "assistant_response", "content": final_response})

    # Depois atualizamos a conversa
    chat_history = get_chat_history(memory_config)
    update_payload = {
        "thread_id": st.session_state.thread_id,
        "messages": chat_history
    }
    patch_resp = requests.patch(f"{API_URL}/conversation", json=update_payload)
    if patch_resp.status_code != 200:
        st.error("Error on updating conversation.")


