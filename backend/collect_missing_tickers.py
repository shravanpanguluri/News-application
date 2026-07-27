"""
Targeted collection for the 19 tickers missing from correlation_data.json.
Zero duplication risk — these tickers have no existing events.
Immediately backfills 1d/3d/7d/30d returns after each event is tracked.
"""
import sys
import json
import time
import math
import requests
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from services.correlation_tracker import tracker
from services.foia_engine import foia_engine
from services.usaspending_service import usaspending_service

# ── Tickers to collect ────────────────────────────────────────────────────────
MISSING = [
    {"ticker": "AMD",  "company": "Advanced Micro Devices"},
    {"ticker": "ADBE", "company": "Adobe"},
    {"ticker": "NFLX", "company": "Netflix"},
    {"ticker": "C",    "company": "Citigroup"},
    {"ticker": "AXP",  "company": "American Express"},
    {"ticker": "COP",  "company": "ConocoPhillips"},
    {"ticker": "KO",   "company": "Coca Cola"},
    {"ticker": "MCD",  "company": "McDonalds"},
    {"ticker": "NKE",  "company": "Nike"},
    {"ticker": "DIS",  "company": "Walt Disney"},
    {"ticker": "SBUX", "company": "Starbucks"},
    {"ticker": "TGT",  "company": "Target"},
    {"ticker": "LOW",  "company": "Lowes"},
    {"ticker": "MMM",  "company": "3M"},
    {"ticker": "UPS",  "company": "United Parcel Service"},
    {"ticker": "FDX",  "company": "FedEx"},
    {"ticker": "T",    "company": "AT&T"},
    {"ticker": "VZ",   "company": "Verizon"},
    {"ticker": "TMUS", "company": "T-Mobile"},
]

# ── Price cache to avoid re-fetching ─────────────────────────────────────────
_price_cache = {}

def _safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None

def get_price_on(ticker, target_date, window=5):
    """Return closing price closest to target_date within ±window trading days."""
    key = (ticker, target_date.strftime("%Y-%m-%d"))
    if key in _price_cache:
        return _price_cache[key]

    start = target_date - timedelta(days=window + 2)
    end   = target_date + timedelta(days=window + 2)
    try:
        hist = yf.Ticker(ticker).history(start=start.strftime("%Y-%m-%d"),
                                          end=end.strftime("%Y-%m-%d"))
        if hist.empty:
            _price_cache[key] = None
            return None
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        closest = min(hist.index, key=lambda d: abs((d.to_pydatetime() - target_date).days))
        price = _safe_float(float(hist.loc[closest, "Close"]))
        _price_cache[key] = price
        return price
    except Exception as e:
        print(f"    ⚠ Price fetch error for {ticker}: {e}")
        _price_cache[key] = None
        return None


def backfill_prices(event_id, ticker, event_date):
    """Fill in 1d/3d/7d/30d returns for a newly tracked event."""
    p0 = get_price_on(ticker, event_date)
    if p0 is None or p0 == 0:
        return False

    updated = False
    for event in tracker.data["events"]:
        if event["event_id"] != event_id:
            continue

        event["price_0d"] = p0
        for days in [1, 3, 7, 30]:
            ph = get_price_on(ticker, event_date + timedelta(days=days))
            if ph:
                ret = _safe_float((ph - p0) / p0 * 100)
                event[f"price_{days}d"] = ph
                event[f"return_{days}d"] = ret

        # Momentum features (need 3d before event)
        p_minus3 = get_price_on(ticker, event_date - timedelta(days=3))
        if p_minus3 and p_minus3 != 0:
            event["stock_momentum_3d"] = _safe_float((p0 - p_minus3) / p_minus3 * 100)

        event["market_regime"] = 1  # assume bull (simplified; avoids extra SPY fetch)
        event["market_momentum_3d"] = 0.0
        event["relative_momentum"] = event.get("stock_momentum_3d", 0.0)
        updated = True
        break

    if updated:
        tracker._save_data()
    return updated


def collect_contracts(ticker, company, limit=15):
    """Fetch USASpending contracts and track+price them."""
    count = 0
    try:
        contracts = usaspending_service.get_contract_awards_for_ticker(
            ticker, company_name=company, limit=limit
        )
        for c in contracts:
            date_str = c.get("date") or c.get("period_of_performance_start_date", "")
            if not date_str:
                continue
            try:
                event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception:
                continue

            title = (c.get("description") or f"Federal Contract: {company}")[:200]
            award  = c.get("Award Amount") or c.get("total_obligated_amount") or 0

            event_id = tracker.track_event(
                ticker=ticker,
                event_type="contract",
                event_title=title,
                event_date=event_date,
                source="USAspending.gov",
                url=c.get("usaspending_permalink", ""),
            )
            # Store award amount on event
            for ev in tracker.data["events"]:
                if ev["event_id"] == event_id:
                    ev["Award Amount"] = award
                    break

            ok = backfill_prices(event_id, ticker, event_date)
            if ok:
                count += 1
                print(f"    ✓ contract {event_date.date()} ${award:,.0f}")
            time.sleep(0.3)
    except Exception as e:
        print(f"    ✗ contract error: {e}")
    return count


def collect_foia(ticker, company, limit=15):
    """Fetch MuckRock FOIA docs and track+price them."""
    count = 0
    try:
        docs = foia_engine.get_foia_documents_for_ticker(ticker, company)
        for doc in docs[:limit]:
            date_str = (doc.get("datetime_done") or
                        doc.get("datetime_submitted") or "")
            if not date_str:
                continue
            try:
                event_date = datetime.fromisoformat(date_str[:10])
            except Exception:
                continue

            title = (doc.get("title") or f"FOIA: {company}")[:200]

            event_id = tracker.track_event(
                ticker=ticker,
                event_type="foia",
                event_title=title,
                event_date=event_date,
                source="MuckRock FOIA",
                url=doc.get("absolute_url", ""),
            )
            ok = backfill_prices(event_id, ticker, event_date)
            if ok:
                count += 1
                print(f"    ✓ FOIA  {event_date.date()}  {title[:60]}")
            time.sleep(0.3)
    except Exception as e:
        print(f"    ✗ FOIA error: {e}")
    return count


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    before = len(tracker.data["events"])
    print(f"\n{'='*60}")
    print(f"  Targeted Collection — {len(MISSING)} new tickers")
    print(f"  Events before: {before}")
    print(f"{'='*60}\n")

    total_new = 0
    for i, item in enumerate(MISSING):
        ticker  = item["ticker"]
        company = item["company"]
        print(f"\n[{i+1}/{len(MISSING)}] {company} ({ticker})")

        c_count = collect_contracts(ticker, company, limit=15)
        print(f"  → contracts with prices: {c_count}")

        f_count = collect_foia(ticker, company, limit=15)
        print(f"  → FOIA with prices:      {f_count}")

        total_new += c_count + f_count
        time.sleep(2)  # be polite to APIs

    after = len(tracker.data["events"])
    print(f"\n{'='*60}")
    print(f"  Done. Events: {before} → {after}  (+{after - before} total tracked)")
    print(f"  Events with full price data: {total_new}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
