# Portfolio Newsletter — Project Handoff

**Purpose of this doc:** hand off an in-progress project from a Claude Chat session to Cowork. Read this first to get oriented, then continue from "What's left to build."

---

## What this project is

A daily automated email newsletter that analyzes Krish's personal investment portfolio (15–20 holdings) like a Wall Street analyst would. Each morning a pipeline: pulls market data → enriches with web search → computes portfolio risk → sends it all to Claude for analysis → formats an HTML email → sends it. Runs unattended on a schedule.

**Owner:** Krish (GitHub: krishpathak28), 19, CS student. Wants to learn the full Python build, with assistance. Prefers answer-first, plain-English explanations.

---

## Locked-in architecture

```
GitHub Actions (daily cron)
  └─> Docker container
        └─> main.py orchestrates:
              portfolio.json
                → data_fetch.py   (yfinance: price, %chg, 52wk, P/E, sector, headlines)
                → web_enrich.py   (Tavily search, 1 per ticker — "Option B")
                → risk.py         (sector concentration, VaR, P&L)
                → analysis.py     (Claude API — framework + risk + data → JSON analysis)
                → email_template.py (JSON → HTML)
                → email_send.py   (Resend → inbox)
```

**Design principle throughout:** each stage is an isolated, independently testable module, so a failure at 6am points to one specific piece.

## Tech stack (decided, do not re-litigate without reason)

| Component | Choice | Why |
|---|---|---|
| Holdings source | manual `portfolio.json` | simplest; Schwab API is a future v2 (free w/ Schwab acct, but OAuth + 7-day token refresh is a hassle) |
| Market data | `yfinance` | free, no key |
| Web search | Tavily ("Option B": fixed 1 search/ticker in Python) | Krish wants to SEE/control searches while learning. Future: "Option A" = let Claude search via API tool. Isolated in `web_enrich.py` so the switch is a 1-function change. |
| Risk math | `risk.py` (adapted from maverick-mcp, MIT) | sector concentration + parametric VaR + P&L, dependency-free |
| Analysis | Claude API, model `claude-sonnet-4-6` | quality/cost sweet spot for analytical writing |
| Email format | inline-CSS HTML, card-per-holding | email clients strip <style> blocks |
| Email send | Resend | dev-first, 3k emails/mo free, ~5-line API |
| Container | Docker | reproducible; portable to Pi later |
| Schedule | GitHub Actions cron | free, already have GitHub |
| Secrets | GitHub Actions Secrets | never hardcode keys |

---

## Accounts / keys needed (Krish's action items)

| Account | For | Cost | Status |
|---|---|---|---|
| GitHub repo | scheduling | free | ✅ created (empty, no README/gitignore) |
| Anthropic API key | analysis | $5 free trial credit (phone verify), then pennies/day | ⬜ not yet obtained |
| Tavily API key | web search | free tier | ⬜ needed |
| Resend account + key | email | free tier | ⬜ needed for Step 6 |

At ~3–5k tokens/run on Sonnet, daily cost is a few dollars/year. The $5 Anthropic trial alone could cover months.

---

## Key decisions & their reasoning (so they aren't relitigated)

