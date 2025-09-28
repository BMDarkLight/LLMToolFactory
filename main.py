import asyncio
from agent import get_agent_graph
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

_SESSION = {
    "selected_agent_id": None,
    "history": [],
}

async def list_agents():
    graph, messages, agent_name, agent_id = await get_agent_graph(
        question={"action": "list_agents"},
        organization_id=None,
        chat_history=[],
        agent_id=None
    )
    meta = messages[0]
    agents = meta.get("agents", [])
    for agent in agents:
        if not agent.get("id") and agent.get("_id") is not None:
            agent["id"] = str(agent.get("_id"))
    return agents

async def list_connectors():
    graph, messages, agent_name, agent_id = await get_agent_graph(
        question={"action": "list_connectors"},
        organization_id=None,
        chat_history=[],
        agent_id=None
    )
    meta = messages[0]
    connectors = meta.get("connectors", [])
    return connectors

async def get_agent_by_id(agent_id):
    agents = await list_agents()
    for agent in agents:
        if str(agent.get("id")) == str(agent_id):
            return agent
    return None

async def get_connector_by_id(connector_id):
    connectors = await list_connectors()
    for connector in connectors:
        if str(connector.get("id")) == str(connector_id):
            return connector
    return None

async def settings_menu():
    while True:
        print("\n--- Settings Menu ---")
        print("1. List agents")
        print("2. Add agent")
        print("3. Edit agent")
        print("4. Delete agent")
        print("5. List connectors")
        print("6. Add connector")
        print("7. Edit connector")
        print("8. Delete connector")
        print("9. Link connector to agent")
        print("10. Unlink connector from agent")
        print("0. Back")
        choice = input("Select option: ").strip()
        if choice == "1":
            agents = await list_agents()
            print("\nAgents:")
            for a in agents:
                print(f"  ID: {a.get('id')}, Name: {a.get('name')}, Connectors: {a.get('connectors', [])}")
            await asyncio.sleep(2.5)
        elif choice == "2":
            name = input("Enter new agent name: ").strip()
            _, _, _, _ = await get_agent_graph(
                question={"action": "add_agent", "name": name},
                organization_id=None,
                chat_history=[],
                agent_id=None
            )
            print("Agent added.")
            await asyncio.sleep(2.5)
        elif choice == "3":
            agent_id = input("Enter agent ID to edit: ").strip()
            agent = await get_agent_by_id(agent_id)
            if not agent:
                print("Agent not found.")
                await asyncio.sleep(2.5)
                continue
            new_name = input(f"Enter new name for agent '{agent.get('name')}' (leave blank to keep): ").strip()
            if new_name:
                _, _, _, _ = await get_agent_graph(
                    question={"action": "edit_agent", "agent_id": agent_id, "name": new_name},
                    organization_id=None,
                    chat_history=[],
                    agent_id=None
                )
                print("Agent updated.")
            await asyncio.sleep(2.5)
        elif choice == "4":
            agent_id = input("Enter agent ID to delete: ").strip()
            _, _, _, _ = await get_agent_graph(
                question={"action": "delete_agent", "agent_id": agent_id},
                organization_id=None,
                chat_history=[],
                agent_id=None
            )
            print("Agent deleted.")
            await asyncio.sleep(2.5)
        elif choice == "5":
            connectors = await list_connectors()
            print("\nConnectors:")
            for c in connectors:
                print(f"  ID: {c.get('id')}, Name: {c.get('name')}, Type: {c.get('type')}")
            await asyncio.sleep(2.5)
        elif choice == "6":
            name = input("Enter new connector name: ").strip()
            ctype = input("Enter connector type: ").strip()
            _, _, _, _ = await get_agent_graph(
                question={"action": "add_connector", "name": name, "type": ctype},
                organization_id=None,
                chat_history=[],
                agent_id=None
            )
            print("Connector added.")
            await asyncio.sleep(2.5)
        elif choice == "7":
            connector_id = input("Enter connector ID to edit: ").strip()
            new_name = input("Enter new name (leave blank to keep): ").strip()
            new_type = input("Enter new type (leave blank to keep): ").strip()
            _, _, _, _ = await get_agent_graph(
                question={"action": "edit_connector", "connector_id": connector_id, "name": new_name or None, "type": new_type or None},
                organization_id=None,
                chat_history=[],
                agent_id=None
            )
            print("Connector updated.")
            await asyncio.sleep(2.5)
        elif choice == "8":
            connector_id = input("Enter connector ID to delete: ").strip()
            _, _, _, _ = await get_agent_graph(
                question={"action": "delete_connector", "connector_id": connector_id},
                organization_id=None,
                chat_history=[],
                agent_id=None
            )
            print("Connector deleted.")
            await asyncio.sleep(2.5)
        elif choice == "9":
            agent_id = input("Enter agent ID: ").strip()
            connector_input = input("Enter connector ID or name substring to link: ").strip()
            connectors = await list_connectors()
            connector_id = None
            for c in connectors:
                if str(c.get("id")) == connector_input:
                    connector_id = str(c.get("id"))
                    break
            if connector_id is None:
                matching_connectors = [c for c in connectors if connector_input.lower() in c.get("name", "").lower()]
                if not matching_connectors:
                    print("No matching connectors found.")
                    await asyncio.sleep(2.5)
                    continue
                elif len(matching_connectors) == 1:
                    connector_id = str(matching_connectors[0].get("id"))
                    print(f"Selected connector: {matching_connectors[0].get('name')} (ID: {connector_id})")
                else:
                    print("Multiple connectors match:")
                    for idx, c in enumerate(matching_connectors, 1):
                        print(f"{idx}. {c.get('name')} (ID: {c.get('id')})")
                    sel = input("Select connector number: ").strip()
                    try:
                        sel_idx = int(sel) - 1
                        if 0 <= sel_idx < len(matching_connectors):
                            connector_id = str(matching_connectors[sel_idx].get("id"))
                        else:
                            print("Invalid selection.")
                            await asyncio.sleep(2.5)
                            continue
                    except ValueError:
                        print("Invalid input.")
                        await asyncio.sleep(2.5)
                        continue
            _, _, _, _ = await get_agent_graph(
                question={"action": "link_connector", "agent_id": agent_id, "connector_id": connector_id},
                organization_id=None,
                chat_history=[],
                agent_id=None
            )
            print("Connector linked to agent.")
            await asyncio.sleep(2.5)
        elif choice == "10":
            agent_id = input("Enter agent ID: ").strip()
            connector_input = input("Enter connector ID or name substring to unlink: ").strip()
            connectors = await list_connectors()
            connector_id = None
            for c in connectors:
                if str(c.get("id")) == connector_input:
                    connector_id = str(c.get("id"))
                    break
            if connector_id is None:
                matching_connectors = [c for c in connectors if connector_input.lower() in c.get("name", "").lower()]
                if not matching_connectors:
                    print("No matching connectors found.")
                    await asyncio.sleep(2.5)
                    continue
                elif len(matching_connectors) == 1:
                    connector_id = str(matching_connectors[0].get("id"))
                    print(f"Selected connector: {matching_connectors[0].get('name')} (ID: {connector_id})")
                else:
                    print("Multiple connectors match:")
                    for idx, c in enumerate(matching_connectors, 1):
                        print(f"{idx}. {c.get('name')} (ID: {c.get('id')})")
                    sel = input("Select connector number: ").strip()
                    try:
                        sel_idx = int(sel) - 1
                        if 0 <= sel_idx < len(matching_connectors):
                            connector_id = str(matching_connectors[sel_idx].get("id"))
                        else:
                            print("Invalid selection.")
                            await asyncio.sleep(2.5)
                            continue
                    except ValueError:
                        print("Invalid input.")
                        await asyncio.sleep(2.5)
                        continue
            _, _, _, _ = await get_agent_graph(
                question={"action": "unlink_connector", "agent_id": agent_id, "connector_id": connector_id},
                organization_id=None,
                chat_history=[],
                agent_id=None
            )
            print("Connector unlinked from agent.")
            await asyncio.sleep(2.5)
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            await asyncio.sleep(2.5)

