from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request, Depends, Header
from langchain_core.messages import HumanMessage
from typing import Optional
from services.disease_detection.exceptions import (
    HFNetworkError,
    HFTimeoutError,
    HFAuthenticationError,
    HFServiceError,
    InvalidImageError,
    DiseaseDetectionError
)
import os
from services.image_storage import image_as_data_url, remove_stored_image, save_uploaded_image

async def verify_internal_api_key(x_internal_api_key: str = Header(...)):
    expected = os.getenv("INTERNAL_API_SECRET")
    if not expected or x_internal_api_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid internal API key")

chat_router = APIRouter(dependencies=[Depends(verify_internal_api_key)])

@chat_router.post("/chat", tags=["Chat"])
async def chat_endpoint(
    request: Request,
    query: str = Form(...),
    session_id: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """
    Handle user queries for the agriculture assistant.
    Can accept a text query and an optional image file (e.g., for disease detection).
    """
    graph = request.app.state.graph
    session_id = session_id.strip()
    if not session_id or len(session_id) > 255:
        raise HTTPException(status_code=400, detail="Invalid session_id.")

    image_attachment = None
    completed = False
    print(f"Received query: {query}")
    print(f"Received file object: {file}")
    
    if file is not None and file.filename:
        print(f"File name: {file.filename}, File content type: {file.content_type}")
        try:
            image_attachment = await save_uploaded_image(file)
            print(f"Saved image to durable storage: {image_attachment['path']}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            print(f"Error saving image: {e}")
            raise HTTPException(status_code=500, detail="Failed to store the uploaded image.") from e

    try:
        # Run the LangGraph application
        human_message = HumanMessage(
            content=query,
            additional_kwargs={"image_attachment": image_attachment} if image_attachment else {},
        )
        initial_state = {
            "user_query": query,
            "has_image": image_attachment is not None,
            "messages": [human_message]
        }
        
        config = {
            "configurable": {
                "thread_id": session_id,
                "image_path": image_attachment["path"] if image_attachment else None
            }
        }
        
        result = await graph.ainvoke(initial_state, config=config)
        
        final_response = result.get("final_response", "Failed to generate a response.")
        
        response = {
            "status": "success",
            "query": query,
            "response": final_response,
            "session_id": session_id,
            "selected_agents": result.get("selected_agents", []),
            "agent_responses": result.get("agent_responses", {})
        }
        completed = True
        return response
    except HTTPException:
        raise
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HFAuthenticationError as e:
        raise HTTPException(status_code=500, detail=f"Configuration Error: {e}")
    except (HFNetworkError, HFTimeoutError, HFServiceError) as e:
        raise HTTPException(status_code=502, detail=f"External Detection Service Error: {e}")
    except DiseaseDetectionError as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {e}")
    finally:
        if not completed and image_attachment:
            remove_stored_image(image_attachment.get("path"))

@chat_router.get("/chat/{session_id}", tags=["Chat"])
async def get_chat_history(session_id: str, request: Request):
    """
    Retrieve message history for a given session.
    """
    try:
        session_id = session_id.strip()
        if not session_id:
            raise HTTPException(status_code=400, detail="Invalid session_id.")
            
        graph = request.app.state.graph
        config = {"configurable": {"thread_id": session_id}}
        
        state_snapshot = await graph.aget_state(config)
        
        if not state_snapshot or not state_snapshot.values:
            return {"session_id": session_id, "messages": []}
            
        messages = state_snapshot.values.get("messages", [])
        
        formatted_messages = []
        for msg in messages:
            # Check msg type attribute or class name
            msg_type = getattr(msg, "type", None)
            if not msg_type:
                msg_type = "human" if "HumanMessage" in str(type(msg)) else "ai"
                
            if msg_type == "human":
                formatted = {"role": "user", "content": msg.content}
                attachment = getattr(msg, "additional_kwargs", {}).get("image_attachment")
                if attachment:
                    image = image_as_data_url(attachment.get("path", ""), attachment.get("content_type", ""))
                    if image:
                        formatted["image"] = {
                            "data_url": image,
                            "filename": attachment.get("filename", "image"),
                            "content_type": attachment.get("content_type", "image/jpeg"),
                            "size": attachment.get("size", 0),
                        }
                formatted_messages.append(formatted)
            elif msg_type == "ai":
                formatted_messages.append({"role": "assistant", "content": msg.content})
                
        return {"session_id": session_id, "messages": formatted_messages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {e}")
