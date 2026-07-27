"""
Backfill real SPY momentum, VIX level, and market_regime for all events.

Fixes the hardcoded market_regime=1 / market_momentum_3d=0.0 values.
Adds vix_level as a new per-event field used as a model feature.

Strategy: batch-fetch full SPY and VIX history once, then look up dates
from the in-memory DataFrame — no per-event network calls.

Run from backend/:
    source venv/bin/activate && python backfill_market_data.py
"""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_FILE = Path("correlation_data.json")


def _safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def fetch_series(symbol, start, end):
    """Fetch full price history as a timezone-naive date→price dict."""
    print(f"  Fetching {symbol} {start} → {end} …")
    hist = yf.Ticker(symbol).history(start=start, end=end)
    if hist.empty:
        return {}
    hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
    return {ts.date(): float(hist.loc[ts, "Close"]) for ts in hist.index}


def closest_price(series, target_date, window=5):
    """Return price in series closest to target_date within ±window calendar days."""
    for delta in range(0, window + 1):
        for sign in [0, -1, 1]:
            d = (target_date + timedelta(days=delta * sign)).date()
            if d in series:
                return _safe(series[d])
    return None


def main():
    data   = json.load(open(DATA_FILE))
    events = data["events"]

    # Determine date range
    dates = []
    for e in events:
        ds = e.get("event_date", "")
        if ds:
            try:
                dates.append(datetime.fromisoformat(ds[:19]))
            except Exception:
                pass
    if not dates:
        print("No events with dates found.")
        return

    start_str = (min(dates) - timedelta(days=100)).strftime("%Y-%m-%d")
    end_str   = (max(dates) + timedelta(days=40)).strftime("%Y-%m-%d")
    print(f"\nDate range: {start_str} → {end_str}")

    # Batch-fetch both series
    spy_series = fetch_series("SPY",  start_str, end_str)
    vix_series = fetch_series("^VIX", start_str, end_str)
    print(f"  SPY: {len(spy_series)} trading days, VIX: {len(vix_series)} trading days")

    needs = [
        e for e in events
        if e.get("market_momentum_3d") is None
        or e.get("market_regime") is None
        or e.get("vix_level") is None
    ]
    print(f"\nEvents needing market backfill: {len(needs):,} / {len(events):,}")

    updated = 0
    for event in events:
        missing_mom    = event.get("market_momentum_3d") is None
        missing_regime = event.get("market_regime") is None
        missing_vix    = event.get("vix_level") is None
        if not (missing_mom or missing_regime or missing_vix):
            continue

        ds = event.get("event_date", "")
        if not ds:
            continue
        try:
            dt = datetime.fromisoformat(ds[:19])
        except Exception:
            continue

        # SPY 3-day momentum
        if missing_mom or missing_regime:
            spy_now = closest_price(spy_series, dt)
            spy_m3  = closest_price(spy_series, dt - timedelta(days=3))
            spy_m90 = closest_price(spy_series, dt - timedelta(days=90))

            if spy_now and spy_m3 and spy_m3 != 0:
                event["market_momentum_3d"] = _safe((spy_now - spy_m3) / spy_m3 * 100)

            if spy_now and spy_m90 and spy_m90 != 0:
                event["market_regime"] = 1 if (spy_now - spy_m90) / spy_m90 > 0 else 0
            elif event.get("market_regime") is None:
                event["market_regime"] = 1  # default bull

        # VIX level
        if missing_vix:
            vix = closest_price(vix_series, dt)
            if vix is not None:
                event["vix_level"] = vix

        # Recalculate relative_momentum with real market data
        sm = event.get("stock_momentum_3d") or 0.0
        mm = event.get("market_momentum_3d") or 0.0
        event["relative_momentum"] = _safe(sm - mm)

        updated += 1

    print(f"\nUpdated {updated:,} events — saving…")
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

    # Sanity check
    regime_vals = [e.get("market_regime") for e in events]
    vix_vals    = [e["vix_level"] for e in events if e.get("vix_level") is not None]
    mom_vals    = [e["market_momentum_3d"] for e in events if e.get("market_momentum_3d") is not None]
    print(f"\n  market_regime  — bull(1): {regime_vals.count(1)}, bear(0): {regime_vals.count(0)}, "
          f"None: {regime_vals.count(None)}")
    print(f"  vix_level      — {len(vix_vals):,} filled, "
          f"avg={round(sum(vix_vals)/len(vix_vals),1) if vix_vals else 'n/a'}")
    print(f"  market_mom_3d  — {len(mom_vals):,} filled")
    print("\nDone.")


if __name__ == "__main__":
    main()
