from typing import TypedDict, Annotated, Sequence, Union, Literal
import json
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from .tools import read_skill, run_command, fetch_website, follow_questions, invoke_subagent
from .memory import MultiTierMemoryManager
from .customizations import CustomizationsLoader

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    session_id: str
    user_id: str

# Initialize Managers
memory_manager = MultiTierMemoryManager()

# We will assume workspace is the parent directory of orchestrators for demo purposes
workspace_root = "/Users/emmanuelf/2026/agents"
customizations_loader = CustomizationsLoader(workspace_root)

# Load custom components
rules_prompt = customizations_loader.load_rules()
local_skills = customizations_loader.load_local_skills()
mcp_tools = customizations_loader.load_mcp_tools()

# Define Tools
base_tools = [
    read_skill, 
    run_command, 
    fetch_website, 
    follow_questions, 
    invoke_subagent
]
all_tools = base_tools + local_skills + mcp_tools
tool_executor = ToolExecutor(all_tools)

# Initialize Model
model = ChatOpenAI(temperature=0, model="gpt-4o")
model_with_tools = model.bind_tools(all_tools)

# Define the nodes
def call_model(state: AgentState):
    messages = state['messages']
    
    # We dynamically construct the system prompt based on the last message
    last_user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_query = msg.content
            break
            
    # Inject Tier 2 & Tier 3 memories dynamically
    memory_injection = memory_manager.get_system_prompt_injections(
        state['session_id'], 
        state['user_id'], 
        last_user_query
    )
    
    # Base System Prompt with rules
    system_prompt = f"""You are a highly capable agentic coding assistant similar to Cursor.
You have access to a variety of tools.
{rules_prompt}
{memory_injection}
"""
    
    # Ensure system prompt is first
    sys_msg = SystemMessage(content=system_prompt)
    
    # If the first message is already a system message, replace it, else prepend
    if len(messages) > 0 and isinstance(messages[0], SystemMessage):
        messages = [sys_msg] + list(messages[1:])
    else:
        messages = [sys_msg] + list(messages)
        
    response = model_with_tools.invoke(messages)
    
    # Handle the interrupt circuit breaker manually for follow_questions
    if isinstance(response, AIMessage) and response.tool_calls:
        for call in response.tool_calls:
            if call['name'] == 'follow_questions':
                # Return the message, but graph will intercept in 'should_continue'
                pass
                
    return {"messages": [response]}


def call_tools(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    
    tool_messages = []
    
    for tool_call in last_message.tool_calls:
        # Construct a ToolInvocation from the tool_call
        action = ToolInvocation(
            tool=tool_call["name"],
            tool_input=tool_call["args"],
        )
        
        # We call the tool_executor and get back a response
        response = tool_executor.invoke(action)
        
        # If follow_questions was called, the response has __INTERRUPT__
        # In a real LangGraph setup, we'd use the built-in interrupt() or breakpoint features
        # For simplicity, we just pass the response back as a ToolMessage
        
        tool_messages.append(ToolMessage(
            content=str(response), 
            name=action.tool, 
            tool_call_id=tool_call["id"]
        ))
        
    return {"messages": tool_messages}

def should_continue(state: AgentState) -> Literal["continue", "end"]:
    messages = state['messages']
    last_message = messages[-1]
    
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "end"
        
    # Check if a circuit breaker tool was called
    for call in last_message.tool_calls:
        if call['name'] == 'follow_questions':
            # Halt and return to user immediately
            return "end"
            
    # Otherwise continue execution
    return "continue"

# Define the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("src", call_model)
workflow.add_node("action", call_tools)

# Set the entrypoint
workflow.add_edge(START, "src")

# Add conditional edges
workflow.add_conditional_edges(
    "src",
    should_continue,
    {
        "continue": "action",
        "end": END
    }
)

# Add normal edge from action back to src
workflow.add_edge("action", "src")

# Compile the graph
agent_executor = workflow.compile()
