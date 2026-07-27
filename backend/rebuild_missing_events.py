"""
Rebuild events for tickers missing from the recovered correlation_data.json.

Collects USASpending contracts + MuckRock FOIA, deduplicates against
the current dataset (no events added if ticker+date already present ±1 day),
and immediately backfills 1d/3d/7d/30d returns + market data + NLP scores.

Run from backend/:
    source venv/bin/activate && python rebuild_missing_events.py
"""
import json
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, str(Path(__file__).parent))
from services.correlation_tracker import tracker
from services.foia_engine import foia_engine
from services.usaspending_service import usaspending_service

DATA_FILE = Path("correlation_data.json")

# All 73 tickers — re-collect for any with <50 events or completely missing
TICKERS = [
    {"ticker": "ADBE", "company": "Adobe"},
    {"ticker": "AMD",  "company": "Advanced Micro Devices"},
    {"ticker": "AVGO", "company": "Broadcom"},
    {"ticker": "AXP",  "company": "American Express"},
    {"ticker": "BLK",  "company": "BlackRock"},
    {"ticker": "C",    "company": "Citigroup"},
    {"ticker": "CAT",  "company": "Caterpillar"},
    {"ticker": "COST", "company": "Costco"},
    {"ticker": "DIS",  "company": "Walt Disney"},
    {"ticker": "EOG",  "company": "EOG Resources"},
    {"ticker": "FDX",  "company": "FedEx"},
    {"ticker": "GE",   "company": "General Electric"},
    {"ticker": "HON",  "company": "Honeywell"},
    {"ticker": "HWM",  "company": "Howmet Aerospace"},
    {"ticker": "IBM",  "company": "IBM"},
    {"ticker": "LOW",  "company": "Lowes"},
    {"ticker": "MMM",  "company": "3M"},
    {"ticker": "MS",   "company": "Morgan Stanley"},
    {"ticker": "NKE",  "company": "Nike"},
    {"ticker": "PLTR", "company": "Palantir"},
    {"ticker": "SBUX", "company": "Starbucks"},
    {"ticker": "SLB",  "company": "SLB Schlumberger"},
    {"ticker": "T",    "company": "AT&T"},
    {"ticker": "TGT",  "company": "Target"},
    {"ticker": "TMUS", "company": "T-Mobile"},
    {"ticker": "UPS",  "company": "United Parcel Service"},
    {"ticker": "VZ",   "company": "Verizon"},
    {"ticker": "WFC",  "company": "Wells Fargo"},
    {"ticker": "WMT",  "company": "Walmart"},
    # Under-represented tickers
    {"ticker": "CRM",  "company": "Salesforce"},
    {"ticker": "NVDA", "company": "Nvidia"},
    {"ticker": "BAC",  "company": "Bank of America"},
    {"ticker": "LLY",  "company": "Eli Lilly"},
    {"ticker": "UNH",  "company": "UnitedHealth"},
]

_price_cache = {}
_spy_cache   = {}
_vix_cache   = {}
_vader       = SentimentIntensityAnalyzer()


def _safe(v):
    if v is None: return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def _fetch(symbol, target_date, window=5):
    key = f"{symbol}_{target_date.strftime('%Y-%m-%d')}"
    cache = _spy_cache if symbol in ("SPY", "^VIX") else _price_cache
    if key in cache:
        return cache[key]
    start = (target_date - timedelta(days=window + 3)).strftime("%Y-%m-%d")
    end   = (target_date + timedelta(days=window + 3)).strftime("%Y-%m-%d")
    try:
        hist = yf.Ticker(symbol).history(start=start, end=end)
        if hist.empty:
            cache[key] = None
            return None
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        closest = min(hist.index, key=lambda d: abs((d.to_pydatetime() - target_date).days))
        price = _safe(float(hist.loc[closest, "Close"]))
        cache[key] = price
        return price
    except Exception:
        cache[key] = None
        return None


def _build_existing_index():
    """Build set of (ticker, date_str) for fast deduplication."""
    index = {}
    for e in tracker.data["events"]:
        t = e.get("ticker", "")
        ds = e.get("event_date", "")[:10]
        index.setdefault(t, set()).add(ds)
    return index


def _is_duplicate(existing_index, ticker, event_date):
    dates = existing_index.get(ticker, set())
    for delta in range(-1, 2):
        d = (event_date + timedelta(days=delta)).strftime("%Y-%m-%d")
        if d in dates:
            return True
    return False


