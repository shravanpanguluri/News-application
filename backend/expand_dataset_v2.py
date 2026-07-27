"""
Dataset Expansion v2 — Three phases:
  A) Deep-fetch SEC 8-K filings (limit=200) for thin existing tickers (<20 events)
  B) Add FOIA data for Phase-2 tickers that only have SEC+contracts
  C) Collect all sources for 25 brand-new high-gov-exposure tickers

All new events are fully backfilled with:
  price returns (1d/3d/7d/30d), stock_momentum_3d, market_momentum_3d,
  relative_momentum, market_regime, vix_level, VADER NLP scores

Run from backend/:
    source venv/bin/activate && python expand_dataset_v2.py
    source venv/bin/activate && python expand_dataset_v2.py --phase A
"""
import argparse
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, str(Path(__file__).parent))
from services.correlation_tracker import tracker
from services.sec_edgar_service import sec_edgar_service
from services.usaspending_service import usaspending_service
from services.foia_engine import foia_engine

DATA_FILE    = Path("correlation_data.json")
TARGET_FORMS = {"8-K", "8-K/A"}
_vader       = SentimentIntensityAnalyzer()

# ── Phase A: thin tickers that need deeper SEC collection ──────────────────
THIN_TICKERS = [
    {"ticker": "AMAT",  "company": "Applied Materials"},
    {"ticker": "REGN",  "company": "Regeneron Pharmaceuticals"},
    {"ticker": "HUM",   "company": "Humana"},
    {"ticker": "CI",    "company": "Cigna"},
    {"ticker": "AZN",   "company": "AstraZeneca"},
    {"ticker": "NVDA",  "company": "NVIDIA"},
    {"ticker": "NFLX",  "company": "Netflix"},
    {"ticker": "BMY",   "company": "Bristol-Myers Squibb"},
    {"ticker": "WMT",   "company": "Walmart"},
    {"ticker": "GS",    "company": "Goldman Sachs"},
    {"ticker": "PG",    "company": "Procter & Gamble"},
    {"ticker": "CRM",   "company": "Salesforce"},
    {"ticker": "INTC",  "company": "Intel"},
    {"ticker": "MS",    "company": "Morgan Stanley"},
    {"ticker": "EOG",   "company": "EOG Resources"},
    {"ticker": "TXN",   "company": "Texas Instruments"},
    {"ticker": "VRTX",  "company": "Vertex Pharmaceuticals"},
    {"ticker": "MOH",   "company": "Molina Healthcare"},
]

# ── Phase B: tickers that only have SEC+contracts but NO FOIA ──────────────
# These are from Phase-2 collection — run FOIA engine for each
PHASE2_TICKERS_NEED_FOIA = [
    {"ticker": "QCOM",  "company": "Qualcomm"},
    {"ticker": "DELL",  "company": "Dell Technologies"},
    {"ticker": "HPE",   "company": "Hewlett Packard Enterprise"},
    {"ticker": "ACN",   "company": "Accenture"},
    {"ticker": "SAIC",  "company": "Science Applications International"},
    {"ticker": "MDT",   "company": "Medtronic"},
    {"ticker": "ABT",   "company": "Abbott Laboratories"},
    {"ticker": "TMO",   "company": "Thermo Fisher Scientific"},
    {"ticker": "DHR",   "company": "Danaher"},
    {"ticker": "BSX",   "company": "Boston Scientific"},
    {"ticker": "BIIB",  "company": "Biogen"},
    {"ticker": "AZN",   "company": "AstraZeneca"},
    {"ticker": "DE",    "company": "Deere"},
    {"ticker": "EMR",   "company": "Emerson Electric"},
    {"ticker": "ETN",   "company": "Eaton"},
    {"ticker": "PH",    "company": "Parker Hannifin"},
    {"ticker": "PSX",   "company": "Phillips 66"},
    {"ticker": "F",     "company": "Ford Motor"},
    {"ticker": "GM",    "company": "General Motors"},
    {"ticker": "HEI",   "company": "HEICO"},
    {"ticker": "AXON",  "company": "Axon Enterprise"},
]

