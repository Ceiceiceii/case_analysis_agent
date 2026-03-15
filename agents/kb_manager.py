"""KB Manager agent node using create_react_agent."""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from config import (
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    MINIMAX_API_KEY,
    MINIMAX_BASE_URL,
    MINIMAX_MODEL,
)
from prompts import KB_MANAGER_SYSTEM_PROMPT
from state.project_state import ProjectState
from tools.kb_tools import (
    approve_enrichment_tool,
    create_kb_tool,
    enrich_kb_tool,
    get_enrichment_logs_tool,
    ingest_document_tool,
    list_kbs_tool,
    search_kb_tool,
    set_kb_keywords_tool,
)

_KB_TOOLS = [
    create_kb_tool,
    list_kbs_tool,
    ingest_document_tool,
    search_kb_tool,
    set_kb_keywords_tool,
    enrich_kb_tool,
    approve_enrichment_tool,
    get_enrichment_logs_tool,
]


def _get_llm():
    return ChatOpenAI(
        model=MINIMAX_MODEL,
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )


def kb_manager_node(state: ProjectState) -> Command:
    """KB Manager agent node."""
    conversation = state.get("conversation_history", [])
    last_user_msg = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    kb_ids = state.get("selected_kb_ids", [])
    project_id = state.get("project_id", "")
    context = f"Current project: {project_id}. Selected KB IDs: {kb_ids}."

    llm = _get_llm()
    agent = create_react_agent(llm, _KB_TOOLS, prompt=KB_MANAGER_SYSTEM_PROMPT)

    try:
        result = agent.invoke({
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": last_user_msg or "List available knowledge bases."},
            ]
        })
        last_msg = result["messages"][-1]
        response_content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    except Exception as e:
        response_content = f"KB Manager error: {e}"

    return Command(
        goto="orchestrator",
        update={
            "agent_message": response_content,
            "next_node": "orchestrator",
            "conversation_history": [{
                "role": "assistant",
                "content": f"[kb_manager] {response_content}",
                "agent": "kb_manager",
            }],
        },
    )
