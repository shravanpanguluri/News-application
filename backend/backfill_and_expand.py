"""
Phase-1: Backfill missing fields for 1,414 partially-populated events.
Phase-2: Collect events for 31 new tickers (SEC 8-K + contracts).

Root cause: the massive_data_collection run stored return_1d/7d/30d but
never wrote return_3d, vix_level, stock_momentum_3d, market_momentum_3d,
relative_momentum, market_regime, or VADER vader_positive / vader_negative.
Training on those 1,414 events with those fields zeroed out introduces a
large systematic bias.  This script repairs them.

Run from backend/:
    source venv/bin/activate && python backfill_and_expand.py
"""
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, str(Path(__file__).parent))
from services.correlation_tracker import tracker
from services.sec_edgar_service import sec_edgar_service
from services.usaspending_service import usaspending_service

DATA_FILE = Path("correlation_data.json")
_vader    = SentimentIntensityAnalyzer()

# --------------------------------------------------------------------------
# NEW tickers to collect — 31 companies with high gov-contract exposure
# --------------------------------------------------------------------------
NEW_TICKERS = [
    # Semiconductors / Defense tech
    {"ticker": "QCOM", "company": "Qualcomm"},
    {"ticker": "TXN",  "company": "Texas Instruments"},
    {"ticker": "AMAT", "company": "Applied Materials"},
    # IT / Cloud — large federal contracts
    {"ticker": "DELL", "company": "Dell Technologies"},
    {"ticker": "HPE",  "company": "Hewlett Packard Enterprise"},
    {"ticker": "ACN",  "company": "Accenture"},
    {"ticker": "SAIC", "company": "Science Applications International"},
    # Healthcare / Medical devices (Medicare / DoD)
    {"ticker": "MDT",  "company": "Medtronic"},
    {"ticker": "ABT",  "company": "Abbott Laboratories"},
    {"ticker": "TMO",  "company": "Thermo Fisher Scientific"},
    {"ticker": "DHR",  "company": "Danaher"},
    {"ticker": "BSX",  "company": "Boston Scientific"},
    # Managed care / Medicaid
    {"ticker": "HUM",  "company": "Humana"},
    {"ticker": "CI",   "company": "Cigna"},
    {"ticker": "CNC",  "company": "Centene"},
    {"ticker": "MOH",  "company": "Molina Healthcare"},
    # Pharma / Biotech (FDA actions, NIH)
    {"ticker": "REGN", "company": "Regeneron Pharmaceuticals"},
    {"ticker": "VRTX", "company": "Vertex Pharmaceuticals"},
    {"ticker": "BIIB", "company": "Biogen"},
    {"ticker": "AZN",  "company": "AstraZeneca"},
    # Industrial / Defense-adjacent
    {"ticker": "DE",   "company": "Deere"},
    {"ticker": "EMR",  "company": "Emerson Electric"},
    {"ticker": "ETN",  "company": "Eaton"},
    {"ticker": "PH",   "company": "Parker Hannifin"},
    # Energy (federal leases / regulation)
    {"ticker": "COP",  "company": "ConocoPhillips"},
    {"ticker": "OXY",  "company": "Occidental Petroleum"},
    {"ticker": "PSX",  "company": "Phillips 66"},
    # Automotive (DoD vehicle contracts)
    {"ticker": "F",    "company": "Ford Motor"},
    {"ticker": "GM",   "company": "General Motors"},
    # Additional defense / aerospace
    {"ticker": "HEI",  "company": "HEICO"},
    {"ticker": "AXON", "company": "Axon Enterprise"},
]

TARGET_FORMS = {"8-K", "8-K/A"}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def _load_price_history(symbol, start_date, end_date):
    """Fetch full OHLCV history for symbol between start/end and return as
    a dict {date_str: close_price} with tz stripped."""
    try:
        hist = yf.Ticker(symbol).history(
            start=start_date.strftime("%Y-%m-%d"),
            end=(end_date + timedelta(days=5)).strftime("%Y-%m-%d"),
        )
        if hist.empty:
            return {}
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        return {d.strftime("%Y-%m-%d"): round(float(c), 4)
                for d, c in zip(hist.index, hist["Close"])}
    except Exception as e:
        print(f"    ⚠ price history error for {symbol}: {e}")
        return {}


