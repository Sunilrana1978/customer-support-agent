"""
Tool 4: web_search — AgentCore Gateway Lambda target.
Uses DuckDuckGo (no API key required).
"""

import json


def handler(event, context):
    """Search the web via DuckDuckGo and return structured results."""
    query = event.get("query", "").strip()
    max_results = int(event.get("max_results", 5))

    if not query:
        return {"error": "query parameter is required", "results": []}

    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

        return {
            "query": query,
            "total_results": len(results),
            "results": results,
        }

    except Exception as exc:
        return {
            "error": f"Search failed: {str(exc)}",
            "query": query,
            "results": [],
        }