def print_main_menu(selected_agent_id):
    print("\n=== LLMToolFactory CLI ===")
    print("Type your message to chat.")
    print("Commands:")
    print("  settings      - Open settings menu")
    print("  select        - Select agent")
    print("  revoke        - Unselect agent")
    print("  history       - Show chat history")
    print("  exit/quit     - Exit")
    if selected_agent_id:
        print(f"Current agent: {selected_agent_id}")
    else:
        print("No agent selected.")

async def select_agent():
    agents = await list_agents()
    if not agents:
        print("No agents available.")
        return None
    print("\nAvailable agents:")
    for a in agents:
        print(f"  ID: {a.get('id')}, Name: {a.get('name')}")
    agent_input = input("Enter agent ID or name substring to select: ").strip()
    for a in agents:
        if str(a.get("id")) == agent_input:
            print(f"Agent {agent_input} selected.")
            return agent_input
    matching_agents = [a for a in agents if agent_input.lower() in a.get("name", "").lower()]
    if not matching_agents:
        print("Agent not found.")
        return None
    elif len(matching_agents) == 1:
        agent_id = str(matching_agents[0].get("id"))
        print(f"Selected agent: {matching_agents[0].get('name')} (ID: {agent_id})")
        return agent_id
    else:
        print("Multiple agents match:")
        for idx, a in enumerate(matching_agents, 1):
            print(f"{idx}. {a.get('name')} (ID: {a.get('id')})")
        sel = input("Select agent number: ").strip()
        try:
            sel_idx = int(sel) - 1
            if 0 <= sel_idx < len(matching_agents):
                agent_id = str(matching_agents[sel_idx].get("id"))
                return agent_id
            else:
                print("Invalid selection.")
                return None
        except ValueError:
            print("Invalid input.")
            return None

async def chat_session():
    session_id = None
    agent_id = _SESSION.get("selected_agent_id")
    chat_history = []
    print_main_menu(agent_id)
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        cmd = user_input.lower()
        if cmd in {"exit", "quit"}:
            break
        elif cmd == "settings":
            await settings_menu()
            print_main_menu(agent_id)
            continue
        elif cmd == "history":
            print("\n--- Chat History ---")
            for h in chat_history:
                print(f"You: {h['user']}")
                print(f"{h['assistant']}")
            continue
        elif cmd == "select":
            agent_id_new = await select_agent()
            if agent_id_new:
                agent_id = agent_id_new
                _SESSION["selected_agent_id"] = agent_id
            continue
        elif cmd == "revoke":
            agent_id = None
            _SESSION["selected_agent_id"] = None
            print("Agent selection revoked.")
            continue
        elif cmd == "menu":
            print_main_menu(agent_id)
            continue

        question = user_input

        graph, messages, agent_name, agent_id_actual = await get_agent_graph(
            question=question,
            organization_id=None,
            chat_history=chat_history,
            agent_id=agent_id,
        )
        if agent_id is None and agent_id_actual:
            agent_id = str(agent_id_actual)
            _SESSION["selected_agent_id"] = agent_id

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
        print("\n")
        chat_history.append({"user": user_input, "assistant": answer})

def main():
    asyncio.run(chat_session())

if __name__ == "__main__":
    main()