import streamlit as st
import uuid
import time
from api_client import send_chat_message, check_health, login, register, fetch_sessions, create_session, fetch_chat_history, rename_session, delete_session

st.set_page_config(page_title="Agricultural AI", layout="wide")

st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .agent-box {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Auth state
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Chat state
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

def refresh_sessions():
    if st.session_state.access_token:
        fetched = fetch_sessions(st.session_state.access_token)
        new_sessions = {}
        for s in fetched:
            # Check if we already have it locally to avoid redundant API calls during reruns
            # But on fresh login, we must fetch from the backend
            existing = st.session_state.sessions.get(s['id'])
            if not existing or not existing.get("messages"):
                messages = fetch_chat_history(s['id'], st.session_state.access_token)
            else:
                messages = existing["messages"]
                
            new_sessions[s['id']] = {
                "title": s['title'],
                "messages": messages
            }
        st.session_state.sessions = new_sessions

def create_new_chat():
    res = create_session(st.session_state.access_token, "New Chat")
    if "error" not in res:
        st.session_state.active_session_id = res['id']
        refresh_sessions()

def delete_current_session(s_id):
    res = delete_session(s_id, st.session_state.access_token)
    if "error" not in res:
        if st.session_state.active_session_id == s_id:
            st.session_state.active_session_id = None
        refresh_sessions()
        st.rerun()

def rename_current_session(s_id, new_title):
    res = rename_session(s_id, st.session_state.access_token, new_title)
    if "error" not in res:
        refresh_sessions()
        st.rerun()

def logout_user():
    st.session_state.access_token = None
    st.session_state.current_user = None
    st.session_state.sessions = {}
    st.session_state.active_session_id = None

# --- AUTH FLOW ---
if not st.session_state.access_token:
    st.title("Agricultural AI - Login")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            l_email = st.text_input("Email")
            l_pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                res = login(l_email, l_pwd)
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.session_state.access_token = res["accessToken"]
                    st.session_state.current_user = l_email
                    st.success("Login successful!")
                    refresh_sessions()
                    st.rerun()
                    
    with tab2:
        with st.form("register_form"):
            r_email = st.text_input("Email")
            r_pwd = st.text_input("Password (min 8 chars)", type="password")
            submitted = st.form_submit_button("Register")
            if submitted:
                res = register(r_email, r_pwd)
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.success("Registration successful! Please login.")
                    
    st.stop()


# --- SIDEBAR ---
with st.sidebar:
    st.title("Agricultural AI")
    st.write(f"Logged in as: **{st.session_state.current_user}**")
    if st.button("Logout", key="logout_btn", use_container_width=True):
        logout_user()
        st.rerun()

    st.markdown("---")
    
    if st.button("➕ New Chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.markdown("### Chats")
    for s_id, session_data in st.session_state.sessions.items():
        col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
        btn_type = "primary" if s_id == st.session_state.active_session_id else "secondary"
        
        with col1:
            if st.button(session_data["title"], key=f"session_{s_id}", type=btn_type, use_container_width=True):
                st.session_state.active_session_id = s_id
                st.rerun()
        with col2:
            with st.popover("✏️", use_container_width=True):
                new_title = st.text_input("New title", value=session_data["title"], key=f"rename_input_{s_id}")
                if st.button("Save", key=f"rename_btn_{s_id}", use_container_width=True):
                    rename_current_session(s_id, new_title)
        with col3:
            if st.button("🗑️", key=f"del_{s_id}", use_container_width=True):
                delete_current_session(s_id)
            
    st.markdown("---")
    st.markdown("### System Status")
    is_connected = check_health()
    if is_connected:
        st.success("Gateway: Connected")
    else:
        st.error("Gateway: Offline")


# --- MAIN APP ---
if not st.session_state.active_session_id or st.session_state.active_session_id not in st.session_state.sessions:
    st.title("Agricultural AI Assistant")
    st.info("Please create or select a chat from the sidebar.")
    st.stop()

active_session = st.session_state.sessions[st.session_state.active_session_id]

st.title("Agricultural AI Assistant")
st.caption(f"Session: {active_session['title']}")

# Display messages
for msg in active_session["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("agents"):
            with st.expander("Agent Activity"):
                st.markdown(msg["agents"], unsafe_allow_html=True)
        if msg.get("debug_info"):
            with st.expander("Show technical details"):
                st.json(msg["debug_info"])

# Chat input and Image Upload
with st.container():
    uploaded_image = st.file_uploader("Attach an image for disease detection (optional)", type=["jpg", "jpeg", "png"], key=st.session_state.uploader_key)

user_input = st.chat_input("Ask a question...")
query = None

if user_input:
    query = user_input
elif "prefill" in st.session_state:
    query = st.session_state.prefill
    del st.session_state.prefill

if query:
    msg_content = query
    if uploaded_image:
        msg_content += "\n\n*(Image attached)*"
        
    active_session["messages"].append({"role": "user", "content": msg_content})
    
    with st.chat_message("user"):
        st.markdown(msg_content)
        
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        response_data = send_chat_message(
            query=query, 
            session_id=st.session_state.active_session_id, 
            token=st.session_state.access_token,
            image_file=uploaded_image
        )
        
        # Reset uploader key to clear the file input for the next message
        st.session_state.uploader_key = str(uuid.uuid4())
        
        if "error" in response_data:
            err_msg = f"Backend error: {response_data['error']}"
            message_placeholder.error(err_msg)
            active_session["messages"].append({"role": "assistant", "content": err_msg})
        else:
            final_response = response_data.get("response", "")
            
            # Streaming effect
            words = final_response.split(" ")
            displayed_text = ""
            for i, word in enumerate(words):
                displayed_text += word + " "
                message_placeholder.markdown(displayed_text + "▌")
                time.sleep(0.01)
            
            message_placeholder.markdown(final_response)
            
            selected_agents = response_data.get("selected_agents", [])
            
            agent_text = "✓ Supervisor Agent<br>"
            if "disease_agent" in selected_agents:
                agent_text += "✓ Disease Agent<br>✓ Disease RAG<br>"
            if "crop_agent" in selected_agents:
                agent_text += "✓ Crop Recommendation Agent<br>"
            if "general_agent" in selected_agents:
                agent_text += "✓ General Agricultural Agent<br>✓ Tavily Search<br>"
                
            agent_html = f"<div class='agent-box'>{agent_text}</div>"
            
            if selected_agents:
                with st.expander("Agent Activity", expanded=True):
                    st.markdown(agent_html, unsafe_allow_html=True)
                    
            debug_info = {
                "Session ID": st.session_state.active_session_id,
                "Selected Agents": selected_agents,
                "Backend Endpoint": "/chat (proxied)"
            }
            with st.expander("Show technical details", expanded=False):
                st.json(debug_info)
                
            active_session["messages"].append({
                "role": "assistant", 
                "content": final_response,
                "agents": agent_html if selected_agents else None,
                "debug_info": debug_info
            })
            
            # Auto-refresh session title if needed
            if active_session['title'] == "New Chat":
                refresh_sessions()
            
    st.rerun()
