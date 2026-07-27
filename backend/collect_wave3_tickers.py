"""
Wave 3 data collection — ~20 new tickers with high government exposure
not yet in the dataset (managed care, biotech/BARDA, defense niche,
healthcare services, industrial gov-IT).

Sources per ticker:
  1. SEC EDGAR 8-K filings  (limit=150)
  2. USASpending.gov contracts (limit=150)

Run from backend/:
    source venv/bin/activate && python collect_wave3_tickers.py
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

NEW_TICKERS_W3 = [
    # Large managed-care (Medicare Advantage / Medicaid — huge regulatory surface)
    {"ticker": "ELV",  "company": "Elevance Health"},
    {"ticker": "HCA",  "company": "HCA Healthcare"},
    {"ticker": "MCK",  "company": "McKesson Corp"},

    # Medical devices / orthopedics (VA / DoD procurement)
    {"ticker": "SYK",  "company": "Stryker Corp"},
    {"ticker": "ISRG", "company": "Intuitive Surgical"},
    {"ticker": "ZBH",  "company": "Zimmer Biomet"},

    # Diagnostics / lab services (CDC, NIH, DoD lab contracts)
    {"ticker": "DGX",  "company": "Quest Diagnostics"},
    {"ticker": "LH",   "company": "Labcorp"},
    {"ticker": "ILMN", "company": "Illumina"},

    # GE HealthCare (VA hospitals, DoD imaging)
    {"ticker": "GEHC", "company": "GE HealthCare Technologies"},

    # Defense niche — very high DoD contract concentration
    {"ticker": "AVAV", "company": "AeroVironment"},
    {"ticker": "TXT",  "company": "Textron"},
    {"ticker": "CW",   "company": "Curtiss-Wright"},
    {"ticker": "MOOG", "company": "Moog Inc"},
    {"ticker": "HWM",  "company": "Howmet Aerospace"},

    # Biotech / BARDA / NIH funded
    {"ticker": "BNTX", "company": "BioNTech"},
    {"ticker": "HAL",  "company": "Halliburton"},

    # Gov-IT / analytics / simulation
    {"ticker": "CDNS", "company": "Cadence Design Systems"},
    {"ticker": "ANSS", "company": "ANSYS"},
    {"ticker": "VRSK", "company": "Verisk Analytics"},
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


def collect_8k(ticker_sym, limit=150):
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
            print(f"    + 8-K {event_date.date()}  {title[:60]}")
        time.sleep(0.3)

    return count


def collect_contracts(ticker_sym, company, existing, limit=150):
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
                print(f"    + contract {event_date.date()} ${award:,.0f}")
            time.sleep(0.2)
    except Exception as e:
        print(f"    ! contract error: {e}")
    return count


def main():
    before = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  Wave 3 Collection — {len(NEW_TICKERS_W3)} companies")
    print(f"  Dataset before: {before:,} events")
    print(f"{'='*62}\n")

    total_new = 0
    for i, item in enumerate(NEW_TICKERS_W3):
        ticker_sym = item["ticker"]
        company    = item["company"]
        print(f"\n[{i+1}/{len(NEW_TICKERS_W3)}] {company} ({ticker_sym})")

        existing = _existing_dates(ticker_sym)
        print(f"  Existing events: {len(existing)}")

        n8k = collect_8k(ticker_sym, limit=150)
        existing = _existing_dates(ticker_sym)
        nc  = collect_contracts(ticker_sym, company, existing, limit=150)

        print(f"  => +{n8k} 8-K  +{nc} contracts  (subtotal +{n8k+nc})")
        total_new += n8k + nc
        time.sleep(2)

    after = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  Done. Dataset: {before:,} -> {after:,}  (+{after - before} events)")
    print(f"  Events with full price data backfilled: {total_new}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
