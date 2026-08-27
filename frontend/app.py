import streamlit as st
import uuid
import time
from api_client import send_chat_message, check_health

st.set_page_config(page_title="Agricultural AI", layout="wide")

# Custom CSS for cleaner UI
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
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())

def create_new_session():
    new_id = str(uuid.uuid4())
    st.session_state.sessions[new_id] = {
        "title": "New Chat",
        "messages": []
    }
    st.session_state.active_session_id = new_id

if st.session_state.active_session_id is None:
    create_new_session()

# --- SIDEBAR ---
with st.sidebar:
    st.title("Agricultural AI")
    if st.button("➕ New Chat", use_container_width=True):
        create_new_session()
        st.rerun()

    st.markdown("### Chats")
    
    # Display in reverse order (newest first)
    for sess_id in list(st.session_state.sessions.keys())[::-1]:
        sess_data = st.session_state.sessions[sess_id]
        if st.button(sess_data["title"], key=f"btn_{sess_id}", use_container_width=True):
            st.session_state.active_session_id = sess_id
            st.rerun()
            
    st.markdown("---")
    st.markdown("### System Status")
    is_connected = check_health()
    if is_connected:
        st.success("Backend: Connected")
    else:
        st.error("Backend: Offline")

# --- MAIN APP ---
active_session = st.session_state.sessions[st.session_state.active_session_id]

st.title("Agricultural AI Assistant")
st.caption("AI-powered crop recommendation, disease assistance and agricultural reasoning")

# Welcome screen if empty
if not active_session["messages"]:
    st.markdown("### Ask questions about:")
    st.markdown("- Crop recommendations\n- Plant diseases\n- Disease treatment and prevention\n- General agricultural questions")
    
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("What crop should I grow with these soil conditions?"):
            st.session_state.prefill = "What crop should I grow with these soil conditions?"
            st.rerun()
    with col2:
        if st.button("What are the symptoms of tomato early blight?"):
            st.session_state.prefill = "What are the symptoms of tomato early blight?"
            st.rerun()

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
    if active_session["title"] == "New Chat":
        active_session["title"] = query[:25] + "..." if len(query) > 25 else query
        
    msg_content = query
    if uploaded_image:
        msg_content += "\n\n*(Image attached)*"
        
    active_session["messages"].append({"role": "user", "content": msg_content})
    
    with st.chat_message("user"):
        st.markdown(msg_content)
        
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        response_data = send_chat_message(query, st.session_state.active_session_id, uploaded_image)
        
        # Reset uploader key to clear the file input for the next message
        st.session_state.uploader_key = str(uuid.uuid4())
        
        if "error" in response_data:
            err_msg = "Backend unavailable. Please start the FastAPI server."
            message_placeholder.error(err_msg)
            print(f"Backend error: {response_data['error']}")
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
                "Backend Endpoint": "/chat"
            }
            with st.expander("Show technical details", expanded=False):
                st.json(debug_info)
                
            active_session["messages"].append({
                "role": "assistant", 
                "content": final_response,
                "agents": agent_html if selected_agents else None,
                "debug_info": debug_info
            })
            
    st.rerun()