1. **Portfolio file keeps a fixed schema:** `{"holdings": [{"ticker","shares","cost_basis"}]}`. Sector is looked up live via yfinance, NOT stored in the file.
2. **4–5 sentences per holding** (not 2–3): Krish wants real analysis, not a skim. Structure per holding: what happened → why → how it fits YOUR position → next-step (watch-item/research question, never a buy/sell instruction).
3. **Analyst framework** (`frameworks.py`) adapted from the `Assaad-FT/assaad-skills` repo. Only the parts that daily price+news data can support HONESTLY were extracted — reasoning lenses + behavioral guardrails (esp. "don't turn a price drop into a sell signal"). Deliberately excluded deep-fundamental checklists that would tempt the model to fake conclusions.
4. **Risk math** (`risk.py`) extracted from `wshobson/maverick-mcp` (MIT) per a council decision. The WHOLE repo was rejected as massive scope-creep (it's a FastMCP server w/ Redis/Postgres/LangGraph/TA-Lib). Only the ~40 lines of risk logic were adapted. **The VaR is deliberately labeled as understating real risk** (it assumes zero correlation between holdings) — both in code and in the prompt — to avoid false precision.
5. **Perplexity for web search:** considered via council, DECLINED for now. It's a better Option B, but the real upgrade path is Option A (Claude-driven search), which may make a separate paid search step redundant. Revisit only if Tavily results prove too thin AND search stays a separate step.

## Repos evaluated (verdicts)

- `Assaad-FT/assaad-skills` → **extracted** analyst frameworks (adapted, condensed) ✅
- `wshobson/maverick-mcp` → **extracted** risk math only; rejected whole-repo adoption ✅
- `muratcankoylan/Agent-Skills-for-Context-Engineering` → ideas only (lean context, output validation); not installed
- `coreyhaines31/marketingskills` → irrelevant (marketing, not analysis)
- `aarora4/Awesome-Prediction-Market-Tools` → out of scope (prediction markets, separate project)
- `sablier-ai/sablier-mcp` → irrelevant (crypto token vesting)
- `Prateek13052003/stock-crew-ai` → not adopted; borrowed the "add live web search" idea only

---

## What's built (all tested, mocked where live keys were needed)

- `portfolio.json` — placeholder AAPL/VOO template (Krish fills real holdings later, same schema)
- `data_fetch.py` — yfinance pull, batched, per-ticker error isolation, sector lookup
- `web_enrich.py` — Tavily search, provider-isolated, graceful no-key fallback
- `frameworks.py` — condensed analyst reasoning framework
- `risk.py` — sector concentration + VaR + P&L, dependency-free, honest-limitation labeling
- `analysis.py` — builds prompt (framework + risk + data), calls Claude, parses JSON, validates all tickers present
- `email_template.py` — inline-CSS HTML, card-per-holding, green/red P&L, disclaimer footer
- `test_integration.py` — verifies framework injection, web-context wiring, graceful degradation, mocked API parse

**Testing note:** the sandbox couldn't reach Yahoo Finance (network allowlist) or use Krish's real API keys, so live network/API calls are UNVERIFIED. Parsing/math/validation logic is verified via mocks. First real run must be done by Krish locally.

## What's left to build

1. **`email_send.py`** (Step 6) — Resend API send. Needs RESEND_API_KEY + a from-address (start with onboarding@resend.dev, no domain verification needed).
2. **`main.py`** — orchestrator chaining all modules with top-level error handling (a failure should ideally still send a "partial" email or alert, not silently die).
3. **`Dockerfile`** (Step 7) — python:3.12-slim base, install requirements, run main.py.
4. **`.github/workflows/daily.yml`** (Step 8) — cron schedule + `workflow_dispatch` for manual test runs; inject secrets as env vars.
5. **Secrets** (Step 9) — add ANTHROPIC_API_KEY, TAVILY_API_KEY, RESEND_API_KEY, recipient email to GitHub repo secrets.
6. **Go-live** — run manually via workflow_dispatch a few times, check the email, then enable cron.

## First things to do in Cowork

1. Confirm all files are present in this folder.
2. Krish: obtain the 3 API keys (Anthropic, Tavily, Resend).
3. Local real-data test (the sandbox couldn't do this):
   ```bash
   pip install -r requirements.txt
   export ANTHROPIC_API_KEY="..."   export TAVILY_API_KEY="..."
   python3 data_fetch.py     # verifies Yahoo Finance reachable + sector lookup
   python3 analysis.py       # verifies real Claude output quality
   ```
4. Then continue building from "What's left" (Step 6 onward).

## Known caveats to watch

- ETFs (e.g. VOO) often return no sector from yfinance → bucketed "Unknown". Expected; handled.
- VaR is a rough gauge only (zero-correlation assumption understates risk). Never present as precise.
- yfinance is unofficial and can break/rate-limit; may need a fallback data source someday.
- Ticker format must match Yahoo (e.g. BRK-B not BRK.B).
