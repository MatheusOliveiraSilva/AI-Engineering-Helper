import streamlit as st
import os
from streamlit_javascript import st_javascript
from chatbot.graph.chatbot_graph import graph
from front_end.utils.message_utils import stream_assistant_response

API_URL = "http://localhost:8000"

# Read CSS login style
css_path = os.path.join(os.path.dirname(__file__), "styles", "login_style.css")
with open(css_path, "r") as f:
    css_content = f.read()

# Apply CSS to the login page
st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# Manage to see if user have cookies that show they are logged in
raw_cookies = st_javascript("document.cookie")
cookies_dict = {}
if raw_cookies:
    for cookie_pair in raw_cookies.split(";"):
        key_value = cookie_pair.strip().split("=")
        if len(key_value) == 2:
            key, value = key_value
            cookies_dict[key] = value

user_sub = cookies_dict.get("sub")

# If user is not logged in, show login page
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

# If user if logged in, we proceed to application
st.title("AI Engineering Q&A")

if "messages" in st.session_state:
    if len(st.session_state.messages) <= 0:
        st.write(f"Welcome! Q&A me about AI Engineering")

# Simple memory config
memory_config = {"configurable": {"thread_id": "1"}}

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thoughts" not in st.session_state:
    st.session_state.thoughts = ""

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.thoughts:
    with st.expander("Model Thoughts", expanded=False):
        st.markdown(st.session_state.thoughts)

# Get the user input in chat box.
if prompt := st.chat_input("Chat with me"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        final_response = stream_assistant_response(prompt, graph, memory_config)

    st.session_state.messages.append({"role": "assistant", "content": final_response})
