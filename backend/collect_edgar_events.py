"""
Collect SEC EDGAR 8-K filings for all tickers in the dataset.

8-K filings are material event disclosures (earnings warnings, major contracts,
officer changes, FDA results, legal settlements) — higher-signal events than
generic federal contract awards.

Only adds events not already present (de-duplicates by ticker + date within ±1 day).

Run from backend/:
    source venv/bin/activate && python collect_edgar_events.py
"""
import json
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
sys.path.insert(0, str(Path(__file__).parent))
from services.correlation_tracker import tracker
from services.sec_edgar_service import sec_edgar_service
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DATA_FILE = Path("correlation_data.json")

# 8-K forms to collect (material event disclosures only)
TARGET_FORMS = {"8-K", "8-K/A"}

# All tickers currently in the dataset
TICKERS = [
    "AAPL", "ABBV", "ADBE", "AMD", "AMGN", "AMZN", "AVGO", "AXP",
    "BA", "BAC", "BAH", "BLK", "BMY", "C", "CACI", "CAT", "COST",
    "CRM", "CSCO", "CVS", "CVX", "DIS", "EOG", "FDX", "GD", "GE",
    "GILD", "GOOGL", "GS", "HD", "HII", "HON", "HWM", "IBM", "INTC",
    "ISRG", "JNJ", "JPM", "KTOS", "LDOS", "LHX", "LLY", "LMT", "LOW",
    "MA", "META", "MMM", "MRK", "MS", "MSFT", "NKE", "NOC", "NVDA",
    "ORCL", "PFE", "PG", "PLTR", "RTX", "SBUX", "SLB", "SYK", "T",
    "TDG", "TGT", "TMUS", "TSLA", "UNH", "UPS", "V", "VZ", "WFC",
    "WMT", "XOM",
]

# Include every ticker with a known SEC CIK mapping. The static list above is
# the original high-signal universe; the service mapping now contains later
# expansion tickers too. Preserve order while appending mapped tickers.
TICKERS = list(dict.fromkeys(TICKERS + sorted(sec_edgar_service._cik_mappings)))

_price_cache = {}
_vader = SentimentIntensityAnalyzer()
_YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def _get_price(ticker_sym, target_date, window=5):
    key = f"{ticker_sym}_{target_date.strftime('%Y-%m-%d')}"
    if key in _price_cache:
        return _price_cache[key]
    price = _get_price_yahoo_chart(ticker_sym, target_date, window)
    _price_cache[key] = price
    return price


def _get_price_yahoo_chart(ticker_sym, target_date, window=5):
    start_dt = target_date - timedelta(days=window + 3)
    end_dt = target_date + timedelta(days=window + 3)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_sym}"
        f"?period1={int(start_dt.timestamp())}"
        f"&period2={int(end_dt.timestamp())}"
        f"&interval=1d&events=history"
    )
    try:
        response = requests.get(url, headers=_YAHOO_HEADERS, timeout=15)
        response.raise_for_status()
        result = (response.json().get("chart", {}).get("result") or [None])[0]
        if not result:
            return None
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        rows = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            rows.append((datetime.fromtimestamp(ts), float(close)))
        if not rows:
            return None
        closest = min(rows, key=lambda item: abs((item[0] - target_date).days))
        return _safe(closest[1])
    except Exception:
        return None


def _existing_dates(ticker):
    """Return set of (ticker, date_str) pairs already in the dataset."""
    return {
        e.get("event_date", "")[:10]
        for e in tracker.data["events"]
        if e.get("ticker") == ticker and e.get("event_date")
    }


def _backfill(event_id, ticker, event_date, title):
    """Fill 1d/3d/7d/30d price returns and NLP scores."""
    p0 = _get_price(ticker, event_date)
    if p0 is None or p0 == 0:
        return False

    for ev in tracker.data["events"]:
        if ev.get("event_id") != event_id:
            continue

        ev["price_0d"] = p0
        for days in [1, 3, 7, 30]:
            ph = _get_price(ticker, event_date + timedelta(days=days))
            if ph:
                ev[f"price_{days}d"] = ph
                ev[f"return_{days}d"] = _safe((ph - p0) / p0 * 100)

        # Stock momentum
        pm3 = _get_price(ticker, event_date - timedelta(days=3))
        if pm3 and pm3 != 0:
            ev["stock_momentum_3d"] = _safe((p0 - pm3) / pm3 * 100)

        # SPY context
        spy0  = _get_price("SPY", event_date)
        spym3 = _get_price("SPY", event_date - timedelta(days=3))
        spym90 = _get_price("SPY", event_date - timedelta(days=90))
        vix   = _get_price("^VIX", event_date)

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

        # VADER NLP
        vs = _vader.polarity_scores(title)
        compound = vs["compound"]
        nlp_score = round((compound + 1.0) / 2.0 * 100.0, 2)
        ev["signal"] = {
            "signal_score":        nlp_score,
            "nlp_sentiment_score": nlp_score,
            "vader_compound":      round(compound, 4),
            "vader_positive":      round(vs["pos"], 4),
            "vader_negative":      round(vs["neg"], 4),
            "vader_neutral":       round(vs["neu"], 4),
        }

        updated = ev.get("return_7d") is not None
        tracker._save_data()
        return updated

    return False


def collect_8k(ticker, limit=20):
    """Fetch 8-K filings and track+backfill each."""
    filings = sec_edgar_service.get_company_filings(ticker, filing_type="8-K", limit=limit)
    if not filings:
        filings = sec_edgar_service.get_company_filings(ticker, limit=limit)
        filings = [f for f in filings if f.get("form_type") in TARGET_FORMS]

    existing = _existing_dates(ticker)
    count = 0

    for filing in filings:
        date_str = filing.get("filing_date", "")
        if not date_str:
            continue
        try:
            event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception:
            continue

        # Skip if we have an event for this ticker within 1 day (de-duplicate)
        nearby = {
            (event_date - timedelta(days=d)).strftime("%Y-%m-%d")
            for d in range(-1, 2)
        }
        if nearby & existing:
            continue

        if _get_price(ticker, event_date) is None:
            continue

        form_type   = filing.get("form_type", "8-K")
        description = (filing.get("description") or "").strip()
        title = (f"SEC {form_type}: {description}" if description
                 else f"SEC {form_type} filing")[:200]
        url   = filing.get("filing_url") or filing.get("document_url") or ""

        event_id = tracker.track_event(
            ticker=ticker,
            event_type="sec_filing",
            event_title=title,
            event_date=event_date,
            source="SEC EDGAR",
            url=url,
        )

        ok = _backfill(event_id, ticker, event_date, title)
        if ok:
            count += 1
            existing.add(date_str[:10])
            print(f"    ✓ 8-K {event_date.date()}  {title[:60]}")
        time.sleep(0.3)

    return count


def main():
    before = len(tracker.data["events"])
    print(f"\n{'='*60}")
    print(f"  SEC EDGAR 8-K Collection — {len(TICKERS)} tickers")
    print(f"  Events before: {before:,}")
    print(f"{'='*60}\n")

    total_new = 0
    for i, ticker in enumerate(TICKERS):
        print(f"[{i+1}/{len(TICKERS)}] {ticker}")
        n = collect_8k(ticker, limit=100)
        print(f"  → {n} new 8-K events with price data")
        total_new += n
        time.sleep(2)

    after = len(tracker.data["events"])
    print(f"\n{'='*60}")
    print(f"  Done. Events: {before:,} → {after:,}  (+{after - before} tracked)")
    print(f"  Events with full price backfill: {total_new}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