# ── Phase C: brand-new tickers with very high gov-contract exposure ─────────
NEW_TICKERS_V2 = [
    # Pure gov-IT / defense consulting (highest signal)
    {"ticker": "BAH",   "company": "Booz Allen Hamilton"},
    {"ticker": "LDOS",  "company": "Leidos Holdings"},
    {"ticker": "CACI",  "company": "CACI International"},
    {"ticker": "PLTR",  "company": "Palantir Technologies"},
    {"ticker": "ICAD",  "company": "iCAD"},
    # Aerospace / defense manufacturing
    {"ticker": "HWM",   "company": "Howmet Aerospace"},
    {"ticker": "SPR",   "company": "Spirit AeroSystems"},
    {"ticker": "KTOS",  "company": "Kratos Defense & Security"},
    {"ticker": "MRCY",  "company": "Mercury Systems"},
    {"ticker": "DRS",   "company": "Leonardo DRS"},
    # Infrastructure / engineering services
    {"ticker": "J",     "company": "Jacobs Engineering"},
    {"ticker": "ACM",   "company": "AECOM"},
    {"ticker": "FLR",   "company": "Fluor"},
    {"ticker": "PWR",   "company": "Quanta Services"},
    # Biotech / pharma with FDA/BARDA contracts
    {"ticker": "MRNA",  "company": "Moderna"},
    {"ticker": "BNTX",  "company": "BioNTech"},
    {"ticker": "SNY",   "company": "Sanofi"},
    {"ticker": "GSK",   "company": "GSK"},
    # Energy with federal exposure
    {"ticker": "HAL",   "company": "Halliburton"},
    {"ticker": "BKR",   "company": "Baker Hughes"},
    {"ticker": "OKE",   "company": "ONEOK"},
    # Utilities (federal nuclear / grid contracts)
    {"ticker": "NEE",   "company": "NextEra Energy"},
    {"ticker": "SO",    "company": "Southern Company"},
    # Telecom / satellite (DoD comms)
    {"ticker": "VSAT",  "company": "Viasat"},
    {"ticker": "L3HM",  "company": "L3Harris Maverick"},  # fallback: skip if no data
]


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except Exception:
        return None


def _load_prices(symbol, start, end):
    try:
        hist = yf.Ticker(symbol).history(
            start=start.strftime("%Y-%m-%d"),
            end=(end + timedelta(days=5)).strftime("%Y-%m-%d"),
        )
        if hist.empty:
            return {}
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        return {d.strftime("%Y-%m-%d"): round(float(c), 4)
                for d, c in zip(hist.index, hist["Close"])}
    except Exception as e:
        print(f"    ⚠ price error {symbol}: {e}")
        return {}


def _closest(pdict, target, max_days=5):
    for delta in range(0, max_days + 1):
        for sign in (0, 1, -1):
            key = (target + timedelta(days=delta * sign)).strftime("%Y-%m-%d")
            if key in pdict:
                return pdict[key]
    return None


def _existing_dates(ticker_sym):
    return {e["event_date"][:10]
            for e in tracker.data["events"]
            if e["ticker"] == ticker_sym}


def _backfill(event_id, ticker_sym, event_date, title,
              prices, spy, vix):
    p0 = _closest(prices, event_date)
    if not p0 or p0 == 0:
        return False
    for ev in tracker.data["events"]:
        if ev["event_id"] != event_id:
            continue
        ev["price_0d"] = p0
        for days in [1, 3, 7, 30]:
            ph = _closest(prices, event_date + timedelta(days=days))
            if ph:
                ev[f"price_{days}d"] = ph
                ev[f"return_{days}d"] = _safe((ph - p0) / p0 * 100)
        pm3 = _closest(prices, event_date - timedelta(days=3))
        if pm3 and pm3 != 0:
            ev["stock_momentum_3d"] = _safe((p0 - pm3) / pm3 * 100)
        spy0  = _closest(spy, event_date)
        spym3 = _closest(spy, event_date - timedelta(days=3))
        spy90 = _closest(spy, event_date - timedelta(days=90))
        if spy0 and spym3 and spym3 != 0:
            ev["market_momentum_3d"] = _safe((spy0 - spym3) / spym3 * 100)
        ev["market_regime"] = (1 if spy0 and spy90 and spy90 != 0
                               and (spy0 - spy90) / spy90 > 0 else 0)
        sm = ev.get("stock_momentum_3d") or 0.0
        mm = ev.get("market_momentum_3d") or 0.0
        ev["relative_momentum"] = _safe(sm - mm)
        vx = _closest(vix, event_date)
        if vx:
            ev["vix_level"] = vx
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


def _fetch_global_indices(start, end):
    print("  Pre-fetching SPY …")
    spy = _load_prices("SPY",  start, end)
    print("  Pre-fetching VIX …")
    vix = _load_prices("^VIX", start, end)
    print(f"  SPY: {len(spy)} records   VIX: {len(vix)} records")
    return spy, vix


