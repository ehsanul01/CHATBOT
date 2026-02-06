import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import bcrypt

import streamlit_authenticator as stauth

from firebase_config import db
from auth_config import credentials, cookie_name, cookie_key, cookie_expiry_days


# ------------------ Load API Key ------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



def get_user_doc(username: str):
    docs = db.collection("users").where("username", "==", username).stream()
    for d in docs:
        return d.id, d.to_dict()
    return None, None

def create_user(username: str, name: str, password: str):
    # basic validation
    if len(username) < 3 or len(password) < 6:
        return False, "Username must be 3+ chars and password 6+ chars."

    _, existing = get_user_doc(username)
    if existing:
        return False, "Username already exists."

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    db.collection("users").add({
        "username": username,
        "name": name,
        "pw_hash": pw_hash,
        "created_at": datetime.utcnow()
    })
    return True, "Account created! Please log in."

def verify_user(username: str, password: str):
    _, user = get_user_doc(username)
    if not user:
        return False, None

    pw_hash = user.get("pw_hash", "")
    ok = bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8"))
    return ok, user
# ---- Dark/Light mode toggle ----
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

st.sidebar.toggle("🌙 Dark mode", key="dark_mode")

if st.session_state.dark_mode:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        [data-testid="stSidebar"] { background-color: #111827; }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .stApp { background-color: white; color: black; }
        [data-testid="stSidebar"] { background-color: #f8fafc; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ------------------ Firestore Helpers ------------------
# ------------------ Firestore Helpers (Topics/Threads) ------------------

def create_topic(username: str, title: str) -> str:
    """Create a new topic/thread and return its Firestore doc id."""
    
    doc_ref = db.collection("topics").document()  # auto-ID created here

    doc_ref.set({
        "username": username,
        "title": title,
        "created_at": datetime.utcnow()
    })

    return doc_ref.id


def list_topics(username: str):
    """Return topics for user sorted by created_at."""
    docs = db.collection("topics").where("username", "==", username).stream()
    topics = []
    for d in docs:
        x = d.to_dict()
        topics.append({
            "id": d.id,
            "title": x.get("title", "Untitled"),
            "created_at": x.get("created_at")
        })
    topics.sort(key=lambda t: t.get("created_at") or datetime.min)
    return topics


def save_message(username: str, topic_id: str, role: str, content: str):
    """Save message under a topic/thread."""
    db.collection("messages").add({
        "username": username,
        "topic_id": topic_id,
        "role": role,
        "content": content,
        "time": datetime.utcnow()
    })


def load_messages(username: str, topic_id: str):
    """Load messages for a topic. Sort locally to avoid index requirements."""
    docs = (
        db.collection("messages")
        .where("username", "==", username)
        .where("topic_id", "==", topic_id)
        .stream()
    )
    items = [d.to_dict() for d in docs]
    items.sort(key=lambda x: x.get("time"))
    return [{"role": x["role"], "content": x["content"]} for x in items]


def clear_topic(username: str, topic_id: str):
    """Delete all messages in a topic for this user."""
    docs = (
        db.collection("messages")
        .where("username", "==", username)
        .where("topic_id", "==", topic_id)
        .stream()
    )
    for d in docs:
        d.reference.delete()
# ------------------ Streamlit Page Setup ------------------
st.set_page_config(page_title="Ehsanul Chatbot", page_icon="__(^^)__")
st.title("EHCHBOT")
# ------------------ Auth (Login / Sign Up) ------------------
if "auth" not in st.session_state:
    st.session_state.auth = False
if "username" not in st.session_state:
    st.session_state.username = None
if "name" not in st.session_state:
    st.session_state.name = None

if not st.session_state.auth:
    tab_login, tab_signup = st.tabs(["🔐 Login", "🆕 Sign Up"])

    with tab_login:
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            ok, user = verify_user(u.strip(), p)
            if ok:
                st.session_state.auth = True
                st.session_state.username = user["username"]
                st.session_state.name = user.get("name", user["username"])
                st.rerun()
            else:
                st.error("Incorrect username or password")

    with tab_signup:
        su = st.text_input("Choose a username", key="su_user")
        sn = st.text_input("Your name", key="su_name")
        sp = st.text_input("Create a password", type="password", key="su_pass")
        if st.button("Create account"):
            ok, msg = create_user(su.strip(), sn.strip(), sp)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.stop()

# Logged in
username = st.session_state.username
name = st.session_state.name

st.sidebar.success(f"✅ Logged in as: {name} ({username})")
if st.sidebar.button("Logout"):
    st.session_state.auth = False
    st.session_state.username = None
    st.session_state.name = None
    st.rerun()


# ------------------ Sidebar Option: Clear History ------------------
# ------------------ Sidebar: Topics ------------------
st.sidebar.subheader("Topics")

# Ensure user has at least 1 topic
topics = list_topics(username)
if "active_topic_id" not in st.session_state:
    if len(topics) == 0:
        st.session_state.active_topic_id = create_topic(username, "General")
        topics = list_topics(username)
    else:
        st.session_state.active_topic_id = topics[-1]["id"]  # newest

# Create a new topic
new_title = st.sidebar.text_input("New topic name", placeholder="e.g., Resume, ML, Fitness")
if st.sidebar.button("➕ Create Topic"):
    title = (new_title or "").strip() or "New Topic"
    st.session_state.active_topic_id = create_topic(username, title)
    st.rerun()

# Pick active topic
topics = list_topics(username)
topic_titles = [t["title"] for t in topics]
topic_ids = [t["id"] for t in topics]

# If active id missing (deleted), fallback
if st.session_state.active_topic_id not in topic_ids and len(topic_ids) > 0:
    st.session_state.active_topic_id = topic_ids[-1]

# Safety check: ensure active topic exists
if st.session_state.active_topic_id not in topic_ids:
    if len(topic_ids) > 0:
        st.session_state.active_topic_id = topic_ids[-1]  # fallback to newest
    else:
        # No topics exist at all → create default
        st.session_state.active_topic_id = create_topic(username, "General")
        st.rerun()

active_index = topic_ids.index(st.session_state.active_topic_id)

selected_title = st.sidebar.selectbox(
    "Select topic",
    topic_titles,
    index=active_index
)
st.session_state.active_topic_id = topic_ids[topic_titles.index(selected_title)]
active_topic_id = st.session_state.active_topic_id

# Clear current topic
if st.sidebar.button(" Clear THIS topic"):
    clear_topic(username, active_topic_id)
    st.rerun()


# ------------------ Load + Display Messages for Active Topic ------------------
messages = load_messages(username, active_topic_id)

st.subheader(f" Topic: {selected_title}")

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ------------------ Chat Input (only for active topic) ------------------
user_text = st.chat_input(f"Message in: {selected_title}")

if user_text:
    save_message(username, active_topic_id, "user", user_text)

    # Reload for context
    messages = load_messages(username, active_topic_id)

    with st.chat_message("user"):
        st.markdown(user_text)

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
                        "- Refuse unsafe requests politely.\n"
                    ),
                },
                *messages,
            ],
        )
        answer = resp.output_text
        st.markdown(answer)

    save_message(username, active_topic_id, "assistant", answer)
    st.rerun()