def _closest_price(price_dict, target_date, max_days=5):
    """Find the price for the trading day closest to target_date."""
    for delta in range(0, max_days + 1):
        for sign in (0, 1, -1):
            d = (target_date + timedelta(days=delta * sign)).strftime("%Y-%m-%d")
            if d in price_dict:
                return price_dict[d]
    return None


# --------------------------------------------------------------------------
# Phase 1 — backfill missing fields in existing events
# --------------------------------------------------------------------------

def phase1_backfill():
    with open(DATA_FILE) as f:
        data = json.load(f)
    events = data["events"]

    # Identify events that need repair
    to_fix = [
        e for e in events
        if e.get("return_1d") is not None and e.get("return_3d") is None
    ]
    print(f"\n{'='*62}")
    print(f"  Phase 1 — Backfill {len(to_fix):,} partially-populated events")
    print(f"{'='*62}")
    if not to_fix:
        print("  Nothing to fix — all events already have return_3d.")
        return

    # Group by ticker so we make one yfinance call per ticker
    by_ticker = defaultdict(list)
    for e in to_fix:
        by_ticker[e["ticker"]].append(e)

    # Also need SPY and VIX once globally
    all_dates = [datetime.fromisoformat(e["event_date"][:19]) for e in to_fix
                 if e.get("event_date")]
    global_start = min(all_dates) - timedelta(days=95)
    global_end   = max(all_dates) + timedelta(days=35)

    print(f"  Fetching SPY …")
    spy_prices = _load_price_history("SPY",  global_start, global_end)
    print(f"  Fetching VIX …")
    vix_prices = _load_price_history("^VIX", global_start, global_end)
    print(f"  SPY records: {len(spy_prices)}   VIX records: {len(vix_prices)}")

    fixed = 0
    total_tickers = len(by_ticker)
    for t_idx, (ticker, tevents) in enumerate(sorted(by_ticker.items())):
        print(f"  [{t_idx+1}/{total_tickers}] {ticker} — {len(tevents)} events")
        t_dates = [datetime.fromisoformat(e["event_date"][:19])
                   for e in tevents if e.get("event_date")]
        if not t_dates:
            continue
        t_start = min(t_dates) - timedelta(days=95)
        t_end   = max(t_dates) + timedelta(days=35)
        prices  = _load_price_history(ticker, t_start, t_end)
        if not prices:
            print(f"    ✗ no price data")
            time.sleep(1)
            continue

        for e in tevents:
            if not e.get("event_date"):
                continue
            try:
                dt = datetime.fromisoformat(e["event_date"][:19])
            except Exception:
                continue

            p0 = _closest_price(prices, dt)
            if not p0 or p0 == 0:
                continue

            # Forward returns
            for days in [3]:  # 1d/7d/30d already exist
                ph = _closest_price(prices, dt + timedelta(days=days))
                if ph:
                    e[f"price_{days}d"] = ph
                    e[f"return_{days}d"] = _safe((ph - p0) / p0 * 100)

            # Momentum features (may also be missing)
            if e.get("stock_momentum_3d") is None:
                pm3 = _closest_price(prices, dt - timedelta(days=3))
                if pm3 and pm3 != 0:
                    e["stock_momentum_3d"] = _safe((p0 - pm3) / pm3 * 100)

            if e.get("market_momentum_3d") is None:
                spy0  = _closest_price(spy_prices, dt)
                spym3 = _closest_price(spy_prices, dt - timedelta(days=3))
                if spy0 and spym3 and spym3 != 0:
                    e["market_momentum_3d"] = _safe((spy0 - spym3) / spym3 * 100)

            if e.get("market_regime") is None:
                spy0   = _closest_price(spy_prices, dt)
                spy90  = _closest_price(spy_prices, dt - timedelta(days=90))
                e["market_regime"] = (1 if (spy0 and spy90 and spy90 != 0
                                            and (spy0 - spy90) / spy90 > 0)
                                      else 0)

            sm = e.get("stock_momentum_3d") or 0.0
            mm = e.get("market_momentum_3d") or 0.0
            if e.get("relative_momentum") is None:
                e["relative_momentum"] = _safe(sm - mm)

            if e.get("vix_level") is None:
                vix = _closest_price(vix_prices, dt)
                if vix:
                    e["vix_level"] = vix

            # VADER scores — patch signal dict
            sig = e.get("signal") or {}
            if sig.get("vader_positive") is None:
                title = e.get("event_title", "")
                vs    = _vader.polarity_scores(title)
                compound = vs["compound"]
                nlp_score = round((compound + 1.0) / 2.0 * 100.0, 2)
                sig.update({
                    "signal_score":        sig.get("signal_score", nlp_score),
                    "nlp_sentiment_score": nlp_score,
                    "vader_compound":      round(compound, 4),
                    "vader_positive":      round(vs["pos"], 4),
                    "vader_negative":      round(vs["neg"], 4),
                    "vader_neutral":       round(vs["neu"], 4),
                })
                e["signal"] = sig

            if e.get("return_3d") is not None:
                fixed += 1

        time.sleep(0.5)   # polite yfinance pacing

    # Write back
    data["events"] = events
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, default=str)

    print(f"\n  ✓ Phase 1 complete — {fixed}/{len(to_fix)} events now have return_3d")


