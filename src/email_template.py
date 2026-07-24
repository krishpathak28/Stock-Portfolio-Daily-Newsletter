"""
email_template.py

Turns the structured analysis from analysis.py into a clean HTML email.

Design notes:
- Card-per-holding layout with breathing room for 4-5 sentence analyses.
- Gains green, losses red for fast visual scan.
- Inline CSS only -- email clients strip <style> blocks unpredictably.
- Pure f-string building, no templating engine dependency.
"""

from datetime import datetime


def _color_for_change(value) -> str:
    if value is None:
        return "#6b7280"
    if value > 0:
        return "#16a34a"
    if value < 0:
        return "#dc2626"
    return "#6b7280"


def _format_pct(value) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value}%"


def _collect_headlines(holding_data: dict, max_items: int = 3) -> list[str]:
    """
    Build a short, de-duplicated headline list for a card.

    Sources, in priority order: yfinance headlines (clean titles) first, then
    Tavily web_context snippets (formatted "Title — clip", so we keep just the
    title before the em dash). Case-insensitive de-dupe keeps the two sources
    from repeating the same story.
    """
    items: list[str] = []
    seen: set[str] = set()

    def _add(text: str) -> None:
        title = text.split(" — ")[0].strip()
        key = title.lower()
        if title and key not in seen:
            seen.add(key)
            items.append(title)

    for h in holding_data.get("headlines", []) or []:
        _add(h)
    for snip in holding_data.get("web_context", []) or []:
        _add(snip)

    return items[:max_items]


def _render_headlines(holding_data: dict) -> str:
    """Compact 'Recent headlines' block. Returns '' if there's no news."""
    headlines = _collect_headlines(holding_data)
    if not headlines:
        return ""

    rows = ""
    for title in headlines:
        rows += f"""
        <li style="margin-bottom:4px;">{title}</li>"""

    return f"""
      <div style="margin-top:14px; padding-top:12px; border-top:1px solid #f3f4f6;">
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.05em;
                    color:#9ca3af; margin-bottom:6px;">Recent headlines</div>
        <ul style="margin:0; padding-left:18px; font-size:12px; line-height:1.5;
                   color:#6b7280;">{rows}
        </ul>
      </div>"""


def _render_holding_card(holding_data: dict, analysis_text: str) -> str:
    ticker = holding_data["ticker"]
    day_change = holding_data.get("day_change_pct")
    gain_loss = holding_data.get("gain_loss_pct")
    price = holding_data.get("current_price")
    price_str = f"${price:,.2f}" if price is not None else "N/A"
    headlines_html = _render_headlines(holding_data)

    return f"""
    <div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px;
                padding:20px; margin-bottom:16px;">
      <div style="display:flex; justify-content:space-between; align-items:baseline;
                  margin-bottom:10px;">
        <span style="font-size:20px; font-weight:700; color:#111827;">{ticker}</span>
        <span style="font-size:16px; color:#374151;">{price_str}</span>
      </div>
      <div style="margin-bottom:12px; font-size:13px;">
        <span style="color:{_color_for_change(day_change)}; font-weight:600;">
          Today: {_format_pct(day_change)}
        </span>
        <span style="color:#9ca3af; margin:0 8px;">|</span>
        <span style="color:{_color_for_change(gain_loss)}; font-weight:600;">
          Your position: {_format_pct(gain_loss)}
        </span>
      </div>
      <div style="font-size:14px; line-height:1.6; color:#374151;">
        {analysis_text}
      </div>
      {headlines_html}
    </div>
    """


def build_email_html(analysis: dict, holdings_data: list[dict]) -> str:
    data_by_ticker = {h["ticker"]: h for h in holdings_data}
    date_str = datetime.now().strftime("%A, %B %d, %Y")

    cards_html = ""
    for item in analysis["holdings"]:
        ticker = item["ticker"]
        holding_data = data_by_ticker.get(ticker, {"ticker": ticker})
        cards_html += _render_holding_card(holding_data, item["analysis"])

    return f"""
    <div style="background:#f3f4f6; padding:24px; font-family:-apple-system,
                BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
      <div style="max-width:640px; margin:0 auto;">
        <div style="text-align:center; margin-bottom:8px;">
          <h1 style="font-size:24px; color:#111827; margin:0;">Your Portfolio Briefing</h1>
          <p style="font-size:13px; color:#6b7280; margin:4px 0 0 0;">{date_str}</p>
        </div>
        <div style="background:#111827; border-radius:12px; padding:20px;
                    margin:20px 0; color:#f9fafb; font-size:15px; line-height:1.6;">
          <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.05em;
                      color:#9ca3af; margin-bottom:8px;">Today's Summary</div>
          {analysis["portfolio_summary"]}
        </div>
        {cards_html}
        <div style="text-align:center; margin-top:24px; padding-top:16px;
                    border-top:1px solid #e5e7eb;">
          <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
            This is an automated briefing generated for your personal use.
            It is not financial advice. Data via Yahoo Finance and web search;
            analysis generated by AI and may contain errors — verify before acting.
          </p>
        </div>
      </div>
    </div>
    """


if __name__ == "__main__":
    sample_analysis = {
        "portfolio_summary": "A mixed session — tech names led while your ETF holdings tracked the broader market.",
        "holdings": [
            {"ticker": "AAPL", "analysis": "Apple climbed 2.56% today, closing at $200, following its new product line announcement. You're up 7.82% since your $185.50 entry. No action needed — worth watching whether it holds above $200."},
            {"ticker": "VOO", "analysis": "VOO was essentially flat, up 0.24%, mirroring a quiet day for the S&P 500. Your position sits 1.22% above cost basis. This is a core holding doing its job — no action required."},
        ],
    }
    sample_holdings_data = [
        {
            "ticker": "AAPL", "current_price": 200.00, "day_change_pct": 2.56,
            "gain_loss_pct": 7.82,
            "headlines": [
                "Apple unveils AI-powered features at fall product event",
                "Analysts raise Apple price targets on strong iPhone demand",
            ],
            "web_context": [
                "Apple stock jumps as new lineup drives holiday-quarter optimism — several firms lifted estimates citing upgrade cycle",
            ],
        },
        {
            "ticker": "VOO", "current_price": 415.00, "day_change_pct": 0.24,
            "gain_loss_pct": 1.22,
            "headlines": ["S&P 500 edges higher in quiet, low-volume session"],
            "web_context": [],
        },
    ]
    html = build_email_html(sample_analysis, sample_holdings_data)
    with open("sample_email.html", "w") as f:
        f.write(html)
    print("Wrote sample_email.html")