def _collect_sec(ticker_sym, limit, existing, prices, spy, vix):
    added = 0
    try:
        filings = sec_edgar_service.get_company_filings(
            ticker_sym, filing_type="8-K", limit=limit)
        if not filings:
            filings = sec_edgar_service.get_company_filings(ticker_sym, limit=limit)
            filings = [f for f in filings if f.get("form_type") in TARGET_FORMS]
        for filing in filings:
            ds = filing.get("filing_date", "")
            if not ds:
                continue
            try:
                edate = datetime.strptime(ds[:10], "%Y-%m-%d")
            except Exception:
                continue
            nearby = {(edate - timedelta(days=d)).strftime("%Y-%m-%d")
                      for d in range(-1, 2)}
            if nearby & existing:
                continue
            ft    = filing.get("form_type", "8-K")
            desc  = (filing.get("description") or "").strip()
            title = (f"SEC {ft}: {desc}" if desc else f"SEC {ft} filing")[:200]
            url   = filing.get("filing_url") or ""
            eid   = tracker.track_event(
                ticker=ticker_sym, event_type="sec_filing",
                event_title=title, event_date=edate,
                source="SEC EDGAR", url=url,
            )
            if _backfill(eid, ticker_sym, edate, title, prices, spy, vix):
                added += 1
                existing.add(ds[:10])
                print(f"    ✓ 8-K {edate.date()} {title[:55]}")
            time.sleep(0.25)
    except Exception as ex:
        print(f"    ✗ SEC error: {ex}")
    return added


def _collect_contracts(ticker_sym, company, limit, existing, prices, spy, vix):
    added = 0
    try:
        contracts = usaspending_service.get_contract_awards_for_ticker(
            ticker_sym, company_name=company, limit=limit)
        for c in contracts:
            ds = c.get("date") or c.get("period_of_performance_start_date", "")
            if not ds:
                continue
            try:
                edate = datetime.strptime(ds[:10], "%Y-%m-%d")
            except Exception:
                continue
            nearby = {(edate - timedelta(days=d)).strftime("%Y-%m-%d")
                      for d in range(-1, 2)}
            if nearby & existing:
                continue
            title = (c.get("description") or f"Federal Contract: {company}")[:200]
            award = c.get("Award Amount") or c.get("total_obligated_amount") or 0
            eid   = tracker.track_event(
                ticker=ticker_sym, event_type="contract",
                event_title=title, event_date=edate,
                source="USAspending.gov",
                url=c.get("usaspending_permalink", ""),
            )
            for ev in tracker.data["events"]:
                if ev["event_id"] == eid:
                    ev["Award Amount"] = award
                    break
            if _backfill(eid, ticker_sym, edate, title, prices, spy, vix):
                added += 1
                existing.add(edate.strftime("%Y-%m-%d"))
                print(f"    ✓ contract {edate.date()} ${award:,.0f}")
            time.sleep(0.2)
    except Exception as ex:
        print(f"    ✗ contract error: {ex}")
    return added


def _collect_foia(ticker_sym, existing, prices, spy, vix):
    added = 0
    try:
        requests = foia_engine.get_foia_requests(ticker_sym, limit=80)
        if not requests:
            return 0
        for req in requests:
            ds = req.get("date_filed") or req.get("date", "")
            if not ds:
                continue
            try:
                edate = datetime.strptime(ds[:10], "%Y-%m-%d")
            except Exception:
                continue
            nearby = {(edate - timedelta(days=d)).strftime("%Y-%m-%d")
                      for d in range(-1, 2)}
            if nearby & existing:
                continue
            title = (req.get("title") or req.get("subject")
                     or f"FOIA request: {ticker_sym}")[:200]
            eid   = tracker.track_event(
                ticker=ticker_sym, event_type="foia",
                event_title=title, event_date=edate,
                source="MuckRock / FOIA",
                url=req.get("absolute_url") or "",
            )
            if _backfill(eid, ticker_sym, edate, title, prices, spy, vix):
                added += 1
                existing.add(ds[:10])
                print(f"    ✓ FOIA  {edate.date()} {title[:55]}")
            time.sleep(0.2)
    except Exception as ex:
        print(f"    ✗ FOIA error: {ex}")
    return added


# ─────────────────────────────────────────────────────────────────────────────
# Phases
# ─────────────────────────────────────────────────────────────────────────────

def run_phase_a(spy, vix):
    print(f"\n{'='*62}")
    print(f"  Phase A — Deep-fetch SEC 8-K (limit=200) for {len(THIN_TICKERS)} thin tickers")
    print(f"{'='*62}\n")
    total = 0
    for i, item in enumerate(THIN_TICKERS):
        sym, co = item["ticker"], item["company"]
        print(f"  [{i+1}/{len(THIN_TICKERS)}] {co} ({sym})")
        t_start = datetime(2010, 1, 1)
        t_end   = datetime.now()
        prices  = _load_prices(sym, t_start, t_end)
        if not prices:
            print(f"    ✗ no price data — skip")
            time.sleep(1)
            continue
        existing = _existing_dates(sym)
        n_sec = _collect_sec(sym, 200, existing, prices, spy, vix)
        existing = _existing_dates(sym)
        n_con = _collect_contracts(sym, co, 150, existing, prices, spy, vix)
        print(f"    → +{n_sec} 8-K  +{n_con} contracts  for {sym}")
        total += n_sec + n_con
        time.sleep(1.5)
    print(f"\n  Phase A done — added {total} events")
    return total


