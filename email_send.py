"""
email_send.py

STEP 6: send the finished HTML newsletter via Resend.

Design notes:
- Plain `requests` POST to the Resend REST API -- no extra dependency, same
  pattern web_enrich.py uses for Tavily. Resend's send endpoint is a single
  authenticated JSON POST.
- Config comes from env vars (never hardcode keys):
    RESEND_API_KEY   -- required; the send fails loudly without it.
    RECIPIENT_EMAIL  -- required; where the briefing goes.
    RESEND_FROM      -- optional; defaults to onboarding@resend.dev, which
                        Resend lets you send from with NO domain verification.
                        Swap to a verified domain address later.
- Returns the Resend message id on success so main.py can log it.
- Raises RuntimeError with a clear message on any failure, so a bad send at
  6am surfaces as one specific, debuggable error rather than a silent no-op.
"""

import os
import requests


RESEND_ENDPOINT = "https://api.resend.com/emails"
SEND_TIMEOUT = 15  # seconds; a slow API shouldn't hang the daily run forever.

# Default from-address. onboarding@resend.dev works out of the box on the free
# tier with no domain setup -- ideal for getting the first real send working.
DEFAULT_FROM = "Portfolio Briefing <onboarding@resend.dev>"


def send_email(html: str, subject: str) -> str:
    """
    Send one HTML email through Resend.

    Args:
        html: the full HTML body (from email_template.build_email_html).
        subject: the email subject line.

    Returns:
        The Resend message id (a string) on success.

    Raises:
        RuntimeError: if config is missing or the API rejects the send.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError(
            "RESEND_API_KEY environment variable not set. "
            "Set it locally for testing, or as a GitHub Actions secret for production."
        )

    recipient = os.environ.get("RECIPIENT_EMAIL")
    if not recipient:
        raise RuntimeError(
            "RECIPIENT_EMAIL environment variable not set. "
            "This is the address the briefing is sent to."
        )

    from_address = os.environ.get("RESEND_FROM", DEFAULT_FROM)

    payload = {
        "from": from_address,
        "to": [recipient],
        "subject": subject,
        "html": html,
    }

    try:
        resp = requests.post(
            RESEND_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=SEND_TIMEOUT,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Resend request failed to send: {e}") from e

    # Resend returns 200 with {"id": "..."} on success; non-2xx carries an
    # error message in the body that's worth surfacing verbatim.
    if not resp.ok:
        raise RuntimeError(
            f"Resend API returned {resp.status_code}: {resp.text[:500]}"
        )

    try:
        message_id = resp.json().get("id")
    except ValueError:
        raise RuntimeError(f"Resend returned non-JSON success body: {resp.text[:500]}")

    if not message_id:
        raise RuntimeError(f"Resend success response missing 'id': {resp.text[:500]}")

    return message_id


if __name__ == "__main__":
    # Manual test: requires RESEND_API_KEY + RECIPIENT_EMAIL set. Sends a tiny
    # real email so you can confirm delivery end-to-end before wiring main.py.
    test_html = """
    <div style="font-family:sans-serif; padding:24px;">
      <h1>Resend test</h1>
      <p>If you're reading this in your inbox, email_send.py works.</p>
    </div>
    """
    msg_id = send_email(test_html, subject="Portfolio Newsletter — Resend test")
    print(f"Sent. Resend message id: {msg_id}")
