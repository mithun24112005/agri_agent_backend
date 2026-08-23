from pydantic import BaseModel
from typing import Optional

class ChatResponse(BaseModel):
    status: str
    query: str
    response: str
    error: Optional[str] = None
