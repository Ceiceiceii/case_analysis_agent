"""Orchestrator node — routes requests via Command pattern."""

from langchain_openai import ChatOpenAI
from langgraph.types import Command

from config import (
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    MINIMAX_API_KEY,
    MINIMAX_BASE_URL,
    MINIMAX_MODEL,
)
from graph.routing import check_phase_dependency, get_allowed_nodes, resolve_next_node
from prompts import ORCHESTRATOR_SYSTEM_PROMPT
from state.project_state import ProjectState


def _get_llm():
    return ChatOpenAI(
        model=MINIMAX_MODEL,
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )


def orchestrator_node(state: ProjectState) -> Command:
    """
    Hub node: reads next_node from state and routes to the appropriate agent.
    Validates phase gates before routing.
    """
    current_phase = state.get("phase", "intake")
    next_node = state.get("next_node", "")
    conversation = state.get("conversation_history", [])

    # If next_node is explicitly set and allowed, route immediately
    if next_node and next_node != "orchestrator":
        allowed = get_allowed_nodes(current_phase)
        if next_node in allowed:
            # Check phase dependency before routing to analysis/report nodes
            ok, err = check_phase_dependency(current_phase, state)
            if not ok:
                return Command(
                    goto="orchestrator",
                    update={
                        "agent_message": err,
                        "error": err,
                        "next_node": "orchestrator",
                        "conversation_history": [{
                            "role": "assistant",
                            "content": f"[orchestrator] {err}",
                            "agent": "orchestrator",
                        }],
                    },
                )
            return Command(goto=next_node, update={"error": None})

    # Parse intent from last user message
    last_user_msg = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    if not last_user_msg:
        # Default: route to analyst for intake
        resolved = resolve_next_node("discover", current_phase)
        if resolved:
            return Command(goto=resolved, update={"error": None})
        return Command(
            goto="orchestrator",
            update={
                "agent_message": "What would you like to do? I can help with knowledge base management, discovery questions, analysis, or report generation.",
                "conversation_history": [{
                    "role": "assistant",
                    "content": "[orchestrator] What would you like to do?",
                    "agent": "orchestrator",
                }],
            },
        )

    # Use LLM to parse intent if simple keyword matching is insufficient
    resolved = resolve_next_node(last_user_msg, current_phase)

    if resolved is None:
        # Phase has no allowed nodes (e.g., delivered)
        msg = f"Project is in '{current_phase}' phase. No further actions available."
        return Command(
            goto="orchestrator",
            update={
                "agent_message": msg,
                "conversation_history": [{"role": "assistant", "content": f"[orchestrator] {msg}", "agent": "orchestrator"}],
            },
        )

    # Validate phase dependency
    ok, err = check_phase_dependency(current_phase, state)
    if not ok:
        return Command(
            goto="orchestrator",
            update={
                "agent_message": err,
                "error": err,
                "next_node": "orchestrator",
                "conversation_history": [{"role": "assistant", "content": f"[orchestrator] {err}", "agent": "orchestrator"}],
            },
        )

    return Command(goto=resolved, update={"error": None, "next_node": resolved})
