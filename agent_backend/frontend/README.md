# Agricultural AI Streamlit Frontend

This is a temporary demonstration UI for the Agricultural Multi-Agent System. 

## Features
- Clean, ChatGPT-like interface
- Multiple chat sessions with memory
- Displays which agents were called (Supervisor, Disease, Crop, General)
- Faked word-by-word streaming effect for smooth UX

## How to run
1. Start the FastAPI backend from the root directory:
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8001
   ```
2. Run Streamlit from the root directory:
   ```bash
   streamlit run frontend/app.py
   ```
