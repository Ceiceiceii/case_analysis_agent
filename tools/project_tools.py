"""Project management tools (create, list, switch)."""

import json
from langchain_core.tools import tool
from state.project_store import create_project, list_projects, load_project


@tool
def create_project_tool(client_name: str, project_type: str) -> str:
    """Create a new consulting project. Returns project metadata as JSON."""
    state = create_project(client_name=client_name, project_type=project_type)
    return json.dumps({
        "project_id": state["project_id"],
        "client_name": state["client_name"],
        "project_type": state["project_type"],
        "phase": state["phase"],
    }, ensure_ascii=False)


@tool
def list_projects_tool() -> str:
    """List all existing consulting projects."""
    projects = list_projects()
    if not projects:
        return "No projects found."
    return json.dumps(projects, ensure_ascii=False, indent=2)


@tool
def get_project_status_tool(project_id: str) -> str:
    """Get the full status of a project including phase, KB selections, and report statuses."""
    state = load_project(project_id)
    if state is None:
        return f"Project '{project_id}' not found."

    def report_status(r):
        if r is None:
            return "not generated"
        return r.get("status", "draft")

    status = {
        "project_id": project_id,
        "client_name": state.get("client_name", ""),
        "project_type": state.get("project_type", ""),
        "phase": state.get("phase", ""),
        "kb_locked": state.get("kb_locked", False),
        "selected_kb_ids": state.get("selected_kb_ids", []),
        "report_1_status": report_status(state.get("report_1")),
        "report_2_status": report_status(state.get("report_2")),
        "report_3_status": report_status(state.get("report_3")),
        "discovery_questions_answered": len(state.get("discovery_answers", {})),
    }
    return json.dumps(status, ensure_ascii=False, indent=2)
