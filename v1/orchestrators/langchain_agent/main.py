from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

app = FastAPI()
llm = ChatOpenAI(model="gpt-4o")

class PromptRequest(BaseModel):
    prompt: str

@app.post("/api/langchain")
async def process_prompt(req: PromptRequest):
    response = llm.invoke([HumanMessage(content=req.prompt)])
    return {"result": response.content}
