from fastapi import APIRouter, HTTPException
from groq import Groq
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.core.config import settings

router = APIRouter()

CHAT_SYSTEM_PROMPT = """You are an expert software engineer and code security analyst.
You help developers understand code issues, vulnerabilities, and how to fix them.
Be concise, practical, and specific. Format your responses with clear sections when helpful.
If you are given context about a specific issue, focus your response on that issue."""

@router.post("/chat", response_model=ChatResponse)
async def chat(data: ChatRequest):
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)

    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]

    # Inject issue context if provided
    if data.context.strip():
        messages.append({
            "role": "user",
            "content": f"Context about the current issue:\n{data.context}"
        })
        messages.append({
            "role": "assistant",
            "content": "I've reviewed the issue context. How can I help you with it?"
        })

    messages.append({"role": "user", "content": data.message})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content.strip()
        return ChatResponse(reply=reply)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")