def _backfill(event_id, ticker, event_date, title, existing_index):
    """Fill price returns, market data, and NLP for a new event."""
    p0 = _fetch(ticker, event_date)
    if p0 is None or p0 == 0:
        return False

    for ev in tracker.data["events"]:
        if ev["event_id"] != event_id:
            continue

        ev["price_0d"] = p0
        for days in [1, 3, 7, 30]:
            ph = _fetch(ticker, event_date + timedelta(days=days))
            if ph:
                ev[f"price_{days}d"] = ph
                ev[f"return_{days}d"] = _safe((ph - p0) / p0 * 100)

        pm3 = _fetch(ticker, event_date - timedelta(days=3))
        if pm3 and pm3 != 0:
            ev["stock_momentum_3d"] = _safe((p0 - pm3) / pm3 * 100)

        spy0   = _fetch("SPY",  event_date)
        spym3  = _fetch("SPY",  event_date - timedelta(days=3))
        spym90 = _fetch("SPY",  event_date - timedelta(days=90))
        vix    = _fetch("^VIX", event_date)

        if spy0 and spym3 and spym3 != 0:
            ev["market_momentum_3d"] = _safe((spy0 - spym3) / spym3 * 100)
        if spy0 and spym90 and spym90 != 0:
            ev["market_regime"] = 1 if (spy0 - spym90) / spym90 > 0 else 0
        else:
            ev["market_regime"] = 1

        if vix is not None:
            ev["vix_level"] = vix

        sm = ev.get("stock_momentum_3d") or 0.0
        mm = ev.get("market_momentum_3d") or 0.0
        ev["relative_momentum"] = _safe(sm - mm)

        vs = _vader.polarity_scores(title)
        compound  = vs["compound"]
        nlp_score = round((compound + 1.0) / 2.0 * 100.0, 2)
        ev["signal"] = {
            "signal_score":        nlp_score,
            "nlp_sentiment_score": nlp_score,
            "vader_compound":      round(compound, 4),
            "vader_positive":      round(vs["pos"], 4),
            "vader_negative":      round(vs["neg"], 4),
            "vader_neutral":       round(vs["neu"], 4),
        }
        break

    tracker._save_data()
    # Update dedup index
    existing_index.setdefault(ticker, set()).add(event_date.strftime("%Y-%m-%d"))
    return True


def collect_contracts(ticker, company, existing_index, limit=30):
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

            if _is_duplicate(existing_index, ticker, event_date):
                continue

            title  = (c.get("description") or f"Federal Contract: {company}")[:200]
            award  = c.get("Award Amount") or c.get("total_obligated_amount") or 0

            event_id = tracker.track_event(
                ticker=ticker,
                event_type="contract",
                event_title=title,
                event_date=event_date,
                source="USAspending.gov",
                url=c.get("usaspending_permalink", ""),
            )
            for ev in tracker.data["events"]:
                if ev["event_id"] == event_id:
                    ev["Award Amount"] = award
                    break

            ok = _backfill(event_id, ticker, event_date, title, existing_index)
            if ok:
                count += 1
                print(f"    ✓ contract {event_date.date()} ${award:,.0f}")
            time.sleep(0.2)
    except Exception as e:
        print(f"    ✗ contract error: {e}")
    return count


def collect_foia(ticker, company, existing_index, limit=20):
    count = 0
    try:
        docs = foia_engine.get_foia_documents_for_ticker(ticker, company)
        for doc in docs[:limit]:
            date_str = (doc.get("datetime_done") or doc.get("datetime_submitted") or "")
            if not date_str:
                continue
            try:
                event_date = datetime.fromisoformat(date_str[:10])
            except Exception:
                continue

            if _is_duplicate(existing_index, ticker, event_date):
                continue

            title = (doc.get("title") or f"FOIA: {company}")[:200]
            event_id = tracker.track_event(
                ticker=ticker,
                event_type="FOIA",
                event_title=title,
                event_date=event_date,
                source="MuckRock FOIA",
                url=doc.get("absolute_url", ""),
            )
            ok = _backfill(event_id, ticker, event_date, title, existing_index)
            if ok:
                count += 1
                print(f"    ✓ FOIA  {event_date.date()}  {title[:55]}")
            time.sleep(0.2)
    except Exception as e:
        print(f"    ✗ FOIA error: {e}")
    return count


def main():
    before         = len(tracker.data["events"])
    existing_index = _build_existing_index()

    print(f"\n{'='*60}")
    print(f"  Rebuild Missing Events — {len(TICKERS)} tickers")
    print(f"  Events before: {before:,}")
    print(f"{'='*60}\n")

    total_new = 0
    for i, item in enumerate(TICKERS):
        ticker  = item["ticker"]
        company = item["company"]
        cur = len(existing_index.get(ticker, set()))
        print(f"\n[{i+1}/{len(TICKERS)}] {company} ({ticker})  current={cur}")

        c = collect_contracts(ticker, company, existing_index, limit=100)
        f = collect_foia(ticker, company, existing_index, limit=20)
        print(f"  → +{c} contracts  +{f} FOIA")
        total_new += c + f
        time.sleep(2)

    after = len(tracker.data["events"])
    print(f"\n{'='*60}")
    print(f"  Done. Events: {before:,} → {after:,}  (+{after - before} total)")
    print(f"  New events with full price data: {total_new}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
