from fastapi import FastAPI
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

@app.post("/api/crewai")
async def run_crew(req: PromptRequest):
    researcher = Agent(
        role='Senior Research Analyst',
        goal='Uncover context',
        backstory='Expert analyst.',
        verbose=True,
        allow_delegation=False
    )
    
    task = Task(
        description=req.prompt,
        expected_output='A comprehensive answer based on research.',
        agent=researcher
    )

    crew = Crew(
        agents=[researcher],
        tasks=[task],
        process=Process.sequential
    )
    
    result = crew.kickoff()
    
    # Check if result has raw attribute (CrewAI string representation of output)
    result_str = getattr(result, "raw", str(result))
    return {"result": result_str}
