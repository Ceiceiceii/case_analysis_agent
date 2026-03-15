"""Knowledge base management tools for the KB Manager agent."""

import json
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool

import knowledge_base as kb_module
from tools.search_tool import web_search


@tool
def create_kb_tool(name: str, description: str = "") -> str:
    """Create a new named knowledge base. Returns KB ID and metadata."""
    meta = kb_module.create_kb(name=name, description=description)
    return json.dumps(meta, ensure_ascii=False)


@tool
def list_kbs_tool() -> str:
    """List all available knowledge bases with their metadata."""
    kbs = kb_module.list_kbs()
    if not kbs:
        return "No knowledge bases found."
    return json.dumps(kbs, ensure_ascii=False, indent=2)


@tool
def ingest_document_tool(kb_id: str, filename: str, content_text: str, source_url: str = "") -> str:
    """
    Ingest a text document into a knowledge base.
    content_text: the plain text content to ingest.
    Returns number of chunks added.
    """
    file_bytes = content_text.encode("utf-8")
    chunks = kb_module.ingest_into_kb(kb_id, file_bytes, filename, source_url=source_url)
    return f"Ingested {chunks} chunks into KB '{kb_id}' from '{filename}'."


@tool
def search_kb_tool(kb_ids: list[str], query: str, k: int = 4) -> str:
    """
    Search across one or more knowledge bases.
    kb_ids: list of KB IDs to search.
    Returns relevant excerpts with source metadata.
    """
    docs = kb_module.search_across_kbs(kb_ids, query, k=k)
    if not docs:
        return "No relevant documents found."
    results = []
    for i, doc in enumerate(docs, 1):
        src = doc.metadata.get("source", "unknown")
        results.append(f"[{i}] Source: {src}\n{doc.page_content[:400]}")
    return "\n\n---\n\n".join(results)


@tool
def set_kb_keywords_tool(kb_id: str, keywords: list[str]) -> str:
    """Set enrichment keywords for a knowledge base to guide web search."""
    ok = kb_module.set_kb_keywords(kb_id, keywords)
    if ok:
        return f"Keywords set for KB '{kb_id}': {', '.join(keywords)}"
    return f"KB '{kb_id}' not found."


@tool
def enrich_kb_tool(kb_id: str, query: str) -> str:
    """
    Search the web for content relevant to the KB and return proposed sources.
    Does NOT ingest automatically — user must approve via approve_enrichment_tool.
    Returns proposed sources as JSON for user review.
    """
    results = web_search(query, max_results=5)
    if not results:
        return "No web results found for the query."

    proposal = {
        "kb_id": kb_id,
        "query": query,
        "proposed_sources": results,
        "requires_approval": True,
        "proposed_at": datetime.utcnow().isoformat(),
    }
    return json.dumps(proposal, ensure_ascii=False, indent=2)


@tool
def approve_enrichment_tool(kb_id: str, approved_urls: list[str], proposed_sources: list[dict]) -> str:
    """
    Ingest approved web sources into a KB after user approval.
    approved_urls: list of URLs the user approved.
    proposed_sources: the list of proposed source dicts (from enrich_kb_tool output).
    """
    approved = [s for s in proposed_sources if s.get("url") in approved_urls]
    if not approved:
        return "No matching sources found for the provided URLs."

    ingested = 0
    for source in approved:
        content = source.get("content", "")
        url = source.get("url", "")
        title = source.get("title", url)
        if content.strip():
            file_bytes = content.encode("utf-8")
            chunks = kb_module.ingest_into_kb(
                kb_id, file_bytes, f"web_{title[:50]}.txt", source_url=url
            )
            ingested += chunks

    return f"Ingested {ingested} chunks from {len(approved)} approved web sources into KB '{kb_id}'."


@tool
def get_enrichment_logs_tool(kb_id: str) -> str:
    """Get the enrichment log for a knowledge base."""
    meta = kb_module.get_kb_meta(kb_id)
    if meta is None:
        return f"KB '{kb_id}' not found."
    sources = meta.get("sources", [])
    web_sources = [s for s in sources if s.get("url")]
    if not web_sources:
        return "No web enrichment sources found for this KB."
    return json.dumps(web_sources, ensure_ascii=False, indent=2)
