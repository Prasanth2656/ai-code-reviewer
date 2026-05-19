from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    context: str = ""   # Optional issue context

class ChatResponse(BaseModel):
    reply: str
