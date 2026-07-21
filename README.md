# Portfolio Newsletter

A daily automated email that analyzes your personal investment portfolio like a
Wall Street analyst: price action, the "why" behind each move, how it fits your
position, portfolio-level risk (sector concentration, VaR, P&L), and a
next-step thought per holding.

## Pipeline

`portfolio.json` → data_fetch (yfinance) → web_enrich (Tavily) → risk metrics →
Claude analysis → HTML email → Resend → your inbox. Scheduled daily via GitHub
Actions, runs in Docker.

## Setup

1. `pip install -r requirements.txt`
2. Set environment variables: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`,
   `RESEND_API_KEY`, `RECIPIENT_EMAIL`.
3. `cp portfolio.example.json portfolio.json`, then edit in your holdings
   (ticker / shares / cost_basis). `portfolio.json` is gitignored — real
   holdings are never committed. In CI it's written at run time from the
   `PORTFOLIO_JSON` secret.
4. Test each module locally (see HANDOFF.md), then wire up the daily workflow.

## Modules

- `data_fetch.py` — market data + sector via yfinance
- `web_enrich.py` — per-ticker web search (swappable provider)
- `risk.py` — sector concentration, parametric VaR, P&L (dependency-free)
- `frameworks.py` — analyst reasoning framework injected into the prompt
- `analysis.py` — Claude API call, JSON output, validation
- `email_template.py` — inline-CSS HTML newsletter
- `email_send.py` — Resend delivery
- `main.py` — orchestrator (chains all stages, alert-email on failure)
- `Dockerfile` — python:3.12-slim container that runs `main.py`
- `.github/workflows/daily.yml` — weekday cron + manual run button

## Attribution

- Risk logic adapted from [wshobson/maverick-mcp](https://github.com/wshobson/maverick-mcp) (MIT).
- Analyst framework adapted from [Assaad-FT/assaad-skills](https://github.com/Assaad-FT/assaad-skills).

## Disclaimer

Automated, AI-assisted, for personal use. Not financial advice. Data may be
stale; analysis may contain errors. Verify before acting.
