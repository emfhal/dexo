import asyncio
from src.config import get_settings
from src.context.loader import AdvancedContextLoader
from src.graph.builder import build_graph
from src.memory.manager import MemoryManager
from src.graph.state import AgentState
from langchain_core.messages import HumanMessage
import uuid
import json

async def main():
    cfg = get_settings()
    memory = MemoryManager(cfg.database, cfg.memory)
    await memory.startup()
    
    loader = AdvancedContextLoader(cfg.assets, memory)
    await loader.warm_up()
    
    async with memory.postgres.checkpointer() as checkpointer:
        workflow = build_graph(memory, loader)
        graph = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["tools"],
        )
        
        from src.security.jwt import JWTService
        jwt_svc = JWTService(cfg.security)
        token = jwt_svc.create_access_token("admin_user", roles=["admin", "src:write", "src:read"])

        thread_id = str(uuid.uuid4())
        state = AgentState(
            messages=[HumanMessage(content="Use a browser to access https://www.n12.co.il/, extract all titles, and save them to a json file named titles.json in the current directory. Do not ask for permissions, just do it.")],
            thread_id=thread_id,
            raw_token=token,
            max_iterations=10,
        )
        
        config = {"configurable": {"thread_id": thread_id}}
        print("Starting agent...")
        result = await graph.ainvoke(state, config=config)
        
        def print_messages(messages):
            for m in messages:
                if hasattr(m, "content") and m.content:
                    print(f"{m.__class__.__name__}: {m.content}")
                if hasattr(m, "tool_calls") and m.tool_calls:
                    print(f"Tool calls: {json.dumps(m.tool_calls)}")

        print_messages(result.get("messages", []))

        # Check if interrupted for tool approval
        curr_state = await graph.aget_state(config)
        while curr_state.tasks:
            print("Graph interrupted. Approving tool execution...")
            result = await graph.ainvoke({"resume_value": "approved"}, config=config)
            print_messages(result.get("messages", []))
            curr_state = await graph.aget_state(config)
            
    await memory.shutdown()
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
