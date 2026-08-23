from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional

chat_router = APIRouter()

@chat_router.post("/chat", tags=["Chat"])
async def chat_endpoint(
    query: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """
    Handle user queries for the agriculture assistant.
    Can accept a text query and an optional image file (e.g., for disease detection).
    """
    import os
    import shutil
    import tempfile
    from graph.main_graph import main_app

    image_path = None
    print(f"Received query: {query}")
    print(f"Received file object: {file}")
    
    if file is not None and file.filename:
        print(f"File name: {file.filename}, File content type: {file.content_type}")
        try:
            # Create a temporary file to save the uploaded image
            fd, temp_path = tempfile.mkstemp(suffix=".jpg")
            with os.fdopen(fd, "wb") as f:
                shutil.copyfileobj(file.file, f)
            image_path = temp_path
            print(f"Saved image to {image_path}")
        except Exception as e:
            print(f"Error saving image: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process image: {e}")

    try:
        # Run the LangGraph application
        initial_state = {
            "user_query": query,
            "image_path": image_path
        }
        
        result = await main_app.ainvoke(initial_state)
        
        final_response = result.get("final_response", "Failed to generate a response.")
        
        return {
            "status": "success",
            "query": query,
            "response": final_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {e}")
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

