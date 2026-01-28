import streamlit as st
import requests

# ---------------- CONFIG ----------------
BACKEND_URL = "http://localhost:8000/chat"

st.set_page_config(
    page_title="Neuraltrix AI",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Neuraltrix AI Assistant")

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- CHAT HISTORY ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- INPUT BOX ----------------
user_input = st.chat_input("Ask something...")

if user_input:
    # Show user message
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"question": user_input},
            timeout=30
        )
        answer = response.json().get("answer", "No response received.")
    except:
        answer = "⚠️ Unable to connect to server."

    # Show assistant reply
    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

    with st.chat_message("assistant"):
        st.markdown(answer)
