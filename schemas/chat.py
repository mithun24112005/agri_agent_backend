from pydantic import BaseModel
from typing import Optional

class ChatResponse(BaseModel):
    status: str
    query: str
    response: str
    session_id: Optional[str] = None
    error: Optional[str] = None
