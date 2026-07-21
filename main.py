"""
main.py

The orchestrator. Chains every stage of the daily pipeline and owns the
top-level error handling. This is what the Docker container / GitHub Action
actually runs each morning.

FLOW:
  portfolio.json
    -> data_fetch.fetch_all_holdings_data()   (yfinance: price, %chg, 52wk, P/E, sector, headlines)
    -> web_enrich.enrich_with_web_search()     (Tavily, 1 search/ticker -- "Option B")
    -> analysis.run_analysis()                 (risk metrics + framework + data -> Claude -> validated JSON)
    -> email_template.build_email_html()       (JSON -> inline-CSS HTML)
    -> email_send.send_email()                 (Resend -> inbox)

ERROR PHILOSOPHY:
- Per-holding data failures are already isolated upstream (data_fetch flags a
  bad ticker and the pipeline carries on), so one delisted symbol never kills
  the run.
- A CATASTROPHIC failure (e.g. the analysis API is down, or the portfolio file
  is missing) is caught here at the top level and turned into a plain-text
  ALERT email, so a 6am failure reaches your inbox instead of dying silently
  in a log you'll never read. If even the alert can't send, we exit non-zero
  so GitHub Actions marks the run red.
"""

import sys
import traceback
from datetime import datetime

from data_fetch import fetch_all_holdings_data
from web_enrich import enrich_with_web_search
from analysis import run_analysis
from email_template import build_email_html
from email_send import send_email


def _subject_line() -> str:
    """Dated subject so briefings thread nicely and are easy to find."""
    return f"Portfolio Briefing — {datetime.now().strftime('%A, %b %d')}"


def _send_failure_alert(error: Exception) -> None:
    """
    Best-effort: turn a pipeline crash into an alert email so you actually
    hear about it. Deliberately dependency-light -- it only needs email_send,
    which reads its own config from env.
    """
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
                Roboto,Helvetica,Arial,sans-serif; padding:24px; max-width:640px;
                margin:0 auto;">
      <h1 style="font-size:20px; color:#dc2626;">Portfolio briefing failed to build</h1>
      <p style="font-size:14px; color:#374151;">
        The daily pipeline hit an error before it could send your briefing.
        The technical details are below so you can debug the failing stage.
      </p>
      <pre style="background:#f3f4f6; border:1px solid #e5e7eb; border-radius:8px;
                  padding:16px; font-size:12px; color:#111827; overflow:auto;
                  white-space:pre-wrap;">{tb}</pre>
    </div>
    """
    send_email(html, subject=f"[ALERT] Portfolio briefing failed — {datetime.now().strftime('%b %d')}")


def run_pipeline() -> str:
    """
    Run the full pipeline and send the briefing.
    Returns the Resend message id on success.
    """
    print("[1/5] Fetching market data...")
    holdings_data = fetch_all_holdings_data()
    ok = sum(1 for h in holdings_data if not h.get("fetch_error"))
    print(f"      {ok}/{len(holdings_data)} holdings fetched cleanly.")

    print("[2/5] Enriching with web search...")
    holdings_data = enrich_with_web_search(holdings_data)

    print("[3/5] Running analysis (risk metrics + Claude)...")
    analysis = run_analysis(holdings_data)

    print("[4/5] Building HTML email...")
    html = build_email_html(analysis, holdings_data)

    print("[5/5] Sending via Resend...")
    message_id = send_email(html, subject=_subject_line())
    print(f"      Sent. Resend message id: {message_id}")
    return message_id


def main() -> int:
    """Entry point. Returns a process exit code (0 = success)."""
    try:
        run_pipeline()
        return 0
    except Exception as error:  # noqa: BLE001 -- top-level catch-all is intentional
        # PRIVACY: this repo is public, which makes GitHub Actions logs public
        # too. Error messages and tracebacks can contain ticker names (e.g.
        # "Missing analysis for tickers: [...]"), so the log gets only the
        # exception TYPE. The full traceback goes to the alert email, which
        # only you can read.
        print(
            f"PIPELINE FAILED: {type(error).__name__} "
            f"(details sent to your email, withheld from public logs)",
            file=sys.stderr,
        )
        try:
            _send_failure_alert(error)
            print("Sent failure-alert email.", file=sys.stderr)
        except Exception as alert_error:  # noqa: BLE001
            # Couldn't even send the alert (e.g. Resend key missing). Nothing
            # left to do but exit red so the scheduler flags the run.
            print(f"Could not send failure alert: {alert_error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
