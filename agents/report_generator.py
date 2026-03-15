"""Report Generator agent node."""

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
from prompts import REPORT_GENERATOR_SYSTEM_PROMPT
from state.project_state import ProjectState
from tools.report_tools import (
    check_report_staleness_tool,
    generate_report_tool,
    get_report_tool,
    list_report_versions_tool,
)

_REPORT_TOOLS = [
    generate_report_tool,
    get_report_tool,
    list_report_versions_tool,
    check_report_staleness_tool,
]


def _get_llm():
    return ChatOpenAI(
        model=MINIMAX_MODEL,
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )


def report_generator_node(state: ProjectState) -> Command:
    """Report Generator agent node."""
    conversation = state.get("conversation_history", [])
    last_user_msg = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    project_id = state.get("project_id", "")
    client_name = state.get("client_name", "")
    project_type = state.get("project_type", "")
    phase = state.get("phase", "report_1")
    kb_ids = state.get("selected_kb_ids", [])
    discovery_answers = state.get("discovery_answers", {})

    # Determine which report number to generate
    phase_to_report = {"report_1": 1, "report_2": 2, "report_3": 3}
    report_num = phase_to_report.get(phase, 1)

    context = (
        f"Project ID: {project_id}\n"
        f"Client: {client_name}\n"
        f"Project type: {project_type}\n"
        f"Phase: {phase} → generating Report {report_num}\n"
        f"KB IDs: {kb_ids}\n"
        f"Discovery answers: {len(discovery_answers)} collected\n"
    )

    llm = _get_llm()
    agent = create_react_agent(llm, _REPORT_TOOLS, prompt=REPORT_GENERATOR_SYSTEM_PROMPT)

    try:
        result = agent.invoke({
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": last_user_msg or f"Generate Report {report_num} for {client_name}."},
            ]
        })
        last_msg = result["messages"][-1]
        response_content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    except Exception as e:
        response_content = f"Report generator error: {e}"

    # Build report dict to update state (draft status)
    report_key = f"report_{report_num}"
    current_report = state.get(report_key)
    updated_report = current_report or {
        "version": 1,
        "status": "draft",
        "content": response_content,
        "generated_at": "",
        "approved_at": None,
    }

    return Command(
        goto="orchestrator",
        update={
            "agent_message": response_content,
            "next_node": "orchestrator",
            report_key: updated_report,
            "conversation_history": [{
                "role": "assistant",
                "content": f"[report_generator] {response_content}",
                "agent": "report_generator",
            }],
        },
    )
