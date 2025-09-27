import asyncio
from agent import (
    get_agent_components,
    sessions_db,
    agents_db,
    connectors_db,
    PyObjectId,
    ConnectorCreate,
    ConnectorUpdate,
    AgentCreate,
    AgentUpdate
)

def print_line():
    print("="*60)

def list_agents():
    print_line()
    print("Agents:")
    for agent in agents_db.find():
        print(f"{agent['_id']}: {agent['name']} | {agent['description']}")
    print_line()

def select_agent():
    list_agents()
    agent_id = input("Enter agent ID to select for this session (or press Enter to cancel): ").strip()
    if agent_id:
        try:
            return PyObjectId(agent_id)
        except Exception:
            print("Invalid agent ID.")
    return None

def list_connectors():
    print_line()
    print("Connectors:")
    for conn in connectors_db.find():
        print(f"{conn['_id']}: {conn['name']} | Type: {conn['connector_type']}")
    print_line()

def create_agent():
    name = input("Agent name: ")
    description = input("Agent description: ")
    model = input("Model (gpt-3.5-turbo, gpt-4, gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-5): ")
    temperature = float(input("Temperature [0.0-2.0]: "))
    agent = AgentCreate(
        name=name,
        description=description,
        model=model,
        temperature=temperature,
        tools=[],
        connector_ids=[]
    )
    data = agent.model_dump(by_alias=True)
    data["org"] = PyObjectId()
    data["created_at"] = data["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
    result = agents_db.insert_one(data)
    print(f"Created agent with ID: {result.inserted_id}")

def edit_agent():
    list_agents()
    agent_id = input("Enter agent ID to edit: ")
    agent = agents_db.find_one({"_id": PyObjectId(agent_id)})
    if not agent:
        print("Agent not found.")
        return
    name = input(f"New name [{agent['name']}]: ") or agent['name']
    description = input(f"New description [{agent['description']}]: ") or agent['description']
    update = AgentUpdate(name=name, description=description)
    agents_db.update_one({"_id": PyObjectId(agent_id)}, {"$set": update.model_dump(exclude_unset=True)})
    print("Agent updated.")

def delete_agent():
    list_agents()
    agent_id = input("Enter agent ID to delete: ")
    agents_db.delete_one({"_id": PyObjectId(agent_id)})
    print("Agent deleted.")

def create_connector():
    name = input("Connector name: ")
    ctype = input("Connector type (source_pdf, source_uri): ")
    connector = ConnectorCreate(name=name, connector_type=ctype, settings={})
    data = connector.model_dump()
    data["org"] = PyObjectId()
    result = connectors_db.insert_one(data)
    print(f"Created connector with ID: {result.inserted_id}")

def edit_connector():
    list_connectors()
    conn_id = input("Enter connector ID to edit: ")
    conn = connectors_db.find_one({"_id": PyObjectId(conn_id)})
    if not conn:
        print("Connector not found.")
        return
    name = input(f"New name [{conn['name']}]: ") or conn['name']
    update = ConnectorUpdate(name=name)
    connectors_db.update_one({"_id": PyObjectId(conn_id)}, {"$set": update.model_dump(exclude_unset=True)})
    print("Connector updated.")

def delete_connector():
    list_connectors()
    conn_id = input("Enter connector ID to delete: ")
    connectors_db.delete_one({"_id": PyObjectId(conn_id)})
    print("Connector deleted.")

def attach_connector_to_agent():
    list_agents()
    agent_id = input("Agent ID: ")
    list_connectors()
    conn_id = input("Connector ID to attach: ")
    agents_db.update_one(
        {"_id": PyObjectId(agent_id)},
        {"$addToSet": {"connector_ids": PyObjectId(conn_id)}}
    )
    print("Connector attached to agent.")

def detach_connector_from_agent():
    list_agents()
    agent_id = input("Agent ID: ")
    agent = agents_db.find_one({"_id": PyObjectId(agent_id)})
    if not agent or not agent.get("connector_ids"):
        print("Agent has no connectors.")
        return
    print("Agent connectors:", agent["connector_ids"])
    conn_id = input("Connector ID to detach: ")
    agents_db.update_one(
        {"_id": PyObjectId(agent_id)},
        {"$pull": {"connector_ids": PyObjectId(conn_id)}}
    )
    print("Connector detached.")

def upload_file_to_connector():
    list_connectors()
    conn_id = input("Enter connector ID to upload file to: ")
    conn = connectors_db.find_one({"_id": PyObjectId(conn_id)})
    if not conn:
        print("Connector not found.")
        return
    file_path = input("Enter path to PDF or TXT file: ")
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        connectors_db.update_one(
            {"_id": PyObjectId(conn_id)},
            {"$set": {"settings.file_content": content}}
        )
        print("File uploaded and stored in connector settings.")
    except Exception as e:
        print(f"Failed to upload file: {e}")

def list_sessions():
    print_line()
    print("Chat Sessions:")
    for sess in sessions_db.find():
        print(f"Session ID: {sess['session_id']}")
        print(f"Chat History Entries: {len(sess.get('chat_history', []))}")
        print_line()

def view_session():
    list_sessions()
    session_id = input("Enter session ID to view: ")
    session = sessions_db.find_one({"session_id": session_id})
    if not session:
        print("Session not found.")
        return
    chat_history = session.get("chat_history", [])
    print_line()
    for i, msg in enumerate(chat_history):
        print(f"{i}: User: {msg['user']}")
        print(f"   Assistant: {msg['assistant']}")
        print_line()

def delete_session():
    list_sessions()
    session_id = input("Enter session ID to delete: ")
    sessions_db.delete_one({"session_id": session_id})
    print("Session deleted.")

def save_chat_history(session_id, chat_history):
    sessions_db.update_one(
        {"session_id": session_id},
        {"$set": {"chat_history": chat_history}},
        upsert=True
    )

async def chat_session(session_id=None):
    print_line()
    print("Welcome to the CLI Chatbot. Type 'exit' to quit, 'settings' for menu, 'history' to view session history, 'select' to choose an agent.")
    print_line()

    if session_id:
        session = sessions_db.find_one({"session_id": session_id})
        if session:
            chat_history = session.get("chat_history", [])
        else:
            chat_history = []
    else:
        session_id = str(PyObjectId())
        chat_history = []

    agent_id = None

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        elif user_input.lower() == "settings":
            settings_menu()
            continue
        elif user_input.lower() == "history":
            print_line()
            for idx, msg in enumerate(chat_history):
                print(f"{idx}: {msg['user']} -> {msg['assistant'][:100]}...")
            print_line()
            action = input("Type 'regenerate <num>', 'edit <num>', 'delete <num>', or press Enter to continue: ").strip()
            if action.startswith("regenerate"):
                try:
                    _, num = action.split()
                    await regenerate_message(session_id, chat_history, int(num))
                except Exception:
                    print("Invalid command format.")
            elif action.startswith("edit"):
                try:
                    _, num = action.split()
                    await edit_message(session_id, chat_history, int(num))
                except Exception:
                    print("Invalid command format.")
            elif action.startswith("delete"):
                try:
                    _, num = action.split()
                    delete_message(session_id, chat_history, int(num))
                except Exception:
                    print("Invalid command format.")
            continue
        elif user_input.lower() == "select":
            agent_id = select_agent()
            continue

        agent_llm, messages, agent_name, agent_id_actual = await get_agent_components(
            question=user_input,
            organization_id=PyObjectId(),
            chat_history=chat_history,
            agent_id=agent_id
        )

        print(f"[Agent: {agent_name}] ", end="", flush=True)
        answer = ""
        async for chunk in agent_llm.astream(messages):
            content = chunk.content or ""
            answer += content
            print(content, end="", flush=True)
        print("\n")

        chat_history.append({
            "user": user_input,
            "assistant": answer,
            "agent_id": agent_id_actual,
            "agent_name": agent_name
        })

        save_chat_history(session_id, chat_history)

async def regenerate_message(session_id, chat_history, message_num):
    if message_num < 0 or message_num >= len(chat_history):
        print("Invalid message number.")
        return
    truncated_history = chat_history[:message_num]
    original_query = chat_history[message_num]['user']

    agent_llm, messages, agent_name, agent_id_actual = await get_agent_components(
        question=original_query,
        organization_id=PyObjectId(),
        chat_history=truncated_history,
        agent_id=chat_history[message_num]['agent_id']
    )

    print(f"[Agent: {agent_name}] (regenerating) ", end="", flush=True)
    answer = ""
    async for chunk in agent_llm.astream(messages):
        content = chunk.content or ""
        answer += content
        print(content, end="", flush=True)
    print("\n")

    chat_history[message_num]['assistant'] = answer
    save_chat_history(session_id, chat_history)

async def edit_message(session_id, chat_history, message_num):
    if message_num < 0 or message_num >= len(chat_history):
        print("Invalid message number.")
        return
    new_query = input("Enter new message content: ")
    truncated_history = chat_history[:message_num]

    agent_llm, messages, agent_name, agent_id_actual = await get_agent_components(
        question=new_query,
        organization_id=PyObjectId(),
        chat_history=truncated_history,
        agent_id=chat_history[message_num]['agent_id']
    )

    print(f"[Agent: {agent_name}] (editing) ", end="", flush=True)
    answer = ""
    async for chunk in agent_llm.astream(messages):
        content = chunk.content or ""
        answer += content
        print(content, end="", flush=True)
    print("\n")

    chat_history[message_num]['user'] = new_query
    chat_history[message_num]['assistant'] = answer
    save_chat_history(session_id, chat_history)

def delete_message(session_id, chat_history, message_num):
    if message_num < 0 or message_num >= len(chat_history):
        print("Invalid message number.")
        return
    del chat_history[message_num]
    save_chat_history(session_id, chat_history)
    print("Message deleted.")

def settings_menu():
    while True:
        print_line()
        print("Settings Menu:")
        print("1. List Agents")
        print("2. Create Agent")
        print("3. Edit Agent")
        print("4. Delete Agent")
        print("5. List Connectors")
        print("6. Create Connector")
        print("7. Edit Connector")
        print("8. Delete Connector")
        print("9. Attach Connector to Agent")
        print("10. Detach Connector from Agent")
        print("11. Upload File to Connector")
        print("12. List Sessions")
        print("13. View Session")
        print("14. Delete Session")
        print("0. Back to Chat")
        choice = input("Choice: ")
        if choice == "1": list_agents()
        elif choice == "2": create_agent()
        elif choice == "3": edit_agent()
        elif choice == "4": delete_agent()
        elif choice == "5": list_connectors()
        elif choice == "6": create_connector()
        elif choice == "7": edit_connector()
        elif choice == "8": delete_connector()
        elif choice == "9": attach_connector_to_agent()
        elif choice == "10": detach_connector_from_agent()
        elif choice == "11": upload_file_to_connector()
        elif choice == "12": list_sessions()
        elif choice == "13": view_session()
        elif choice == "14": delete_session()
        elif choice == "0":
            break

def main():
    asyncio.run(chat_session())

if __name__ == "__main__":
    main()