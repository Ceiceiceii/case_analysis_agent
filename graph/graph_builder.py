"""LangGraph StateGraph wiring — hub-and-spoke with Command pattern."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph

from agents.analyst import analyst_node
from agents.brainstorm import brainstorm_node
from agents.kb_manager import kb_manager_node
from agents.orchestrator import orchestrator_node
from agents.report_generator import report_generator_node
from state.project_state import ProjectState

_compiled_graph = None


def build_graph():
    """Build and compile the LangGraph StateGraph."""
    builder = StateGraph(ProjectState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("kb_manager", kb_manager_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("brainstorm", brainstorm_node)
    builder.add_node("report_generator", report_generator_node)

    builder.add_edge(START, "orchestrator")

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


def get_graph():
    """Return the singleton compiled graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_graph(state_update: dict, thread_id: str) -> dict:
    """
    Invoke the graph with a state update for a given thread.
    Returns the updated state.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(state_update, config=config)
    return result
