# Web Search Provider Options

The web-search step (`web_enrich.py`) is deliberately isolated so the provider
can be swapped by editing one function (`_search_provider`).

## Current: Tavily ("Option B")
- Fixed 1 search per ticker per run (predictable cost).
- Free tier available. Purpose-built for LLM context.
- Chosen so you can SEE and control exactly what's searched while learning.

## Future upgrade: "Option A" — let Claude search via the API
- Pass the `web_search` tool to the Claude API; Claude decides what to search.
- Smarter, less code, but less predictable cost. Natural next step once the
  pipeline is trusted.

## Considered and declined (for now): Perplexity Sonar API
Evaluated via a decision council. Verdict: a better Option B, but not worth
switching to yet.
- Sonar returns synthesized, CITED summaries (nice for the "why" sentence).
- Pricing (mid-2026): base Sonar ~$1/$1 per M tokens + ~$5/1k requests;
  Sonar Pro $3/$15 + $6–14/1k requests. Search + citations bundled in.
- ~15–20 requests/day ≈ a few dollars/month. Not free, but small.
- WHY DECLINED: it improves a step (separate web search) that Option A may
  make redundant entirely. Revisit only if (a) Tavily results prove too thin
  AND (b) you decide to keep search as a separate step rather than folding it
  into the Claude call. If so, Perplexity is the best-in-class choice for the
  slot, and the swap is still just one function.
