# Go-Live Guide — Portfolio Newsletter

**Bottom line:** the code is done and mock-tested. To go live you do four things, in order: (1) get three API keys, (2) put them in GitHub as secrets, (3) fill in your real holdings, (4) run it manually a few times, then flip on the daily schedule. Budget ~30 minutes. No coding required from here.

---

## Step 1 — Get the three API keys

Do these in any order. All three have free tiers that cover this project.

**Anthropic (the analysis).** Go to https://console.anthropic.com → sign up → verify your phone (unlocks $5 free trial credit) → **Settings → API Keys → Create Key**. Copy it (starts with `sk-ant-`). You only see it once.
*Cost reality:* ~3–5k tokens per run on Sonnet ≈ a few dollars per *year*. The $5 trial alone covers months.

**Resend (the email).** Go to https://resend.com → sign up (free tier = 3,000 emails/month, 100/day) → **API Keys → Create API Key** → copy it (starts with `re_`). No domain setup needed — the code sends from `onboarding@resend.dev`, which Resend allows out of the box.
*One catch:* on the free/unverified setup, Resend only lets you send to **your own verified account email**. So use the email you signed up with as your recipient. To send anywhere, verify a domain later (optional).

**Tavily (the web search).** Go to https://tavily.com → sign up → copy the API key from the dashboard (starts with `tvly-`). Free tier covers ~1,000 searches/month; you'll use ~20/day.
*Optional:* if you skip this one, the pipeline still runs — it just falls back to Yahoo Finance headlines with no crash.

---

## Step 2 — Add the keys to GitHub as secrets

In your repo on github.com: **Settings → Secrets and variables → Actions → New repository secret**. Add these four (names must match exactly):

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your `sk-ant-...` key |
| `TAVILY_API_KEY` | your `tvly-...` key |
| `RESEND_API_KEY` | your `re_...` key |
| `RECIPIENT_EMAIL` | the email that gets the briefing (your Resend account email) |
| `PORTFOLIO_JSON` | your real holdings as JSON — see Step 3 |

Secrets are encrypted and never printed in logs. This is why we never hardcode keys.

---

## Step 3 — Your real holdings (public repo, private positions)

**This repo is public, so your holdings never get committed.** Three pieces make that work:

- `portfolio.json` is **gitignored** — your real file stays on your machine only.
- `portfolio.example.json` **is** committed — it documents the schema publicly so others can fork the project.
- The workflow writes the real `portfolio.json` at run time from the `PORTFOLIO_JSON` secret, and it exists only for the ~1 minute the job runs.

**What to put in the secret.** The complete JSON, as one value:

```json
{
  "holdings": [
    { "ticker": "AAPL", "shares": 10, "cost_basis": 185.50 },
    { "ticker": "VOO",  "shares": 5,  "cost_basis": 410.00 }
  ]
}
```

Paste that whole block (with your real positions) as the value of the `PORTFOLIO_JSON` secret.

Two rules: tickers must match Yahoo Finance format (e.g. `BRK-B`, not `BRK.B`), and sector is looked up live — you don't put it in the file.

**Also keep a local copy.** For local testing, create your own `portfolio.json` with the same content — it's gitignored, so it can't leak:

```bash
cp portfolio.example.json portfolio.json   # then edit in your real holdings
```

### Privacy notes for a public repo

- **Actions logs are public on a public repo.** The pipeline is written to print only *counts* ("5 holdings"), never ticker names. If a run crashes, the log shows just the exception type — the full traceback goes to your alert email instead, which only you can read.
- **Never commit `portfolio.json`.** The `.gitignore` entry protects you, but if you ever see it in a `git status` staging list, stop and re-check.
- **What the public does see:** all the code, the architecture, the design docs, and fake example holdings. That's the part that makes it a good portfolio piece.

---

## Step 4 — Push the code, then test before trusting the schedule

**Push everything to the repo** (if not already there). From the project folder:

```bash
git init            # skip if already a repo
git add .
git commit -m "Complete pipeline: email_send, main, Docker, CI"
git branch -M main
git remote add origin https://github.com/krishpathak28/<your-repo>.git
git push -u origin main
```

**Do a manual test run.** In the repo: **Actions tab → "Daily Portfolio Briefing" → Run workflow**. This is the `workflow_dispatch` button. Watch the run:
- Green check → look in your inbox for the briefing. 🎉
- Red X → click into the logs; the failing stage prints as `[n/5] ...`. You'll *also* get an `[ALERT]` email with the traceback (that's the built-in failure handler working).

Run it manually a few times across a couple of days until you trust it.

**Then the schedule runs itself.** The briefing is set for **weekdays at 5:00 PM America/New_York** — one hour after the closing bell (2:00 PM Pacific). Nothing to flip on; once the workflow file is on `main`, GitHub schedules it automatically.

*Why 5:00 PM ET, not 4:00:* earnings are released between 4:05 and 4:30 PM ET, and the coverage explaining a move lands 20–40 minutes later. Running at 5:00 means the "why" behind a big move actually exists for the web-search step to find, instead of reporting a price drop with no story attached.

*How DST is handled:* GitHub cron is always UTC and ignores daylight saving, so a single fixed cron drifts an hour twice a year. Instead, two crons are scheduled (21:00 and 22:00 UTC) and a `gate` job checks real New York time, allowing only the correct one through. The off-season one appears as a grey "skipped" job. Verified against all 261 weekdays of 2026: exactly one run per day, year-round, no drift.

*Punctuality caveat:* GitHub's scheduled runs are best-effort and commonly run 5–20 minutes late during peak load, occasionally longer, and rarely get skipped entirely. Expect the email between about 5:05 and 5:30 PM ET. If a day gets skipped, the manual **Run workflow** button always works.

---

## Optional — test locally first (fastest feedback loop)

If you'd rather see it work on your own machine before touching GitHub:

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."
export RESEND_API_KEY="re_..."
export RECIPIENT_EMAIL="you@example.com"

python3 src/data_fetch.py      # confirms Yahoo Finance is reachable + sector lookup
python3 src/analysis.py        # confirms real Claude output quality
python3 src/email_send.py      # sends a tiny test email — check your inbox
python3 src/main.py            # runs the whole thing end-to-end

# and to run the test suite:
python3 tests/test_integration.py
```

Run these **from the project root** (not from inside `src/`) so `portfolio.json` is found. Do it from a spot that can reach the internet (the earlier build sandbox couldn't, which is why live calls were never verified — this local run is the real first test).

---

## Quick reference — what each piece needs

| Stage | Needs | If it's missing |
|---|---|---|
| `data_fetch.py` | nothing (yfinance is keyless) | per-ticker errors isolated; run continues |
| `web_enrich.py` | `TAVILY_API_KEY` | degrades to Yahoo headlines, no crash |
| `analysis.py` | `ANTHROPIC_API_KEY` | **hard stop** — sends you an alert email |
| `email_send.py` | `RESEND_API_KEY`, `RECIPIENT_EMAIL` | **hard stop** — can't send anything |

---

## Known caveats (from the handoff, still true)

- **VaR is a rough gauge only** — it assumes zero correlation between holdings, so it understates real downside. Never read it as precise; the code and prompt both label it that way on purpose.
- **ETFs (e.g. VOO)** often return no sector → bucketed as "Unknown". Expected, handled.
- **yfinance is unofficial** and can rate-limit or break; may need a fallback data source someday.
- **Resend free tier** sends only to your own account email until you verify a domain.