def run_phase_b(spy, vix):
    print(f"\n{'='*62}")
    print(f"  Phase B — FOIA collection for {len(PHASE2_TICKERS_NEED_FOIA)} Phase-2 tickers")
    print(f"{'='*62}\n")
    # Only run FOIA for tickers that don't already have FOIA events
    foia_tickers = {e["ticker"] for e in tracker.data["events"]
                    if e.get("event_type", "").lower() == "foia"}
    to_run = [t for t in PHASE2_TICKERS_NEED_FOIA if t["ticker"] not in foia_tickers]
    print(f"  Already have FOIA: {foia_tickers & {t['ticker'] for t in PHASE2_TICKERS_NEED_FOIA}}")
    print(f"  Running FOIA for: {[t['ticker'] for t in to_run]}\n")
    total = 0
    for i, item in enumerate(to_run):
        sym, co = item["ticker"], item["company"]
        print(f"  [{i+1}/{len(to_run)}] {co} ({sym})")
        t_start = datetime(2012, 1, 1)
        prices  = _load_prices(sym, t_start, datetime.now())
        if not prices:
            print(f"    ✗ no price data — skip")
            continue
        existing = _existing_dates(sym)
        n = _collect_foia(sym, existing, prices, spy, vix)
        print(f"    → +{n} FOIA events for {sym}")
        total += n
        time.sleep(1.5)
    print(f"\n  Phase B done — added {total} FOIA events")
    return total


def run_phase_c(spy, vix):
    existing_tickers = {e["ticker"] for e in tracker.data["events"]}
    to_collect = [t for t in NEW_TICKERS_V2 if t["ticker"] not in existing_tickers]
    print(f"\n{'='*62}")
    print(f"  Phase C — New tickers: {len(to_collect)} to collect")
    print(f"{'='*62}\n")
    if not to_collect:
        print("  All v2 tickers already collected — skipping.")
        return 0
    total = 0
    for i, item in enumerate(to_collect):
        sym, co = item["ticker"], item["company"]
        print(f"  [{i+1}/{len(to_collect)}] {co} ({sym})")
        t_start = datetime(2016, 1, 1)
        prices  = _load_prices(sym, t_start, datetime.now())
        if not prices:
            print(f"    ✗ no price data — skip")
            time.sleep(1)
            continue
        print(f"    Price records: {len(prices)}")
        existing = _existing_dates(sym)
        n_sec  = _collect_sec(sym, 150, existing, prices, spy, vix)
        existing = _existing_dates(sym)
        n_con  = _collect_contracts(sym, co, 150, existing, prices, spy, vix)
        existing = _existing_dates(sym)
        n_foia = _collect_foia(sym, existing, prices, spy, vix)
        added  = n_sec + n_con + n_foia
        print(f"    → +{n_sec} 8-K  +{n_con} contracts  +{n_foia} FOIA  ({added} total for {sym})")
        total += added
        time.sleep(2)
    print(f"\n  Phase C done — added {total} events across {len(to_collect)} new tickers")
    return total


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["A", "B", "C", "all"], default="all")
    args = p.parse_args()

    before = len(tracker.data["events"])
    print(f"\n  Events before: {before:,}")

    global_start = datetime(2010, 1, 1)
    global_end   = datetime.now()
    spy, vix = _fetch_global_indices(global_start, global_end)

    total_added = 0
    if args.phase in ("A", "all"):
        total_added += run_phase_a(spy, vix)
    if args.phase in ("B", "all"):
        total_added += run_phase_b(spy, vix)
    if args.phase in ("C", "all"):
        total_added += run_phase_c(spy, vix)

    after = len(tracker.data["events"])
    with open(DATA_FILE) as f:
        d = json.load(f)
    evs = d.get("events", [])
    has = {h: sum(1 for e in evs if e.get(f"return_{h}") is not None)
           for h in ["1d", "3d", "7d", "30d"]}

    print(f"\n{'='*62}")
    print(f"  Expansion complete")
    print(f"  Events: {before:,} → {after:,}  (+{after - before:,})")
    print(f"  Return coverage: {has}")
    print(f"{'='*62}")
    print("\n  Next: source venv/bin/activate && python retrain_production_models.py --n-iter 100 --cv 5\n")


if __name__ == "__main__":
    main()
