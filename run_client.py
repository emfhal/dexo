import argparse
import asyncio
import json
import uuid

from langchain_core.messages import HumanMessage

from src.config import get_settings
from src.context.loader import AdvancedContextLoader
from src.graph.builder import build_graph
from src.graph.state import AgentState
from src.memory.manager import MemoryManager
from src.security.jwt import JWTService


async def main():
    print(r"""
  _____   __   __
 |  __ \  \ \ / /
 | |  | |  \ V / 
 | |  | |   > <  
 | |__| |  / . \ 
 |_____/  /_/ \_\
    """)
    parser = argparse.ArgumentParser(description="Dexo CLI Client")
    parser.add_argument("prompt", type=str, help="The prompt to send to the agent")
    parser.add_argument("--thread-id", type=str, default=str(uuid.uuid4()), help="Thread ID for the conversation")
    args = parser.parse_args()

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

        jwt_svc = JWTService(cfg.security)
        token = jwt_svc.create_access_token("admin_user", roles=["admin", "src:write", "src:read"])

        state = AgentState(
            messages=[HumanMessage(content=args.prompt)],
            thread_id=args.thread_id,
            raw_token=token,
            max_iterations=10,
        )

        config = {"configurable": {"thread_id": args.thread_id}}
        print(f"Starting agent in thread: {args.thread_id}\n")

        async def stream_graph(state_input):
            async for event in graph.astream(state_input, config=config, stream_mode="updates"):
                if isinstance(event, dict):
                    for node_name, node_state in event.items():
                        if isinstance(node_state, dict):
                            messages = node_state.get("messages", [])
                            if not isinstance(messages, list):
                                messages = [messages]
                            for m in messages:
                                if hasattr(m, "content") and m.content:
                                    print(f"[{node_name}] {m.__class__.__name__}: {m.content}")
                                if hasattr(m, "tool_calls") and m.tool_calls:
                                    print(f"[{node_name}] Tool calls: {json.dumps(m.tool_calls)}")

        await stream_graph(state)

        # Check if interrupted for tool approval
        curr_state = await graph.aget_state(config)
        while curr_state.tasks:
            print("\nGraph interrupted. Approving tool execution...")
            await stream_graph({"resume_value": "approved"})
            curr_state = await graph.aget_state(config)

    await memory.shutdown()
    print("\nDone")

if __name__ == "__main__":
    asyncio.run(main())
