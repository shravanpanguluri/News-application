"""
Collect events for new tickers not yet in the dataset.

Sources per ticker:
  1. SEC EDGAR 8-K filings  (limit=100)
  2. USASpending.gov contracts (limit=100)

Deduplicates against existing events. Backfills price returns +
SPY/VIX market data + VADER NLP in one pass per event.

Run from backend/:
    source venv/bin/activate && python collect_new_tickers.py
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
from services.sec_edgar_service import sec_edgar_service
from services.usaspending_service import usaspending_service

DATA_FILE    = Path("correlation_data.json")
TARGET_FORMS = {"8-K", "8-K/A"}

# New tickers — high government-contract / regulatory exposure
NEW_TICKERS = [
    # Semiconductors / Defense tech
    {"ticker": "QCOM",  "company": "Qualcomm"},
    {"ticker": "TXN",   "company": "Texas Instruments"},
    {"ticker": "AMAT",  "company": "Applied Materials"},
    # IT / Cloud services (large federal contracts)
    {"ticker": "DELL",  "company": "Dell Technologies"},
    {"ticker": "HPE",   "company": "Hewlett Packard Enterprise"},
    {"ticker": "ACN",   "company": "Accenture"},
    {"ticker": "SAIC",  "company": "Science Applications International"},
    # Healthcare / Medical devices (Medicare / DoD medical)
    {"ticker": "MDT",   "company": "Medtronic"},
    {"ticker": "ABT",   "company": "Abbott Laboratories"},
    {"ticker": "TMO",   "company": "Thermo Fisher Scientific"},
    {"ticker": "DHR",   "company": "Danaher"},
    {"ticker": "BSX",   "company": "Boston Scientific"},
    {"ticker": "SYF",   "company": "Synchrony Financial"},
    # Managed care / Medicaid / Medicare
    {"ticker": "HUM",   "company": "Humana"},
    {"ticker": "CI",    "company": "Cigna"},
    {"ticker": "CNC",   "company": "Centene"},
    {"ticker": "MOH",   "company": "Molina Healthcare"},
    # Pharma / Biotech (FDA actions, NIH grants)
    {"ticker": "REGN",  "company": "Regeneron Pharmaceuticals"},
    {"ticker": "VRTX",  "company": "Vertex Pharmaceuticals"},
    {"ticker": "BIIB",  "company": "Biogen"},
    {"ticker": "AZN",   "company": "AstraZeneca"},
    # Industrial / Defense-adjacent
    {"ticker": "DE",    "company": "Deere"},
    {"ticker": "EMR",   "company": "Emerson Electric"},
    {"ticker": "ETN",   "company": "Eaton"},
    {"ticker": "PH",    "company": "Parker Hannifin"},
    # Energy (federal leases, regulation)
    {"ticker": "COP",   "company": "ConocoPhillips"},
    {"ticker": "OXY",   "company": "Occidental Petroleum"},
    {"ticker": "PSX",   "company": "Phillips 66"},
    # Automotive (DoD vehicle contracts)
    {"ticker": "F",     "company": "Ford Motor"},
    {"ticker": "GM",    "company": "General Motors"},
]

_price_cache = {}
_vader       = SentimentIntensityAnalyzer()


def _safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def _get_price(symbol, target_date, window=5):
    key = f"{symbol}_{target_date.strftime('%Y-%m-%d')}"
    if key in _price_cache:
        return _price_cache[key]
    start = (target_date - timedelta(days=window + 3)).strftime("%Y-%m-%d")
    end   = (target_date + timedelta(days=window + 3)).strftime("%Y-%m-%d")
    try:
        hist = yf.Ticker(symbol).history(start=start, end=end)
        if hist.empty:
            _price_cache[key] = None
            return None
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        closest = min(hist.index, key=lambda d: abs((d.to_pydatetime() - target_date).days))
        price = _safe(float(hist.loc[closest, "Close"]))
        _price_cache[key] = price
        return price
    except Exception:
        _price_cache[key] = None
        return None


def _existing_dates(ticker_sym):
    return {
        e["event_date"][:10]
        for e in tracker.data["events"]
        if e["ticker"] == ticker_sym
    }


def _backfill(event_id, ticker_sym, event_date, title):
    p0 = _get_price(ticker_sym, event_date)
    if p0 is None or p0 == 0:
        return False

    for ev in tracker.data["events"]:
        if ev["event_id"] != event_id:
            continue

        ev["price_0d"] = p0
        for days in [1, 3, 7, 30]:
            ph = _get_price(ticker_sym, event_date + timedelta(days=days))
            if ph:
                ev[f"price_{days}d"] = ph
                ev[f"return_{days}d"] = _safe((ph - p0) / p0 * 100)

        pm3 = _get_price(ticker_sym, event_date - timedelta(days=3))
        if pm3 and pm3 != 0:
            ev["stock_momentum_3d"] = _safe((p0 - pm3) / pm3 * 100)

        spy0   = _get_price("SPY",  event_date)
        spym3  = _get_price("SPY",  event_date - timedelta(days=3))
        spym90 = _get_price("SPY",  event_date - timedelta(days=90))
        vix    = _get_price("^VIX", event_date)

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
    return True


def collect_8k(ticker_sym, limit=100):
    filings = sec_edgar_service.get_company_filings(ticker_sym, filing_type="8-K", limit=limit)
    if not filings:
        filings = sec_edgar_service.get_company_filings(ticker_sym, limit=limit)
        filings = [f for f in filings if f.get("form_type") in TARGET_FORMS]

    existing = _existing_dates(ticker_sym)
    count = 0

    for filing in filings:
        date_str = filing.get("filing_date", "")
        if not date_str:
            continue
        try:
            event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception:
            continue

        nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
        if nearby & existing:
            continue

        form_type   = filing.get("form_type", "8-K")
        description = (filing.get("description") or "").strip()
        title = (f"SEC {form_type}: {description}" if description
                 else f"SEC {form_type} filing")[:200]
        url   = filing.get("filing_url") or filing.get("document_url") or ""

        event_id = tracker.track_event(
            ticker=ticker_sym,
            event_type="sec_filing",
            event_title=title,
            event_date=event_date,
            source="SEC EDGAR",
            url=url,
        )
        if _backfill(event_id, ticker_sym, event_date, title):
            count += 1
            existing.add(date_str[:10])
            print(f"    ✓ 8-K {event_date.date()}  {title[:60]}")
        time.sleep(0.3)

    return count


def collect_contracts(ticker_sym, company, existing, limit=100):
    count = 0
    try:
        contracts = usaspending_service.get_contract_awards_for_ticker(
            ticker_sym, company_name=company, limit=limit
        )
        for c in contracts:
            date_str = c.get("date") or c.get("period_of_performance_start_date", "")
            if not date_str:
                continue
            try:
                event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception:
                continue

            nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
            if nearby & existing:
                continue

            title = (c.get("description") or f"Federal Contract: {company}")[:200]
            award = c.get("Award Amount") or c.get("total_obligated_amount") or 0

            event_id = tracker.track_event(
                ticker=ticker_sym,
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

            if _backfill(event_id, ticker_sym, event_date, title):
                count += 1
                existing.add(event_date.strftime("%Y-%m-%d"))
                print(f"    ✓ contract {event_date.date()} ${award:,.0f}")
            time.sleep(0.2)
    except Exception as e:
        print(f"    ✗ contract error: {e}")
    return count


def main():
    before = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  New Ticker Collection — {len(NEW_TICKERS)} companies")
    print(f"  Events before: {before:,}")
    print(f"{'='*62}\n")

    total_new = 0
    for i, item in enumerate(NEW_TICKERS):
        ticker_sym = item["ticker"]
        company    = item["company"]
        print(f"[{i+1}/{len(NEW_TICKERS)}] {company} ({ticker_sym})")

        existing = _existing_dates(ticker_sym)
        print(f"  Existing events: {len(existing)}")

        n8k = collect_8k(ticker_sym, limit=100)
        existing = _existing_dates(ticker_sym)   # refresh after 8-K adds
        nc  = collect_contracts(ticker_sym, company, existing, limit=100)

        print(f"  → +{n8k} 8-K  +{nc} contracts")
        total_new += n8k + nc
        time.sleep(2)

    after = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  Done. Events: {before:,} → {after:,}  (+{after - before})")
    print(f"  Events with full price data: {total_new}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
