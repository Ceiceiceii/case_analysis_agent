"""JSON persistence for project state in data/projects/{project_id}.json."""

import json
import os
import uuid
from typing import Optional

from config import PROJECTS_DIR
from state.project_state import Phase, ProjectState


def _project_path(project_id: str) -> str:
    return os.path.join(PROJECTS_DIR, f"{project_id}.json")


def create_project(client_name: str, project_type: str) -> ProjectState:
    """Create a new project and persist it. Returns initial ProjectState."""
    project_id = str(uuid.uuid4())
    state: ProjectState = {
        "project_id": project_id,
        "client_name": client_name,
        "project_type": project_type,
        "phase": Phase.INTAKE.value,
        "selected_kb_ids": [],
        "kb_locked": False,
        "conversation_history": [],
        "discovery_answers": {},
        "discovery_questions": [],
        "report_1": None,
        "report_2": None,
        "report_3": None,
        "current_report_version": 0,
        "source_citations": [],
        "kb_enrichment_log": [],
        "next_node": "orchestrator",
        "agent_message": "",
        "error": None,
        "pending_approval": None,
    }
    save_project(state)
    return state


def save_project(state: ProjectState) -> None:
    """Persist project state to disk."""
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    path = _project_path(state["project_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_project(project_id: str) -> Optional[ProjectState]:
    """Load project state from disk. Returns None if not found."""
    path = _project_path(project_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_projects() -> list[dict]:
    """Return list of {project_id, client_name, project_type, phase} for all saved projects."""
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    projects = []
    for fname in os.listdir(PROJECTS_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(PROJECTS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            projects.append({
                "project_id": data["project_id"],
                "client_name": data.get("client_name", ""),
                "project_type": data.get("project_type", ""),
                "phase": data.get("phase", Phase.INTAKE.value),
            })
        except Exception:
            continue
    return projects


def delete_project(project_id: str) -> bool:
    """Delete a project file. Returns True if deleted."""
    path = _project_path(project_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def update_project_phase(project_id: str, new_phase: str) -> bool:
    """Update only the phase field of a project. Returns True on success."""
    state = load_project(project_id)
    if state is None:
        return False
    state["phase"] = new_phase
    save_project(state)
    return True
