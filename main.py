import asyncio
from agent import get_agent_graph
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


async def chat_session(session_id=None, agent_id=None):
    """Simple CLI chat loop with a LangGraph ReAct agent."""

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        # --- Build agent graph ---
        graph, messages, agent_name, agent_id_actual = await get_agent_graph(
            question=user_input,
            organization_id=None,  # can be filled if you need real orgs
            chat_history=[],
            agent_id=agent_id,
        )

        # --- Persist agent id if first run ---
        if agent_id is None and agent_id_actual:
            agent_id = str(agent_id_actual)

        # --- Stream assistant output ---
        print(f"[Agent: {agent_name}] ", end="", flush=True)
        answer = ""
        async for step in graph.astream({"messages": messages}, stream_mode="values"):
            last_msg = step["messages"][-1]
            if hasattr(last_msg, "tool_calls"):
                print(f"\n[Tool Calls]: {last_msg.tool_calls}")
            content = getattr(last_msg, "content", None)
            if content:
                answer += content
                print(content, end="", flush=True)
        print("\n")  # newline after answer


def main():
    asyncio.run(chat_session(agent_id="68d818ec1fa432ab6c396f7c"))


if __name__ == "__main__":
    main()