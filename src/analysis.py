"""
analysis.py

Sends portfolio data to the Claude API and gets back structured analysis:
- a portfolio-level summary
- a 4-5 sentence analysis per holding (what happened, why, portfolio fit,
  next-step thought)

Now enhanced with:
- An analyst framework (frameworks.py) injected as a "how to reason" guide,
  adapted from the assaad-skills legendary-investor frameworks.
- Web-search context per holding (web_enrich.py, Option B) folded into the
  data block so the "why" sentence has real recent news to point to.

Design notes:
- Single API call for the whole portfolio, not one call per ticker.
- Output requested as strict JSON so email_template.py stays simple.
- validate_response() checks every ticker got a real analysis before the
  email step -- the guard between a malformed response and a broken send.
"""

import json
import os
from anthropic import Anthropic
from frameworks import get_framework_text
from risk import compute_risk_metrics


MODEL = "claude-sonnet-4-6"


def build_prompt(holdings_data: list[dict], risk_metrics: dict | None = None) -> str:
    """
    Build the prompt. Keeps input lean (price, %s, P/E, 52wk range, headlines,
    web_context, cost basis) -- high-signal tokens only -- and prepends the
    analyst framework as reasoning guidance.
    """
    clean_holdings = []
    for h in holdings_data:
        if h.get("fetch_error"):
            clean_holdings.append({
                "ticker": h["ticker"],
                "note": f"Data unavailable today ({h['fetch_error']})",
            })
        else:
            clean_holdings.append({
                "ticker": h["ticker"],
                "shares": h["shares"],
                "current_price": h["current_price"],
                "day_change_pct": h["day_change_pct"],
                "your_gain_loss_pct": h["gain_loss_pct"],
                "fifty_two_week_low": h["fifty_two_week_low"],
                "fifty_two_week_high": h["fifty_two_week_high"],
                "pe_ratio": h["pe_ratio"],
                "sector": h.get("sector"),
                "recent_headlines": h.get("headlines", []),
                "web_context": h.get("web_context", []),
            })

    tickers_list = ", ".join(h["ticker"] for h in holdings_data)
    framework = get_framework_text()

    # Build the portfolio-level risk block (quantitative context).
    risk_block = ""
    if risk_metrics:
        risk_block = f"""
PORTFOLIO-LEVEL RISK CONTEXT (quantitative -- use for the portfolio summary,
and reference per-holding only where relevant):
- Total portfolio value: ${risk_metrics['total_value']:,.2f}
- Total unrealized P&L: ${risk_metrics['total_pnl']:,.2f} ({risk_metrics['total_pnl_pct']:+.2f}%)
- Sector concentration: {json.dumps({k: f"{v*100:.0f}%" for k, v in risk_metrics['sector_concentration'].items()})}
- Largest sector: {risk_metrics['max_sector']} at {risk_metrics['max_sector_pct']*100:.0f}% (flag: {risk_metrics['concentration_flag']})
- 1-day parametric VaR (rough estimate, assumes no correlation, UNDERSTATES real risk):
  95%: ${risk_metrics['var_95']:,.2f} | 99%: ${risk_metrics['var_99']:,.2f}
- Risk notes: {risk_metrics['notes'] if risk_metrics['notes'] else "none"}

IMPORTANT on the VaR figure: it is a simplified estimate that assumes holdings
are uncorrelated, so it understates true downside. Present it as a rough gauge,
never as a precise risk number. Do NOT imply false precision.
"""

    prompt = f"""You are writing a daily portfolio newsletter for an individual retail investor.
Here is today's data for their {len(holdings_data)} holdings: {tickers_list}

{framework}
{risk_block}
DATA:
{json.dumps(clean_holdings, indent=2)}

For EACH holding, write a 4-5 sentence analysis covering, in this order:
1. What happened to the stock today (price action in plain terms)
2. Why it likely happened (tie to the headlines/web_context if available, or sector/market trends if not)
3. How this fits the investor's specific position (use their gain/loss %, not just today's move)
4. A concrete next-step thought, framed per the framework's guardrails (watch-item or research question, NOT a buy/sell instruction)

Be specific and substantive -- avoid generic filler like "markets can be volatile." If context data is missing for a holding, reason from sector/market context and say so plainly rather than inventing specifics. Follow the behavioral guardrails: do not turn a price drop alone into a sell signal.

Also write a 2-3 sentence portfolio-level summary: overall tone for the day, total P&L, and anything noteworthy across multiple holdings. Use the PORTFOLIO-LEVEL RISK CONTEXT above -- especially call out sector concentration if the flag is "warn" or "critical," since that's a standing risk most retail investors overlook.

Respond with ONLY valid JSON in this exact structure, no markdown formatting, no preamble:
{{
  "portfolio_summary": "string",
  "holdings": [
    {{"ticker": "string", "analysis": "string"}}
  ]
}}"""
    return prompt


def get_analysis(holdings_data: list[dict]) -> dict:
    """Call the Claude API and return the parsed JSON response."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Set it locally for testing, or as a GitHub Actions secret for production."
        )

    client = Anthropic(api_key=api_key)
    risk_metrics = compute_risk_metrics(holdings_data)
    prompt = build_prompt(holdings_data, risk_metrics)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Defensive cleanup in case the model wraps JSON in markdown fences.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude did not return valid JSON: {e}\nRaw response: {raw_text[:500]}")

    return parsed


def validate_response(parsed: dict, holdings_data: list[dict]) -> list[str]:
    """Confirm every ticker we sent has a real analysis back. [] means all good."""
    problems = []
    if "portfolio_summary" not in parsed or not parsed["portfolio_summary"]:
        problems.append("Missing portfolio_summary")
    if "holdings" not in parsed:
        problems.append("Missing holdings array entirely")
        return problems

    expected_tickers = {h["ticker"] for h in holdings_data}
    returned_tickers = {h.get("ticker") for h in parsed["holdings"]}
    missing = expected_tickers - returned_tickers
    if missing:
        problems.append(f"Missing analysis for tickers: {sorted(missing)}")

    for h in parsed["holdings"]:
        if not h.get("analysis") or len(h["analysis"]) < 50:
            problems.append(f"Suspiciously short/empty analysis for {h.get('ticker')}")
    return problems


def run_analysis(holdings_data: list[dict]) -> dict:
    """Get the analysis and validate it. Raises if validation fails."""
    parsed = get_analysis(holdings_data)
    problems = validate_response(parsed, holdings_data)
    if problems:
        raise RuntimeError(f"Analysis validation failed: {problems}")
    return parsed


if __name__ == "__main__":
    sample_data = [
        {
            "ticker": "AAPL", "shares": 10, "cost_basis": 185.50,
            "current_price": 200.00, "day_change_pct": 2.56, "gain_loss_pct": 7.82,
            "fifty_two_week_low": 164.08, "fifty_two_week_high": 237.49, "pe_ratio": 31.2,
            "headlines": ["Apple announces new product line"],
            "web_context": ["Apple unveils AI features — analysts see holiday demand catalyst"],
            "fetch_error": None,
        }
    ]
    result = run_analysis(sample_data)
    print(json.dumps(result, indent=2))