# --------------------------------------------------------------------------
# Phase 2 — collect events for 31 new tickers
# --------------------------------------------------------------------------

def _existing_dates(ticker_sym):
    return {
        e["event_date"][:10]
        for e in tracker.data["events"]
        if e["ticker"] == ticker_sym
    }


def _backfill_event(event_id, ticker_sym, event_date, title,
                    prices, spy_prices, vix_prices):
    p0 = _closest_price(prices, event_date)
    if not p0 or p0 == 0:
        return False

    for ev in tracker.data["events"]:
        if ev["event_id"] != event_id:
            continue

        ev["price_0d"] = p0
        for days in [1, 3, 7, 30]:
            ph = _closest_price(prices, event_date + timedelta(days=days))
            if ph:
                ev[f"price_{days}d"] = ph
                ev[f"return_{days}d"] = _safe((ph - p0) / p0 * 100)

        pm3 = _closest_price(prices, event_date - timedelta(days=3))
        if pm3 and pm3 != 0:
            ev["stock_momentum_3d"] = _safe((p0 - pm3) / pm3 * 100)

        spy0  = _closest_price(spy_prices, event_date)
        spym3 = _closest_price(spy_prices, event_date - timedelta(days=3))
        spy90 = _closest_price(spy_prices, event_date - timedelta(days=90))

        if spy0 and spym3 and spym3 != 0:
            ev["market_momentum_3d"] = _safe((spy0 - spym3) / spym3 * 100)
        ev["market_regime"] = (1 if spy0 and spy90 and spy90 != 0
                                   and (spy0 - spy90) / spy90 > 0
                               else 0)

        sm = ev.get("stock_momentum_3d") or 0.0
        mm = ev.get("market_momentum_3d") or 0.0
        ev["relative_momentum"] = _safe(sm - mm)

        vix = _closest_price(vix_prices, event_date)
        if vix:
            ev["vix_level"] = vix

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
        break

    tracker._save_data()
    return True


