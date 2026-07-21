"""Verify the integrated pipeline: framework injection + web context + parsing."""
import json
from unittest.mock import MagicMock, patch
import analysis
import web_enrich
import frameworks

SAMPLE = [
    {"ticker": "AAPL", "shares": 10, "cost_basis": 185.50, "current_price": 200.0,
     "day_change_pct": 2.56, "gain_loss_pct": 7.82, "fifty_two_week_low": 164.08,
     "fifty_two_week_high": 237.49, "pe_ratio": 31.2, "headlines": ["Apple news"],
     "web_context": ["Apple unveils AI features — holiday catalyst"], "fetch_error": None},
]

def test_framework_is_injected():
    prompt = analysis.build_prompt(SAMPLE)
    assert "ANALYTICAL FRAMEWORK" in prompt
    assert "Signal vs. noise" in prompt
    assert "do not turn a price drop" in prompt.lower() or "price drop alone" in prompt
    print("PASS: analyst framework injected into prompt")

def test_web_context_in_prompt():
    prompt = analysis.build_prompt(SAMPLE)
    assert "Apple unveils AI features" in prompt
    assert "web_context" in prompt
    print("PASS: web_context folded into the data block")

def test_web_enrich_skips_failed_fetch():
    failed = [{"ticker": "BAD", "fetch_error": "Ticker not found"}]
    result = web_enrich.enrich_with_web_search(failed)
    assert result[0]["web_context"] == []
    print("PASS: web enrichment skips tickers whose fetch failed (no wasted search)")

def test_web_enrich_no_key_returns_empty():
    with patch.dict("os.environ", {}, clear=True):
        snippets = web_enrich._search_provider("AAPL stock news")
    assert snippets == []
    print("PASS: missing TAVILY_API_KEY degrades gracefully to empty (no crash)")

def test_full_parse_with_mocked_api():
    fake = MagicMock()
    fake.content = [MagicMock(text=json.dumps({
        "portfolio_summary": "Mixed day across the book with tech leading.",
        "holdings": [{"ticker": "AAPL", "analysis": "Apple rose on product news and sits comfortably above your cost basis; worth watching the $200 level but no action needed today."}],
    }))]
    with patch("analysis.Anthropic") as MockA:
        c = MagicMock(); c.messages.create.return_value = fake; MockA.return_value = c
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}):
            result = analysis.run_analysis(SAMPLE)
    assert result["holdings"][0]["ticker"] == "AAPL"
    print("PASS: full run_analysis parses + validates a mocked API response")

if __name__ == "__main__":
    test_framework_is_injected()
    test_web_context_in_prompt()
    test_web_enrich_skips_failed_fetch()
    test_web_enrich_no_key_returns_empty()
    test_full_parse_with_mocked_api()
    print("\nAll integration tests passed.")
