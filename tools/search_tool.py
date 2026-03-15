"""Web search abstraction: Tavily (primary) or DuckDuckGo (fallback)."""

from typing import Optional
from config import TAVILY_API_KEY


def _confidence(result: dict) -> str:
    url = result.get("url", "")
    score = result.get("score", 0.0)
    if any(d in url for d in [".gov", ".edu", ".org"]) or score > 0.8:
        return "HIGH"
    elif score > 0.5:
        return "MEDIUM"
    return "LOW"


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Run a web search. Returns list of dicts with:
        title, url, content, confidence (HIGH/MEDIUM/LOW)
    Only HIGH and MEDIUM results are returned; LOW are silently dropped.
    """
    raw_results = []

    if TAVILY_API_KEY:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=TAVILY_API_KEY)
            response = client.search(query, max_results=max_results)
            for r in response.get("results", []):
                raw_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.5),
                })
        except Exception as e:
            raw_results = []

    if not raw_results:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    raw_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "content": r.get("body", ""),
                        "score": 0.5,
                    })
        except Exception:
            return []

    filtered = []
    for r in raw_results:
        conf = _confidence(r)
        if conf in ("HIGH", "MEDIUM"):
            filtered.append({
                "title": r["title"],
                "url": r["url"],
                "content": r["content"],
                "confidence": conf,
            })

    return filtered
