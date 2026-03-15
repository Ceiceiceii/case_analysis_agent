"""Analysis tools for the Analyst agent."""

import json
from datetime import datetime
from langchain_core.tools import tool
import knowledge_base as kb_module


@tool
def run_analysis_tool(
    project_id: str,
    client_name: str,
    project_type: str,
    discovery_answers: dict,
    kb_ids: list[str],
) -> str:
    """
    Run structured analysis using What/Why/How framework and gap scorecard.
    Searches KBs for supporting evidence and returns structured findings.
    """
    # Build analysis query from discovery answers
    context_lines = []
    for qid, answer in discovery_answers.items():
        if isinstance(answer, str) and answer.strip():
            context_lines.append(f"Q[{qid}]: {answer}")
    context = "\n".join(context_lines[:10])  # limit context size

    # Search KBs for relevant content
    kb_evidence = []
    if kb_ids:
        query = f"{project_type} analysis {client_name} {context[:200]}"
        docs = kb_module.search_across_kbs(kb_ids, query, k=6)
        for doc in docs:
            kb_evidence.append({
                "source": doc.metadata.get("source", "unknown"),
                "kb_id": doc.metadata.get("kb_id", ""),
                "excerpt": doc.page_content[:300],
            })

    # Build structured analysis output
    analysis = {
        "project_id": project_id,
        "client_name": client_name,
        "project_type": project_type,
        "analyzed_at": datetime.utcnow().isoformat(),
        "framework": "What-Why-How",
        "sections": {
            "what": {
                "title": "WHAT: Current State Assessment",
                "description": "Based on discovery, the current state and primary challenge.",
                "key_findings": [],
                "evidence_count": len(kb_evidence),
            },
            "why": {
                "title": "WHY: Root Cause Analysis",
                "description": "Underlying drivers and causal factors.",
                "root_causes": [],
            },
            "how": {
                "title": "HOW: Solution Pathways",
                "description": "Potential approaches to address the challenge.",
                "options": [],
            },
        },
        "gap_scorecard": {
            "capability_gaps": [],
            "resource_gaps": [],
            "process_gaps": [],
            "overall_readiness": "TBD",
        },
        "kb_evidence": kb_evidence,
        "discovery_context": context,
    }

    return json.dumps(analysis, ensure_ascii=False, indent=2)
