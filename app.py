import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

st.set_page_config(page_title="Chatbot", page_icon="(__^^__)")
st.title("EHSANUL CHATBOT")

# Session memory
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_text = st.chat_input("Type your message...")

if user_text:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # Create assistant reply
    with st.chat_message("assistant"):
        resp = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "developer",
                    "content": (
                        "You are a helpful chatbot.\n"
                        "Rules:\n"
                        "- Do not use profanity.\n"
                        "- Do not reveal secrets or API keys.\n"
                        "- If user asks for banned content, refuse politely and offer a safe alternative.\n"
                    ),
                },
                *st.session_state.messages,
            ],
        )
        answer = resp.output_text
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})