"""
web_enrich.py

OPTION B: fixed, predictable web search per ticker to enrich the "why"
context beyond what yfinance's news field provides.

DESIGN FOR FUTURE SWITCH TO OPTION A:
Everything funnels through enrich_with_web_search(). When you're ready to
let Claude drive its own searches via the API's web_search tool (Option A),
you just stop calling this function and pass the tool to the API instead --
nothing else in the pipeline changes.

PROVIDER-AGNOSTIC:
The actual search call is isolated in _search_provider(). Swap that one
function to change providers (Tavily / Serper / Brave) without touching the
rest. Default here is Tavily, which is purpose-built for LLM context and has
a free tier, but the shape is the same for any of them.

COST CONTROL:
Exactly ONE search per ticker per run. 15-20 holdings = 15-20 searches/day.
That's the whole point of Option B -- you know the number in advance.
"""

import os
import requests


# How many result snippets to keep per ticker. Small on purpose -- high
# signal, low token cost when this gets fed into the analysis prompt.
MAX_SNIPPETS_PER_TICKER = 3

# Search timeout per request (seconds). A slow provider shouldn't hang the
# whole daily run.
SEARCH_TIMEOUT = 10


def _search_provider(query: str) -> list[str]:
    """
    The ONE function to change if you swap search providers.

    Returns a list of short text snippets (headlines/summaries) for the query.
    Returns [] on any failure -- a failed search is not fatal, the holding
    just falls back to its yfinance headlines.

    Currently implemented for Tavily (https://tavily.com). To switch to
    Serper or Brave, replace the request/parse logic below; keep the
    signature identical.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        # No key configured -> silently skip enrichment rather than crash.
        # The pipeline still works on yfinance data alone.
        return []

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": MAX_SNIPPETS_PER_TICKER,
                "topic": "news",
                "days": 3,  # only recent news -- staleness is the enemy here
            },
            timeout=SEARCH_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        snippets = []
        for result in data.get("results", []):
            title = result.get("title", "").strip()
            content = result.get("content", "").strip()
            if title:
                # Keep it compact: title + a short content clip.
                snippet = title
                if content:
                    snippet += f" — {content[:180]}"
                snippets.append(snippet)
        return snippets[:MAX_SNIPPETS_PER_TICKER]

    except Exception:
        return []


def _build_query(holding: dict) -> str:
    """
    Build the search query for a ticker. Fixed template (that's Option B).
    Kept specific so results are about the company's recent news, not generic.
    """
    ticker = holding["ticker"]
    return f"{ticker} stock news today why moving"


def enrich_with_web_search(holdings_data: list[dict]) -> list[dict]:
    """
    Main entry point. For each holding, runs one web search and attaches the
    snippets under a new 'web_context' key. Non-destructive: everything else
    in each holding dict is preserved.

    This is the function you STOP calling when you migrate to Option A.
    """
    enriched = []
    for holding in holdings_data:
        # Don't waste a search on a ticker whose market-data fetch failed.
        if holding.get("fetch_error"):
            enriched.append({**holding, "web_context": []})
            continue

        query = _build_query(holding)
        snippets = _search_provider(query)
        enriched.append({**holding, "web_context": snippets})

    return enriched


if __name__ == "__main__":
    # Manual test: requires TAVILY_API_KEY set. Shows exactly what each
    # ticker's search pulls back -- which is the whole reason you picked
    # Option B (you get to inspect the searches).
    import json
    sample = [
        {"ticker": "AAPL", "shares": 10, "cost_basis": 185.50, "fetch_error": None},
        {"ticker": "VOO", "shares": 5, "cost_basis": 410.00, "fetch_error": None},
    ]
    result = enrich_with_web_search(sample)
    for h in result:
        print(f"\n=== {h['ticker']} ===")
        if h["web_context"]:
            for i, snip in enumerate(h["web_context"], 1):
                print(f"  {i}. {snip}")
        else:
            print("  (no web context — check TAVILY_API_KEY is set)")
