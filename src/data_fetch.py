"""
data_fetch.py

Pulls daily market data for every holding in portfolio.json:
- current price, day change %, 52-week high/low, P/E ratio, recent headlines.

Design notes:
- Batches all tickers into a single yfinance call instead of one-per-ticker.
- Each ticker is wrapped individually so one bad/delisted symbol doesn't
  crash the whole pipeline -- it just gets flagged and skipped.
- News pulled from yfinance's built-in .news field; web_enrich.py adds more.
"""

import json
import yfinance as yf


def load_portfolio(path: str = "portfolio.json") -> list[dict]:
    """Read portfolio.json and return the list of holdings."""
    with open(path, "r") as f:
        data = json.load(f)
    return data["holdings"]


def fetch_news(ticker_obj, max_headlines: int = 2) -> list[str]:
    """Pull a couple of recent headline titles for a ticker."""
    try:
        news_items = ticker_obj.news or []
        headlines = []
        for item in news_items[:max_headlines]:
            title = item.get("content", {}).get("title") or item.get("title")
            if title:
                headlines.append(title)
        return headlines
    except Exception:
        return []


def fetch_holding_data(holding: dict, ticker_obj) -> dict:
    """Build a data record for a single holding (portfolio entry + live data)."""
    ticker = holding["ticker"]
    try:
        info = ticker_obj.info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose")

        day_change_pct = None
        if current_price is not None and prev_close:
            day_change_pct = round((current_price - prev_close) / prev_close * 100, 2)

        gain_loss_pct = None
        if current_price is not None and holding.get("cost_basis"):
            gain_loss_pct = round(
                (current_price - holding["cost_basis"]) / holding["cost_basis"] * 100, 2
            )

        return {
            "ticker": ticker,
            "shares": holding["shares"],
            "cost_basis": holding["cost_basis"],
            "current_price": current_price,
            "day_change_pct": day_change_pct,
            "gain_loss_pct": gain_loss_pct,
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "pe_ratio": info.get("trailingPE"),
            "sector": info.get("sector"),  # enables risk.py concentration analysis
            "headlines": fetch_news(ticker_obj),
            "fetch_error": None,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "shares": holding.get("shares"),
            "cost_basis": holding.get("cost_basis"),
            "current_price": None,
            "day_change_pct": None,
            "gain_loss_pct": None,
            "fifty_two_week_low": None,
            "fifty_two_week_high": None,
            "pe_ratio": None,
            "headlines": [],
            "fetch_error": str(e),
        }


def fetch_all_holdings_data(portfolio_path: str = "portfolio.json") -> list[dict]:
    """Load the portfolio and return enriched data for every holding."""
    holdings = load_portfolio(portfolio_path)
    tickers_str = " ".join(h["ticker"] for h in holdings)
    batch = yf.Tickers(tickers_str)

    results = []
    for holding in holdings:
        ticker_obj = batch.tickers.get(holding["ticker"])
        if ticker_obj is None:
            results.append({**holding, "fetch_error": "Ticker not found", "headlines": []})
            continue
        results.append(fetch_holding_data(holding, ticker_obj))
    return results


if __name__ == "__main__":
    data = fetch_all_holdings_data()
    print(json.dumps(data, indent=2))
