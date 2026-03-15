"""Discovery tools for the Analyst agent."""

import json
from langchain_core.tools import tool
import knowledge_base as kb_module
from tools.search_tool import web_search


@tool
def generate_questionnaire_tool(
    client_name: str,
    project_type: str,
    tier: int = 1,
    existing_answers: dict = None,
) -> str:
    """
    Generate ORID-structured discovery questions for a client engagement.
    tier: 1 = basic intake (5 questions), 2 = deepening (5 targeted follow-ups), 3 = gap-filling.
    existing_answers: dict of already answered questions to avoid repetition.
    Returns JSON list of question dicts with {id, tier, category, question, rationale}.
    """
    existing_answers = existing_answers or {}

    tier1_questions = [
        {
            "id": "t1_q1",
            "tier": 1,
            "category": "Objective",
            "question": f"What is the primary business objective for this {project_type} engagement with {client_name}?",
            "rationale": "Establishes the north star for all analysis",
        },
        {
            "id": "t1_q2",
            "tier": 1,
            "category": "Current State",
            "question": f"Describe {client_name}'s current situation and the key challenge you're facing.",
            "rationale": "Baseline for gap analysis",
        },
        {
            "id": "t1_q3",
            "tier": 1,
            "category": "Stakeholders",
            "question": "Who are the key decision-makers and stakeholders involved in this project?",
            "rationale": "Identifies influence map and approval chain",
        },
        {
            "id": "t1_q4",
            "tier": 1,
            "category": "Constraints",
            "question": "What are the key constraints — budget, timeline, resources, or regulatory requirements?",
            "rationale": "Scopes feasible solution space",
        },
        {
            "id": "t1_q5",
            "tier": 1,
            "category": "Success",
            "question": "How will you define success for this engagement? What does a great outcome look like?",
            "rationale": "Defines KPIs and acceptance criteria",
        },
    ]

    tier2_questions = [
        {
            "id": "t2_q1",
            "tier": 2,
            "category": "Root Cause",
            "question": "What do you believe are the root causes of the current challenges you described?",
            "rationale": "Moves from symptoms to drivers",
        },
        {
            "id": "t2_q2",
            "tier": 2,
            "category": "Previous Attempts",
            "question": "What solutions or approaches have been tried before? What worked, what didn't?",
            "rationale": "Avoids repeating past failures",
        },
        {
            "id": "t2_q3",
            "tier": 2,
            "category": "Competitive Context",
            "question": "How do your competitors approach this same challenge? What industry benchmarks are you aware of?",
            "rationale": "Identifies competitive pressure and best practices",
        },
        {
            "id": "t2_q4",
            "tier": 2,
            "category": "Data & Evidence",
            "question": "What data or evidence do you have to support the scale and urgency of this challenge?",
            "rationale": "Grounds analysis in facts not assumptions",
        },
        {
            "id": "t2_q5",
            "tier": 2,
            "category": "Change Readiness",
            "question": "How ready is the organization for change? What internal resistance might we face?",
            "rationale": "Assesses implementation feasibility",
        },
    ]

    tier3_questions = [
        {
            "id": "t3_q1",
            "tier": 3,
            "category": "Gap Analysis",
            "question": "What capabilities or resources do you currently lack to reach your desired state?",
            "rationale": "Direct gap identification",
        },
        {
            "id": "t3_q2",
            "tier": 3,
            "category": "Risk",
            "question": "What are the top 3 risks that could derail this initiative?",
            "rationale": "Risk register foundation",
        },
        {
            "id": "t3_q3",
            "tier": 3,
            "category": "Quick Wins",
            "question": "Are there any quick wins you could achieve in the next 30 days?",
            "rationale": "Early momentum building",
        },
    ]

    questions_by_tier = {1: tier1_questions, 2: tier2_questions, 3: tier3_questions}
    selected = questions_by_tier.get(tier, tier1_questions)

    # Filter out already-answered questions
    unanswered = [q for q in selected if q["id"] not in existing_answers]

    return json.dumps(unanswered, ensure_ascii=False, indent=2)


@tool
def run_background_research_tool(client_name: str, project_type: str, industry: str = "") -> str:
    """
    Run web research on the client/industry to enrich discovery context.
    Returns structured background findings with confidence ratings.
    """
    queries = [
        f"{client_name} company overview {industry}",
        f"{industry} industry trends {project_type}",
        f"{project_type} consulting best practices",
    ]

    all_findings = []
    for query in queries:
        results = web_search(query, max_results=3)
        for r in results:
            all_findings.append({
                "query": query,
                "title": r["title"],
                "url": r["url"],
                "excerpt": r["content"][:300],
                "confidence": r["confidence"],
            })

    if not all_findings:
        return "No background research results found. Proceeding with client-provided information only."

    output = f"## Background Research: {client_name} / {project_type}\n\n"
    for f in all_findings:
        output += f"### {f['title']} [{f['confidence']}]\n"
        output += f"Source: {f['url']}\n"
        output += f"{f['excerpt']}\n\n"

    return output