def phase2_new_tickers():
    print(f"\n{'='*62}")
    print(f"  Phase 2 — Collect events for {len(NEW_TICKERS)} new tickers")
    print(f"{'='*62}")

    existing_tickers = {e["ticker"] for e in tracker.data["events"]}
    to_collect = [t for t in NEW_TICKERS if t["ticker"] not in existing_tickers]
    already    = [t for t in NEW_TICKERS if t["ticker"] in existing_tickers]
    if already:
        print(f"  Already collected ({len(already)}): {[t['ticker'] for t in already]}")
    if not to_collect:
        print("  All new tickers already have data — skipping Phase 2.")
        return

    print(f"  New tickers to collect: {[t['ticker'] for t in to_collect]}\n")

    # Pre-fetch SPY + VIX for the whole range once
    global_start = datetime(2018, 1, 1)
    global_end   = datetime.now()
    print("  Pre-fetching SPY …")
    spy_prices = _load_price_history("SPY",  global_start, global_end)
    print("  Pre-fetching VIX …")
    vix_prices = _load_price_history("^VIX", global_start, global_end)

    before = len(tracker.data["events"])
    total_new = 0

    for i, item in enumerate(to_collect):
        ticker_sym = item["ticker"]
        company    = item["company"]
        print(f"\n  [{i+1}/{len(to_collect)}] {company} ({ticker_sym})")

        # Fetch ticker price history once
        t_start = datetime(2016, 1, 1)
        prices  = _load_price_history(ticker_sym, t_start, global_end)
        if not prices:
            print(f"    ✗ No price data — skipping")
            continue
        print(f"    Price records: {len(prices)}")

        existing = _existing_dates(ticker_sym)
        n_added  = 0

        # SEC 8-K filings
        try:
            filings = sec_edgar_service.get_company_filings(ticker_sym,
                                                            filing_type="8-K",
                                                            limit=100)
            if not filings:
                filings = sec_edgar_service.get_company_filings(ticker_sym, limit=100)
                filings = [f for f in filings if f.get("form_type") in TARGET_FORMS]

            for filing in filings:
                date_str = filing.get("filing_date", "")
                if not date_str:
                    continue
                try:
                    event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except Exception:
                    continue
                nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d")
                          for d in range(-1, 2)}
                if nearby & existing:
                    continue
                form_type   = filing.get("form_type", "8-K")
                description = (filing.get("description") or "").strip()
                title = (f"SEC {form_type}: {description}"
                         if description else f"SEC {form_type} filing")[:200]
                url = filing.get("filing_url") or ""

                event_id = tracker.track_event(
                    ticker=ticker_sym, event_type="sec_filing",
                    event_title=title, event_date=event_date,
                    source="SEC EDGAR", url=url,
                )
                if _backfill_event(event_id, ticker_sym, event_date, title,
                                   prices, spy_prices, vix_prices):
                    n_added += 1
                    existing.add(date_str[:10])
                    print(f"    ✓ 8-K {event_date.date()} {title[:55]}")
                time.sleep(0.25)
        except Exception as ex:
            print(f"    ✗ 8-K error: {ex}")

        # USASpending contracts
        try:
            contracts = usaspending_service.get_contract_awards_for_ticker(
                ticker_sym, company_name=company, limit=100
            )
            for c in contracts:
                date_str = c.get("date") or c.get("period_of_performance_start_date", "")
                if not date_str:
                    continue
                try:
                    event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except Exception:
                    continue
                nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d")
                          for d in range(-1, 2)}
                if nearby & existing:
                    continue
                title = (c.get("description") or f"Federal Contract: {company}")[:200]
                award = c.get("Award Amount") or c.get("total_obligated_amount") or 0

                event_id = tracker.track_event(
                    ticker=ticker_sym, event_type="contract",
                    event_title=title, event_date=event_date,
                    source="USAspending.gov",
                    url=c.get("usaspending_permalink", ""),
                )
                for ev in tracker.data["events"]:
                    if ev["event_id"] == event_id:
                        ev["Award Amount"] = award
                        break

                if _backfill_event(event_id, ticker_sym, event_date, title,
                                   prices, spy_prices, vix_prices):
                    n_added += 1
                    existing.add(event_date.strftime("%Y-%m-%d"))
                    print(f"    ✓ contract {event_date.date()} ${award:,.0f}")
                time.sleep(0.2)
        except Exception as ex:
            print(f"    ✗ contract error: {ex}")

        print(f"    → added {n_added} new events for {ticker_sym}")
        total_new += n_added
        time.sleep(1.5)

    after = len(tracker.data["events"])
    print(f"\n  ✓ Phase 2 complete — events: {before:,} → {after:,}  (+{after - before})")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["1", "2", "all"], default="all",
                   help="Which phases to run (default: all)")
    args = p.parse_args()

    if args.phase in ("1", "all"):
        phase1_backfill()

    if args.phase in ("2", "all"):
        phase2_new_tickers()

    # Quick summary
    with open(DATA_FILE) as f:
        d = json.load(f)
    evs = d.get("events", [])
    has_3d = sum(1 for e in evs if e.get("return_3d") is not None)
    print(f"\n{'='*62}")
    print(f"  Final dataset: {len(evs):,} events")
    print(f"  With return_3d: {has_3d:,}  ({has_3d/max(len(evs),1)*100:.0f}%)")
    print(f"{'='*62}")
    print("\n  Next step: run retrain_production_models.py --n-iter 60\n")
