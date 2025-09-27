from langchain_openai import ChatOpenAI
from langsmith import traceable
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.tools import Tool
from typing import TypedDict, Literal, List, Optional, Dict, Any
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Tuple
from bson import ObjectId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import Tool

import os
import re

from tools.pdf_source import get_pdf_source_tool
from tools.uri_source import get_uri_source_tool

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).llmtf.sessions
agents_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).llmtf.agents
connectors_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).llmtf.connectors

Connectors = Literal[
    "source_pdf",
    "source_uri"
]

Models = Literal[
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-5"
]

def _clean_tool_name(name: str, prefix: str) -> str:
    s = re.sub(r'\W+', '_', name)
    return f"{prefix}_{s}".lower()

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        def validate_object_id(v):
            if isinstance(v, ObjectId):
                return v
            if ObjectId.is_valid(v):
                return ObjectId(v)
            raise ValueError("Invalid ObjectId")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.no_info_after_validator_function(
                validate_object_id, core_schema.str_schema()
            ),
            python_schema=core_schema.no_info_plain_validator_function(
                validate_object_id
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

class Connector(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    connector_type: Connectors
    settings: Dict[str, Any]
    org: PyObjectId

class ConnectorCreate(BaseModel):
    name: str
    connector_type: Connectors
    settings: Dict[str, Any]

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class Agent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: str
    org: PyObjectId
    model: Models
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    tools: List[Tool] = []
    connector_ids: List[PyObjectId] = Field(default_factory=list)
    created_at: str
    updated_at: str

class AgentCreate(BaseModel):
    name: str
    description: str
    model: Models
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    tools: List[Tool] = []
    connector_ids: List[PyObjectId] = Field(default_factory=list)

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[Models] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    tools: Optional[List[Tool]] = None
    connector_ids: Optional[List[PyObjectId]] = None

class ChatHistoryEntry(TypedDict):
    user: str
    assistant: str
    agent_id: Optional[str]
    agent_name: str

class AgentState(TypedDict, total=False):
    question: str
    chat_history: Optional[List[ChatHistoryEntry]]
    agent_id: Optional[str]
    agent_name: str
    answer: str

@traceable
async def get_agent_graph(
    question: str,
    organization_id: ObjectId,
    chat_history: Optional[List[dict]] = None,
    agent_id: Optional[str] = None,
) -> Tuple:
    """Return a LangGraph ReAct agent graph + metadata for execution."""
    question = question.strip()
    chat_history = chat_history or []

    # --- Step 1: Select agent (either explicit ID or via router) ---
    print(f"Selecting agent for question: {agent_id}")
    if agent_id:
        selected_agent = agents_db.find_one(
            {"_id": ObjectId(agent_id)}
        )
    else:
        agents = list(agents_db.find({"org": organization_id}))
        selected_agent = None
        if agents:
            agent_descriptions = "\n".join(
                [f"- {agent['name']}: {agent['description']}" for agent in agents]
            )
            router_prompt = [
                SystemMessage(
                    content="Route the user's question to the most appropriate agent.\n"
                            f"Available Agents:\n{agent_descriptions}"
                ),
                HumanMessage(content=question),
            ]
            router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            selected_agent_name = (await router_llm.ainvoke(router_prompt)).content.strip()
            selected_agent = next((a for a in agents if a["name"] == selected_agent_name), None)

    # --- Step 2: Collect tools ---
    tools: List[Tool] = []
    if selected_agent:
        tools.extend(selected_agent.get("tools", []))
        tool_factory_map = {
            "source_pdf": get_pdf_source_tool,
            "source_uri": get_uri_source_tool
        }
        connector_ids = selected_agent.get("connector_ids", [])
        if connector_ids:
            agent_connectors = list(connectors_db.find({"_id": {"$in": connector_ids}}))
            for connector in agent_connectors:
                factory = tool_factory_map.get(connector.get("connector_type"))
                if not factory:
                    continue
                tool_name = f"{connector['connector_type']}_{connector['name']}".replace(" ", "_").lower()
                tools.append(factory(settings=connector["settings"], name=tool_name))

        for t in tools:
            print(f"Using tool: {t.name} - {t.description}")

        llm = ChatOpenAI(
            model=selected_agent["model"],
            temperature=selected_agent.get("temperature", 0.7),
            streaming=True,
            max_retries=3,
        )
        system_prompt = selected_agent["description"]
        final_agent_id, final_agent_name = selected_agent["_id"], selected_agent["name"]
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_retries=3)
        system_prompt = "You are a helpful general-purpose assistant."
        final_agent_id, final_agent_name = None, "Generalist"

    # --- Step 3: Create graph ---
    graph = create_react_agent(llm, tools)

    # --- Step 4: Build message history ---
    messages = [SystemMessage(content=system_prompt)]
    for entry in chat_history:
        messages.append(HumanMessage(content=entry["user"]))
        messages.append(AIMessage(content=entry["assistant"]))
    messages.append(HumanMessage(content=question))

    return graph, messages, final_agent_name, str(final_agent_id) if final_agent_id else None