"""ProjectState TypedDict and Phase enum for the consulting co-pilot."""

import operator
from enum import Enum
from typing import Annotated, Optional, TypedDict


class Phase(str, Enum):
    INTAKE = "intake"
    DISCOVERY = "discovery"
    REPORT_1 = "report_1"
    ANALYSIS = "analysis"
    REPORT_2 = "report_2"
    BRAINSTORM = "brainstorm"
    REPORT_3 = "report_3"
    DELIVERED = "delivered"


class ReportDict(TypedDict):
    version: int
    status: str  # "draft" | "approved" | "rejected"
    content: str
    generated_at: str
    approved_at: Optional[str]


class CitationDict(TypedDict):
    source_id: str
    source_type: str  # "kb" | "web"
    title: str
    url: Optional[str]
    kb_id: Optional[str]
    confidence: str  # "HIGH" | "MEDIUM" | "LOW"
    excerpt: str
    cited_in: str  # which report or analysis section


class EnrichmentLogEntry(TypedDict):
    kb_id: str
    query: str
    proposed_sources: list[dict]
    approved: bool
    approved_at: Optional[str]
    ingested_count: int


class ProjectState(TypedDict):
    project_id: str
    client_name: str
    project_type: str
    phase: str  # Phase enum value string

    selected_kb_ids: list[str]
    kb_locked: bool

    # Append-only via operator.add reducer
    conversation_history: Annotated[list[dict], operator.add]

    discovery_answers: dict
    discovery_questions: list[dict]

    report_1: Optional[ReportDict]
    report_2: Optional[ReportDict]
    report_3: Optional[ReportDict]
    current_report_version: int

    source_citations: Annotated[list[CitationDict], operator.add]
    kb_enrichment_log: Annotated[list[EnrichmentLogEntry], operator.add]

    next_node: str
    agent_message: str
    error: Optional[str]
    pending_approval: Optional[dict]
