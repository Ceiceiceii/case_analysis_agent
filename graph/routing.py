"""Phase routing table and dependency validation."""

from typing import Optional

PHASE_ROUTING: dict[str, set[str]] = {
    "intake":     {"kb_manager", "analyst"},
    "discovery":  {"kb_manager", "analyst"},
    "report_1":   {"report_generator", "analyst"},
    "analysis":   {"analyst", "kb_manager"},
    "report_2":   {"report_generator", "analyst"},
    "brainstorm": {"brainstorm", "report_generator"},
    "report_3":   {"report_generator"},
    "delivered":  set(),
}

# (prerequisite_report_key, required_status)
PHASE_DEPENDENCIES: dict[str, tuple[str, str]] = {
    "analysis":   ("report_1", "approved"),
    "report_2":   ("report_1", "approved"),
    "brainstorm": ("report_2", "approved"),
    "report_3":   ("report_2", "approved"),
    "delivered":  ("report_3", "approved"),
}

PHASE_ORDER = [
    "intake",
    "discovery",
    "report_1",
    "analysis",
    "report_2",
    "brainstorm",
    "report_3",
    "delivered",
]


def get_allowed_nodes(phase: str) -> set[str]:
    """Return the set of agent nodes allowed to run in the given phase."""
    return PHASE_ROUTING.get(phase, set())


def check_phase_dependency(phase: str, state: dict) -> tuple[bool, str]:
    """
    Check if dependency requirements are met to enter the given phase.
    Returns (ok: bool, error_message: str).
    """
    if phase not in PHASE_DEPENDENCIES:
        return True, ""

    report_key, required_status = PHASE_DEPENDENCIES[phase]
    report = state.get(report_key)

    if report is None:
        return False, (
            f"Cannot enter '{phase}' phase: {report_key} has not been generated yet. "
            f"Please complete and approve {report_key.replace('_', ' ').title()} first."
        )

    current_status = report.get("status", "")
    if current_status != required_status:
        return False, (
            f"Cannot enter '{phase}' phase: {report_key} status is '{current_status}', "
            f"but '{required_status}' is required."
        )

    return True, ""


def resolve_next_node(user_intent: str, current_phase: str) -> Optional[str]:
    """
    Map a user intent keyword to the appropriate agent node, gated by phase.
    Returns None if the intent doesn't map to an allowed node.
    """
    intent_map = {
        "kb": "kb_manager",
        "knowledge": "kb_manager",
        "upload": "kb_manager",
        "search": "kb_manager",
        "enrich": "kb_manager",
        "discover": "analyst",
        "question": "analyst",
        "analyze": "analyst",
        "analysis": "analyst",
        "report": "report_generator",
        "generate": "report_generator",
        "brainstorm": "brainstorm",
        "idea": "brainstorm",
        "option": "brainstorm",
    }

    allowed = get_allowed_nodes(current_phase)
    for keyword, node in intent_map.items():
        if keyword in user_intent.lower() and node in allowed:
            return node

    # Default routing per phase
    defaults = {
        "intake": "kb_manager",
        "discovery": "analyst",
        "report_1": "report_generator",
        "analysis": "analyst",
        "report_2": "report_generator",
        "brainstorm": "brainstorm",
        "report_3": "report_generator",
    }
    return defaults.get(current_phase)


def get_phase_display_name(phase: str) -> str:
    names = {
        "intake": "Intake",
        "discovery": "Discovery",
        "report_1": "Report 1 (Background)",
        "analysis": "Analysis",
        "report_2": "Report 2 (Analysis)",
        "brainstorm": "Brainstorm",
        "report_3": "Report 3 (Recommendations)",
        "delivered": "Delivered",
    }
    return names.get(phase, phase.title())


def get_phase_index(phase: str) -> int:
    try:
        return PHASE_ORDER.index(phase)
    except ValueError:
        return 0
