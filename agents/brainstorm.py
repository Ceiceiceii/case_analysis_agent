"""Brainstorm Partner agent node."""

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
from prompts import BRAINSTORM_SYSTEM_PROMPT
from state.project_state import ProjectState
from tools.kb_tools import search_kb_tool

_BRAINSTORM_TOOLS = [search_kb_tool]


def _get_llm():
    return ChatOpenAI(
        model=MINIMAX_MODEL,
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        temperature=0.3,  # slightly higher for creative output
        max_tokens=LLM_MAX_TOKENS,
    )


def brainstorm_node(state: ProjectState) -> Command:
    """Brainstorm Partner agent node."""
    conversation = state.get("conversation_history", [])
    last_user_msg = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    client_name = state.get("client_name", "")
    project_type = state.get("project_type", "")
    kb_ids = state.get("selected_kb_ids", [])

    context = (
        f"Client: {client_name}\n"
        f"Project type: {project_type}\n"
        f"Available KBs: {kb_ids}\n"
        "Generate at least 3 strategic options. Include one contrarian option."
    )

    llm = _get_llm()
    agent = create_react_agent(llm, _BRAINSTORM_TOOLS, prompt=BRAINSTORM_SYSTEM_PROMPT)

    try:
        result = agent.invoke({
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": last_user_msg or f"Generate strategic options for {client_name}."},
            ]
        })
        last_msg = result["messages"][-1]
        response_content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    except Exception as e:
        response_content = f"Brainstorm error: {e}"

    return Command(
        goto="orchestrator",
        update={
            "agent_message": response_content,
            "next_node": "orchestrator",
            "conversation_history": [{
                "role": "assistant",
                "content": f"[brainstorm] {response_content}",
                "agent": "brainstorm",
            }],
        },
    )
