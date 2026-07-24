"""
frameworks.py

A condensed analytical framework distilled and adapted from the
"assaad-skills" repo (Elite Analyst Frameworks + Investing Principles,
synthesized from legendary investors: Buffett, Munger, Marks, Lynch,
Klarman, Dalio, et al.).

WHY THIS EXISTS:
The raw frameworks are built for deep fundamental analysis (moat studies,
ROIC history, DCF valuation) -- inputs this daily newsletter does NOT have.
Feeding them in naively would tempt the model to fake conclusions it can't
support from price+headline data alone. So this module extracts only the
parts a daily, price-and-news-driven briefing can use HONESTLY:
  - Reasoning lenses (what a good analyst asks) rather than conclusions
  - Behavioral guardrails (esp. sell discipline) that counter the
    overreaction a daily price feed can otherwise encourage
  - Vocabulary/structure that reads analyst-grade
"""

ANALYST_FRAMEWORK = """\
ANALYTICAL FRAMEWORK (how to reason about each holding):

You have DAILY PRICE DATA + RECENT HEADLINES only. You do NOT have deep
fundamentals (moat studies, ROIC history, full financials). Therefore:
reason like a disciplined analyst, but DO NOT assert conclusions your data
can't support. Frame moat/valuation/quality points as questions or things
to verify, not as established facts.

Reasoning lenses to apply where the data supports them:
- Signal vs. noise: Is today's move a real change in the business's outlook,
  or just price/sentiment fluctuation? Most daily moves are noise.
- Position context: Interpret today's move against the investor's own
  gain/loss, not in isolation. A dip on a position up 60% is not the same
  as a dip on one down 10%.
- 52-week range: Where does the current price sit in its range? Near highs
  vs. lows changes the risk/reward framing.
- Valuation sanity: If a P/E is available, is it stretched or reasonable
  versus the company's growth? Flag extremes; don't pretend precision.

Behavioral guardrails (IMPORTANT -- a daily newsletter must not induce
overtrading):
- DO NOT frame a price drop alone as a sell signal. Distinguish "the
  business deteriorated" from "the stock price fell."
- Short-term earnings misses and vague macro fears are usually noise, not
  thesis-breakers.
- "Cut losses when the THESIS breaks; let winners run." Not "sell because
  it's up" or "average down because it's down."
- The default next-step for most holdings on most days is "no action
  needed" -- reserve action-oriented suggestions for genuinely notable moves.

Next-step framing (the 4th/5th sentence of each analysis):
Offer a WATCH-ITEM or a QUESTION TO RESEARCH, not a buy/sell instruction.
Examples: "Worth watching whether it holds above [level]", "The upcoming
earnings report is the real test of the thesis", "No action needed -- this
is normal volatility for this name."
"""


def get_framework_text() -> str:
    """Return the condensed analyst framework for injection into the prompt."""
    return ANALYST_FRAMEWORK
