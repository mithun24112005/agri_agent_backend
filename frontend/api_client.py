import requests
import json

BACKEND_URL = "http://127.0.0.1:8001"

def send_chat_message(query: str, session_id: str, image_file=None):
    url = f"{BACKEND_URL}/chat"
    data = {
        "query": query,
        "session_id": session_id
    }
    files = None
    if image_file:
        files = {"file": (image_file.name, image_file.getvalue(), image_file.type)}
        
    try:
        response = requests.post(url, data=data, files=files, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def check_health():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False
