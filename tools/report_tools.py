"""Report generation and management tools."""

import json
import os
from datetime import datetime
from langchain_core.tools import tool

from config import REPORTS_DIR
import knowledge_base as kb_module


def _report_path(project_id: str, report_num: int, version: int) -> str:
    return os.path.join(REPORTS_DIR, f"{project_id}_report_{report_num}_v{version}.json")


def _load_latest_report(project_id: str, report_num: int) -> tuple[dict | None, int]:
    """Find the latest version of a report. Returns (report_dict, version)."""
    v = 1
    latest = None
    while True:
        path = _report_path(project_id, report_num, v)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            v += 1
        else:
            break
    return latest, v - 1


@tool
def generate_report_tool(
    project_id: str,
    report_num: int,
    client_name: str,
    project_type: str,
    discovery_answers: dict,
    kb_ids: list[str],
    analysis_json: str = "",
    previous_report_content: str = "",
) -> str:
    """
    Generate a consulting report (1, 2, or 3).
    report_num: 1=Background, 2=Analysis, 3=Recommendations.
    Returns the report dict as JSON and saves to disk.
    """
    # Gather KB evidence
    evidence_sections = []
    if kb_ids:
        query = f"{project_type} {client_name} report"
        docs = kb_module.search_across_kbs(kb_ids, query, k=6)
        for doc in docs:
            evidence_sections.append({
                "source": doc.metadata.get("source", "unknown"),
                "kb_id": doc.metadata.get("kb_id", ""),
                "excerpt": doc.page_content[:400],
                "source_url": doc.metadata.get("source_url", ""),
            })

    report_titles = {
        1: "Background & Context Report",
        2: "Analysis & Findings Report",
        3: "Recommendations & Roadmap Report",
    }

    report_sections = {
        1: ["Executive Summary", "Client Overview", "Industry Context",
            "Current State Assessment", "Key Challenges Identified", "Methodology"],
        2: ["Executive Summary", "Root Cause Analysis", "Gap Assessment",
            "Competitive Benchmarking", "Risk Register", "Key Insights"],
        3: ["Executive Summary", "Strategic Recommendations", "Implementation Roadmap",
            "Quick Wins (30 days)", "Medium-term Initiatives (90 days)",
            "Long-term Vision (12 months)", "Success Metrics", "Next Steps"],
    }

    _, latest_version = _load_latest_report(project_id, report_num)
    new_version = latest_version + 1

    # Build report content scaffold
    sections = report_sections.get(report_num, ["Executive Summary", "Findings", "Conclusions"])
    content_parts = [f"# {report_titles.get(report_num, f'Report {report_num}')}\n"]
    content_parts.append(f"**Client:** {client_name}\n**Project Type:** {project_type}\n")
    content_parts.append(f"**Date:** {datetime.utcnow().strftime('%B %d, %Y')}\n\n---\n")

    for section in sections:
        content_parts.append(f"\n## {section}\n\n*[Content to be populated by analyst based on discovery data]*\n")

    if evidence_sections:
        content_parts.append("\n## Supporting Evidence from Knowledge Base\n")
        for i, ev in enumerate(evidence_sections[:4], 1):
            content_parts.append(f"\n### Evidence {i}: {ev['source']}\n{ev['excerpt']}\n")

    if discovery_answers:
        content_parts.append("\n## Discovery Data Summary\n")
        for qid, ans in list(discovery_answers.items())[:5]:
            content_parts.append(f"**{qid}:** {ans}\n")

    content = "\n".join(content_parts)

    report_dict = {
        "project_id": project_id,
        "report_num": report_num,
        "version": new_version,
        "title": report_titles.get(report_num, f"Report {report_num}"),
        "status": "draft",
        "content": content,
        "generated_at": datetime.utcnow().isoformat(),
        "approved_at": None,
        "kb_evidence": evidence_sections,
        "source_count": len(evidence_sections),
    }

    path = _report_path(project_id, report_num, new_version)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)

    return json.dumps({
        "status": "generated",
        "report_num": report_num,
        "version": new_version,
        "path": path,
        "content_preview": content[:500],
    }, ensure_ascii=False)


@tool
def get_report_tool(project_id: str, report_num: int, version: int = 0) -> str:
    """
    Get a report's content and metadata.
    version=0 means latest version.
    """
    if version == 0:
        report, ver = _load_latest_report(project_id, report_num)
    else:
        path = _report_path(project_id, report_num, version)
        if not os.path.exists(path):
            return f"Report {report_num} version {version} not found."
        with open(path, "r", encoding="utf-8") as f:
            report = json.load(f)
        ver = version

    if report is None:
        return f"Report {report_num} has not been generated yet."

    return json.dumps(report, ensure_ascii=False, indent=2)


@tool
def list_report_versions_tool(project_id: str, report_num: int) -> str:
    """List all versions of a report."""
    versions = []
    v = 1
    while True:
        path = _report_path(project_id, report_num, v)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            versions.append({
                "version": v,
                "status": data.get("status", "draft"),
                "generated_at": data.get("generated_at", ""),
            })
            v += 1
        else:
            break

    if not versions:
        return f"No versions of Report {report_num} found."
    return json.dumps(versions, ensure_ascii=False, indent=2)


@tool
def check_report_staleness_tool(project_id: str, report_num: int, kb_ids: list[str]) -> str:
    """
    Check if a report is stale (KBs have been updated since report was generated).
    Returns staleness assessment.
    """
    report, _ = _load_latest_report(project_id, report_num)
    if report is None:
        return f"Report {report_num} has not been generated."

    generated_at = report.get("generated_at", "")
    stale_kbs = []
    for kb_id in kb_ids:
        meta = kb_module.get_kb_meta(kb_id)
        if meta:
            sources = meta.get("sources", [])
            for src in sources:
                ingested_at = src.get("ingested_at", "")
                if ingested_at > generated_at:
                    stale_kbs.append(kb_id)
                    break

    if stale_kbs:
        return (
            f"Report {report_num} may be stale. KBs updated after report generation: "
            f"{', '.join(stale_kbs)}. Consider regenerating."
        )
    return f"Report {report_num} is current — no KB updates since it was generated."
