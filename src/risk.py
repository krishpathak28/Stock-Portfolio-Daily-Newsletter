"""
risk.py

Portfolio-level risk metrics: sector concentration, parametric Value-at-Risk
(VaR), and total P&L. Adapted (rewritten clean, dependency-free) from the
RiskService in wshobson/maverick-mcp (MIT License) -- credit to that project
for the VaR/concentration approach and threshold constants.

WHY THIS EXISTS:
The rest of the pipeline reasons QUALITATIVELY (Claude writing about each
holding). This module adds QUANTITATIVE portfolio-level context -- the kind
of numbers that separate an analyst report from a newsletter. These feed the
Claude prompt as standing portfolio context, NOT as daily "news" (VaR and
concentration barely move day-to-day; they're framing, not headlines).

HONEST LIMITATIONS (documented so nobody over-trusts the output):
- VaR here is a SIMPLIFIED parametric estimate. It assumes a flat per-position
  daily volatility and ZERO correlation between holdings. Real portfolios have
  correlated positions (esp. within a sector), so this UNDERSTATES true risk.
  It's a rough directional gauge, not a precise risk figure. maverick-mcp makes
  the same simplification; we keep it but improve it slightly by letting the
  per-position vol be overridden from real data if available.
- Concentration is only as good as the sector labels. Missing sectors get
  bucketed as "Unknown", which will understate real concentration.

No third-party dependencies -- pure standard library (math only).
"""

import math


# Parametric VaR z-scores (one-tailed, standard normal).
_Z_95 = 1.645
_Z_99 = 2.326

# Concentration alert thresholds (fraction of total portfolio value).
# Borrowed from maverick-mcp's constants -- sensible retail defaults.
SECTOR_WARN_PCT = 0.30       # >30% in one sector = worth flagging
SECTOR_CRITICAL_PCT = 0.50   # >50% in one sector = heavy concentration

# Default assumed daily volatility per position when we have nothing better.
_DEFAULT_DAILY_VOL = 0.02  # 2%


def _position_value(pos: dict) -> float:
    """Market value of a single position."""
    return float(pos.get("shares") or 0) * float(pos.get("current_price") or 0)


def _estimate_portfolio_std(positions: list[dict], total_value: float) -> float:
    """
    Estimate simplified portfolio daily standard deviation.

    Assumes a per-position daily vol (2% default, or a position's own recent
    vol if provided under 'daily_vol') and ZERO cross-correlation. This is a
    diversification-adjusted std -- it will understate real risk because real
    holdings are correlated. Directional gauge only.
    """
    if total_value <= 0 or not positions:
        return _DEFAULT_DAILY_VOL

    variance = 0.0
    for pos in positions:
        weight = _position_value(pos) / total_value
        vol = float(pos.get("daily_vol") or _DEFAULT_DAILY_VOL)
        variance += (weight * vol) ** 2
    return math.sqrt(variance)


def compute_risk_metrics(holdings_data: list[dict]) -> dict:
    """
    Main entry point. Takes the enriched holdings data (same shape produced by
    data_fetch.py: ticker, shares, cost_basis, current_price, and optionally
    sector) and returns portfolio-level risk metrics.

    Returns a dict with:
      - total_value, total_pnl, total_pnl_pct, position_count
      - sector_concentration: {sector: fraction}
      - max_sector, max_sector_pct, concentration_flag
      - var_95, var_99  (1-day parametric VaR, in dollars)
      - notes: list of human-readable flags for the prompt
    """
    # Only include holdings that actually have a price (skip failed fetches).
    positions = [
        h for h in holdings_data
        if not h.get("fetch_error") and h.get("current_price") is not None
    ]

    if not positions:
        return {
            "total_value": 0.0, "total_pnl": 0.0, "total_pnl_pct": 0.0,
            "position_count": 0, "sector_concentration": {},
            "max_sector": None, "max_sector_pct": 0.0,
            "concentration_flag": "none", "var_95": 0.0, "var_99": 0.0,
            "notes": ["No priced positions available today."],
        }

    total_value = sum(_position_value(p) for p in positions)
    total_cost = sum(
        float(p.get("shares") or 0) * float(p.get("cost_basis") or 0)
        for p in positions
    )
    total_pnl = total_value - total_cost
    total_pnl_pct = round(total_pnl / total_cost * 100, 2) if total_cost > 0 else 0.0

    # Sector concentration
    sector_values: dict[str, float] = {}
    for pos in positions:
        sector = pos.get("sector") or "Unknown"
        sector_values[sector] = sector_values.get(sector, 0.0) + _position_value(pos)

    sector_concentration = {
        s: round(v / total_value, 4) for s, v in sector_values.items()
    } if total_value > 0 else {}

    max_sector, max_sector_pct = (None, 0.0)
    if sector_concentration:
        max_sector = max(sector_concentration, key=sector_concentration.get)
        max_sector_pct = sector_concentration[max_sector]

    # Concentration flag
    if max_sector_pct >= SECTOR_CRITICAL_PCT:
        concentration_flag = "critical"
    elif max_sector_pct >= SECTOR_WARN_PCT:
        concentration_flag = "warn"
    else:
        concentration_flag = "none"

    # Parametric 1-day VaR
    portfolio_std = _estimate_portfolio_std(positions, total_value)
    var_95 = round(_Z_95 * portfolio_std * total_value, 2)
    var_99 = round(_Z_99 * portfolio_std * total_value, 2)

    # Human-readable notes for the prompt
    notes = []
    if concentration_flag == "critical" and max_sector != "Unknown":
        notes.append(
            f"Heavy concentration: {round(max_sector_pct*100)}% of the portfolio "
            f"is in {max_sector}. Single-sector risk is elevated."
        )
    elif concentration_flag == "warn" and max_sector != "Unknown":
        notes.append(
            f"Notable concentration: {round(max_sector_pct*100)}% in {max_sector}."
        )
    if "Unknown" in sector_concentration and sector_concentration["Unknown"] > 0.2:
        notes.append(
            "Sector data missing for a meaningful share of the portfolio; "
            "concentration figures may understate true exposure."
        )

    return {
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": total_pnl_pct,
        "position_count": len(positions),
        "sector_concentration": sector_concentration,
        "max_sector": max_sector,
        "max_sector_pct": max_sector_pct,
        "concentration_flag": concentration_flag,
        "var_95": var_95,
        "var_99": var_99,
        "notes": notes,
    }


if __name__ == "__main__":
    import json
    sample = [
        {"ticker": "AAPL", "shares": 10, "cost_basis": 185.50, "current_price": 200.0, "sector": "Technology"},
        {"ticker": "MSFT", "shares": 5, "cost_basis": 380.0, "current_price": 420.0, "sector": "Technology"},
        {"ticker": "VOO", "shares": 5, "cost_basis": 410.0, "current_price": 415.0, "sector": "Diversified"},
    ]
    print(json.dumps(compute_risk_metrics(sample), indent=2))
