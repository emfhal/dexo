from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from langchain_core.messages import HumanMessage

from .agent import agent_executor

app = FastAPI(title="Cursor-like LangChain Agent")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "default_user"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    clarification_required: bool = False

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    
    inputs = {
        "messages": [HumanMessage(content=req.message)],
        "session_id": session_id,
        "user_id": req.user_id
    }
    
    try:
        # Run the src graph
        result = agent_executor.invoke(inputs)
        
        last_message = result['messages'][-1]
        response_text = last_message.content
        clarification_required = False
        
        # Check if the execution halted due to follow_questions
        # In our implementation, this happens if the last message had tool_calls but we hit END
        if getattr(last_message, 'tool_calls', None):
            for call in last_message.tool_calls:
                if call['name'] == 'follow_questions':
                    clarification_required = True
                    # Extract the question from the arguments
                    args = call.get('args', {})
                    question = args.get('question', 'Clarification needed.')
                    opts = args.get('options', [])
                    response_text = f"CLARIFICATION REQUIRED: {question}"
                    if opts:
                        response_text += f"\nOptions: {', '.join(opts)}"
                    break

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            clarification_required=clarification_required
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
