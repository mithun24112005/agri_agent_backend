import requests
import json
import os

# Now point to the Express Gateway
BACKEND_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:3001/api")

def _get_headers(token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def login(email, password):
    url = f"{BACKEND_URL}/auth/login"
    try:
        res = requests.post(url, json={"email": email, "password": password}, timeout=10)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        if e.response is not None:
            return {"error": e.response.json().get("error", {}).get("message", "Login failed")}
        return {"error": str(e)}

def register(email, password):
    url = f"{BACKEND_URL}/auth/register"
    try:
        res = requests.post(url, json={"email": email, "password": password}, timeout=10)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        if e.response is not None:
            return {"error": e.response.json().get("error", {}).get("message", "Registration failed")}
        return {"error": str(e)}

def fetch_sessions(token):
    url = f"{BACKEND_URL}/sessions"
    try:
        res = requests.get(url, headers=_get_headers(token), timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return []

def create_session(token, title="New Chat"):
    url = f"{BACKEND_URL}/sessions"
    try:
        res = requests.post(url, json={"title": title}, headers=_get_headers(token), timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def rename_session(session_id: str, token: str, title: str):
    url = f"{BACKEND_URL}/sessions/{session_id}"
    try:
        res = requests.patch(url, json={"title": title}, headers=_get_headers(token), timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def delete_session(session_id: str, token: str):
    url = f"{BACKEND_URL}/sessions/{session_id}"
    try:
        res = requests.delete(url, headers=_get_headers(token), timeout=10)
        res.raise_for_status()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}

def send_chat_message(query: str, session_id: str, token: str, image_file=None):
    url = f"{BACKEND_URL}/chat"
    data = {
        "query": query,
        "session_id": session_id
    }
    files = None
    if image_file:
        files = {"file": (image_file.name, image_file.getvalue(), image_file.type)}
        
    try:
        response = requests.post(url, data=data, files=files, headers=_get_headers(token), timeout=65)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if e.response is not None:
            return {"error": e.response.json().get("error", {}).get("message", "Chat request failed")}
        return {"error": str(e)}

def fetch_chat_history(session_id: str, token: str):
    url = f"{BACKEND_URL}/chat/{session_id}"
    try:
        res = requests.get(url, headers=_get_headers(token), timeout=10)
        res.raise_for_status()
        return res.json().get("messages", [])
    except Exception as e:
        return []

def check_health():
    # Let's check the Express gateway health
    try:
        response = requests.get(f"http://127.0.0.1:3001/health", timeout=5)
        return response.status_code == 200
    except:
        return False
