"""Analyst agent node."""

import json

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
from prompts import ANALYST_SYSTEM_PROMPT
from state.project_state import ProjectState
from tools.analysis_tools import run_analysis_tool
from tools.discovery_tools import generate_questionnaire_tool, run_background_research_tool
from tools.kb_tools import search_kb_tool

_ANALYST_TOOLS = [
    generate_questionnaire_tool,
    run_background_research_tool,
    run_analysis_tool,
    search_kb_tool,
]


def _get_llm():
    return ChatOpenAI(
        model=MINIMAX_MODEL,
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )


def analyst_node(state: ProjectState) -> Command:
    """Discovery & Analysis agent node."""
    conversation = state.get("conversation_history", [])
    last_user_msg = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    project_id = state.get("project_id", "")
    client_name = state.get("client_name", "")
    project_type = state.get("project_type", "")
    kb_ids = state.get("selected_kb_ids", [])
    discovery_answers = state.get("discovery_answers", {})
    phase = state.get("phase", "intake")

    context = (
        f"Project: {project_id}\n"
        f"Client: {client_name}\n"
        f"Project type: {project_type}\n"
        f"Current phase: {phase}\n"
        f"KB IDs: {kb_ids}\n"
        f"Discovery answers collected: {len(discovery_answers)}\n"
    )
    if discovery_answers:
        context += f"Sample answers: {json.dumps(dict(list(discovery_answers.items())[:3]))}\n"

    llm = _get_llm()
    agent = create_react_agent(llm, _ANALYST_TOOLS, prompt=ANALYST_SYSTEM_PROMPT)

    try:
        result = agent.invoke({
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": last_user_msg or f"Begin Tier 1 discovery for {client_name}."},
            ]
        })
        last_msg = result["messages"][-1]
        response_content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    except Exception as e:
        response_content = f"Analyst error: {e}"

    # Extract any new discovery answers from the response (simple heuristic)
    new_answers = {}

    return Command(
        goto="orchestrator",
        update={
            "agent_message": response_content,
            "next_node": "orchestrator",
            "discovery_answers": {**discovery_answers, **new_answers},
            "conversation_history": [{
                "role": "assistant",
                "content": f"[analyst] {response_content}",
                "agent": "analyst",
            }],
        },
    )
