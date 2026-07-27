"""
Expanded FOIA/Regulatory Data Collection
Three high-signal sources not yet in training data:

  A) Federal Register — RULE, PRORULE, NOTICE for all 130 tickers
     (arms sales → defense; CMS rules → managed care; EPA rules → energy; etc.)

  B) openFDA drug approvals — original NDAs/BLAs for pharma/biotech tickers
     (highly material stock-moving events)

  C) FDA recall/enforcement — negative-signal events for pharma tickers

Run from backend/:
    source venv/bin/activate && python collect_foia_expanded.py
    source venv/bin/activate && python collect_foia_expanded.py --phase A
    source venv/bin/activate && python collect_foia_expanded.py --phase B
    source venv/bin/activate && python collect_foia_expanded.py --phase C
"""
import argparse
import json
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, str(Path(__file__).parent))
from services.correlation_tracker import tracker

_vader       = SentimentIntensityAnalyzer()
_price_cache = {}

# ── Per-source rate limits ────────────────────────────────────────────────────
FR_DELAY  = 0.5   # Federal Register (polite)
FDA_DELAY = 0.4   # openFDA
_HEADERS  = {"User-Agent": "Predovex-Research/1.0 shrav494@gmail.com"}

# ── Company → ticker master list (all 130 in dataset) ────────────────────────
ALL_TICKERS = [
    # Defense / Aerospace
    {"ticker": "LMT",  "company": "Lockheed Martin"},
    {"ticker": "RTX",  "company": "Raytheon Technologies"},
    {"ticker": "NOC",  "company": "Northrop Grumman"},
    {"ticker": "GD",   "company": "General Dynamics"},
    {"ticker": "BA",   "company": "Boeing"},
    {"ticker": "LHX",  "company": "L3Harris Technologies"},
    {"ticker": "HII",  "company": "Huntington Ingalls"},
    {"ticker": "TDG",  "company": "TransDigm"},
    {"ticker": "HEI",  "company": "HEICO"},
    {"ticker": "KTOS", "company": "Kratos Defense"},
    {"ticker": "MRCY", "company": "Mercury Systems"},
    {"ticker": "DRS",  "company": "Leonardo DRS"},
    {"ticker": "AXON", "company": "Axon Enterprise"},
    {"ticker": "AVAV", "company": "AeroVironment"},
    {"ticker": "TXT",  "company": "Textron"},
    {"ticker": "CW",   "company": "Curtiss-Wright"},
    {"ticker": "MOOG", "company": "Moog"},
    {"ticker": "HWM",  "company": "Howmet Aerospace"},
    # Gov IT / Consulting
    {"ticker": "BAH",  "company": "Booz Allen Hamilton"},
    {"ticker": "LDOS", "company": "Leidos"},
    {"ticker": "CACI", "company": "CACI International"},
    {"ticker": "SAIC", "company": "SAIC"},
    {"ticker": "PLTR", "company": "Palantir Technologies"},
    {"ticker": "ACN",  "company": "Accenture"},
    # Infrastructure / Engineering
    {"ticker": "J",    "company": "Jacobs Engineering"},
    {"ticker": "ACM",  "company": "AECOM"},
    {"ticker": "FLR",  "company": "Fluor"},
    {"ticker": "PWR",  "company": "Quanta Services"},
    {"ticker": "GE",   "company": "General Electric"},
    {"ticker": "HON",  "company": "Honeywell"},
    {"ticker": "MMM",  "company": "3M"},
    {"ticker": "CAT",  "company": "Caterpillar"},
    {"ticker": "DE",   "company": "Deere"},
    {"ticker": "EMR",  "company": "Emerson Electric"},
    {"ticker": "ETN",  "company": "Eaton"},
    {"ticker": "PH",   "company": "Parker Hannifin"},
    # Big Tech / Cloud (federal cloud contracts)
    {"ticker": "MSFT", "company": "Microsoft"},
    {"ticker": "AMZN", "company": "Amazon"},
    {"ticker": "GOOGL","company": "Google"},
    {"ticker": "IBM",  "company": "IBM"},
    {"ticker": "ORCL", "company": "Oracle"},
    {"ticker": "DELL", "company": "Dell Technologies"},
    {"ticker": "HPE",  "company": "Hewlett Packard Enterprise"},
    {"ticker": "CDNS", "company": "Cadence Design Systems"},
    {"ticker": "ANSS", "company": "ANSYS"},
    # Semiconductors
    {"ticker": "NVDA", "company": "NVIDIA"},
    {"ticker": "INTC", "company": "Intel"},
    {"ticker": "AMD",  "company": "AMD"},
    {"ticker": "QCOM", "company": "Qualcomm"},
    {"ticker": "TXN",  "company": "Texas Instruments"},
    {"ticker": "AMAT", "company": "Applied Materials"},
    # Pharma / Biotech
    {"ticker": "PFE",  "company": "Pfizer"},
    {"ticker": "JNJ",  "company": "Johnson Johnson"},
    {"ticker": "MRK",  "company": "Merck"},
    {"ticker": "LLY",  "company": "Eli Lilly"},
    {"ticker": "ABBV", "company": "AbbVie"},
    {"ticker": "AMGN", "company": "Amgen"},
    {"ticker": "GILD", "company": "Gilead Sciences"},
    {"ticker": "BMY",  "company": "Bristol-Myers Squibb"},
    {"ticker": "MRNA", "company": "Moderna"},
    {"ticker": "REGN", "company": "Regeneron"},
    {"ticker": "VRTX", "company": "Vertex Pharmaceuticals"},
    {"ticker": "BIIB", "company": "Biogen"},
    {"ticker": "AZN",  "company": "AstraZeneca"},
    {"ticker": "BNTX", "company": "BioNTech"},
    {"ticker": "GSK",  "company": "GSK"},
    {"ticker": "SNY",  "company": "Sanofi"},
    {"ticker": "ILMN", "company": "Illumina"},
    # Healthcare Services / Devices
    {"ticker": "UNH",  "company": "UnitedHealth Group"},
    {"ticker": "CVS",  "company": "CVS Health"},
    {"ticker": "HUM",  "company": "Humana"},
    {"ticker": "CI",   "company": "Cigna"},
    {"ticker": "CNC",  "company": "Centene"},
    {"ticker": "MOH",  "company": "Molina Healthcare"},
    {"ticker": "ELV",  "company": "Elevance Health"},
    {"ticker": "HCA",  "company": "HCA Healthcare"},
    {"ticker": "MCK",  "company": "McKesson"},
    {"ticker": "SYK",  "company": "Stryker"},
    {"ticker": "ISRG", "company": "Intuitive Surgical"},
    {"ticker": "ZBH",  "company": "Zimmer Biomet"},
    {"ticker": "MDT",  "company": "Medtronic"},
    {"ticker": "ABT",  "company": "Abbott Laboratories"},
    {"ticker": "TMO",  "company": "Thermo Fisher"},
    {"ticker": "DHR",  "company": "Danaher"},
    {"ticker": "BSX",  "company": "Boston Scientific"},
    {"ticker": "DGX",  "company": "Quest Diagnostics"},
    {"ticker": "LH",   "company": "Labcorp"},
    {"ticker": "GEHC", "company": "GE HealthCare"},
    # Energy
    {"ticker": "XOM",  "company": "ExxonMobil"},
    {"ticker": "CVX",  "company": "Chevron"},
    {"ticker": "COP",  "company": "ConocoPhillips"},
    {"ticker": "OXY",  "company": "Occidental Petroleum"},
    {"ticker": "HAL",  "company": "Halliburton"},
    {"ticker": "SLB",  "company": "Schlumberger"},
    {"ticker": "BKR",  "company": "Baker Hughes"},
    {"ticker": "PSX",  "company": "Phillips 66"},
    {"ticker": "EOG",  "company": "EOG Resources"},
    {"ticker": "NEE",  "company": "NextEra Energy"},
    {"ticker": "SO",   "company": "Southern Company"},
    # Finance / Banking
    {"ticker": "JPM",  "company": "JPMorgan Chase"},
    {"ticker": "BAC",  "company": "Bank of America"},
    {"ticker": "WFC",  "company": "Wells Fargo"},
    {"ticker": "GS",   "company": "Goldman Sachs"},
    {"ticker": "MS",   "company": "Morgan Stanley"},
    {"ticker": "C",    "company": "Citigroup"},
    {"ticker": "BLK",  "company": "BlackRock"},
    {"ticker": "AXP",  "company": "American Express"},
    {"ticker": "V",    "company": "Visa"},
    {"ticker": "MA",   "company": "Mastercard"},
    # Consumer / Retail
    {"ticker": "WMT",  "company": "Walmart"},
    {"ticker": "AAPL", "company": "Apple"},
    {"ticker": "META", "company": "Meta Platforms"},
    {"ticker": "TSLA", "company": "Tesla"},
    {"ticker": "NFLX", "company": "Netflix"},
    {"ticker": "DIS",  "company": "Disney"},
    {"ticker": "ADBE", "company": "Adobe"},
    {"ticker": "CRM",  "company": "Salesforce"},
    {"ticker": "NKE",  "company": "Nike"},
    {"ticker": "MCD",  "company": "McDonald's"},
    {"ticker": "SBUX", "company": "Starbucks"},
    {"ticker": "KO",   "company": "Coca-Cola"},
    {"ticker": "FDX",  "company": "FedEx"},
    {"ticker": "UPS",  "company": "UPS"},
    {"ticker": "HD",   "company": "Home Depot"},
    {"ticker": "LOW",  "company": "Lowe's"},
    {"ticker": "TGT",  "company": "Target"},
    {"ticker": "T",    "company": "AT&T"},
    {"ticker": "VZ",   "company": "Verizon"},
    {"ticker": "TMUS", "company": "T-Mobile"},
    {"ticker": "VSAT", "company": "Viasat"},
    {"ticker": "VRSK", "company": "Verisk Analytics"},
    {"ticker": "PG",   "company": "Procter Gamble"},
    {"ticker": "F",    "company": "Ford Motor"},
    {"ticker": "GM",   "company": "General Motors"},
]

# Pharma tickers that have FDA drug approval data
PHARMA_TICKERS = {
    "PFE": "Pfizer", "JNJ": "Johnson Johnson", "MRK": "Merck",
    "LLY": "Eli Lilly", "ABBV": "AbbVie", "AMGN": "Amgen",
    "GILD": "Gilead", "BMY": "Bristol-Myers", "MRNA": "Moderna",
    "REGN": "Regeneron", "VRTX": "Vertex", "BIIB": "Biogen",
    "AZN": "AstraZeneca", "BNTX": "BioNTech", "GSK": "GSK",
    "SNY": "Sanofi", "ILMN": "Illumina", "MDT": "Medtronic",
    "ABT": "Abbott", "BSX": "Boston Scientific",
}


# ─────────────────────────────────────────────────────────────────────────────
# Shared price/NLP helpers
# ─────────────────────────────────────────────────────────────────────────────

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
    return {e["event_date"][:10] for e in tracker.data["events"] if e["ticker"] == ticker_sym}


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


# ─────────────────────────────────────────────────────────────────────────────
# Phase A: Federal Register
# ─────────────────────────────────────────────────────────────────────────────

FR_BASE = "https://www.federalregister.gov/api/v1"
FR_TYPES = ["RULE", "PRORULE", "NOTICE"]   # binding rules, proposed rules, notices


def _fetch_fr_page(company, page, per_page=100):
    try:
        r = requests.get(
            f"{FR_BASE}/documents.json",
            params={
                "conditions[term]":   company,
                "conditions[type][]": FR_TYPES,
                "per_page":           per_page,
                "page":               page,
                "order":              "newest",
                "fields[]": [
                    "title", "publication_date", "type",
                    "html_url", "abstract", "agencies",
                ],
            },
            headers=_HEADERS,
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"    ! FR fetch error: {e}")
    return {}


def collect_federal_register(ticker_sym, company, limit=200):
    existing = _existing_dates(ticker_sym)
    count    = 0
    page     = 1
    fetched  = 0

    while fetched < limit:
        data = _fetch_fr_page(company, page, per_page=min(100, limit - fetched))
        results = data.get("results", [])
        if not results:
            break

        for doc in results:
            pub_date = doc.get("publication_date", "")
            if not pub_date:
                continue
            try:
                event_date = datetime.strptime(pub_date[:10], "%Y-%m-%d")
            except Exception:
                continue

            # Skip events older than 10 years
            if event_date < datetime(2015, 1, 1):
                continue

            nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
            if nearby & existing:
                continue

            title   = (doc.get("title") or "Federal Register document")[:200]
            url     = doc.get("html_url", "")
            doc_type = doc.get("type", "NOTICE")

            event_type_map = {
                "RULE":    "regulatory_rule",
                "PRORULE": "regulatory_proposed",
                "NOTICE":  "regulatory_notice",
            }
            event_type = event_type_map.get(doc_type, "regulatory_notice")

            event_id = tracker.track_event(
                ticker=ticker_sym,
                event_type=event_type,
                event_title=title,
                event_date=event_date,
                source="Federal Register",
                url=url,
            )
            if _backfill(event_id, ticker_sym, event_date, title):
                count += 1
                existing.add(pub_date[:10])
                print(f"    + FR {doc_type} {event_date.date()}  {title[:55]}")
            time.sleep(FR_DELAY)

        fetched += len(results)
        total   = data.get("count", 0)
        if fetched >= total or len(results) < 100:
            break
        page += 1

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Phase B: openFDA — Drug Approvals (pharma tickers)
# ─────────────────────────────────────────────────────────────────────────────

FDA_BASE = "https://api.fda.gov"

_APPROVAL_STATUS = {"AP", "TA"}  # Approved, Tentatively Approved


def _parse_fda_date(date_str):
    """Parse openFDA date strings: YYYYMMDD or YYYY-MM-DD"""
    if not date_str:
        return None
    date_str = date_str.replace("-", "")
    try:
        return datetime.strptime(date_str[:8], "%Y%m%d")
    except Exception:
        return None


def collect_fda_approvals(ticker_sym, company_search, limit=150):
    """Collect original drug approval events from openFDA."""
    existing = _existing_dates(ticker_sym)
    count    = 0
    skip     = 0

    while skip < limit:
        try:
            r = requests.get(
                f"{FDA_BASE}/drug/drugsfda.json",
                params={
                    "search": f'openfda.manufacturer_name:"{company_search}"',
                    "limit":  min(100, limit - skip),
                    "skip":   skip,
                },
                headers=_HEADERS,
                timeout=15,
            )
            if r.status_code != 200:
                break
            data = r.json()
        except Exception as e:
            print(f"    ! FDA approval error: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for rec in results:
            products  = rec.get("products", [{}])
            brand     = (products[0].get("brand_name") or "").strip() if products else ""
            generic   = (products[0].get("generic_name") or "").strip() if products else ""
            drug_name = brand or generic or "Unknown Drug"

            for sub in rec.get("submissions", []):
                if sub.get("submission_status") not in _APPROVAL_STATUS:
                    continue
                sub_type = sub.get("submission_type", "")
                # Only original approvals and major efficacy supplements
                if sub_type not in ("ORIG", "EFFICACY"):
                    continue

                event_date = _parse_fda_date(sub.get("submission_status_date", ""))
                if not event_date or event_date < datetime(2015, 1, 1):
                    continue

                nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
                if nearby & existing:
                    continue

                status_label = "Approval" if sub_type == "ORIG" else "Supplemental Approval"
                title = f"FDA {status_label}: {drug_name} ({company_search})"[:200]
                url   = f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm"

                event_id = tracker.track_event(
                    ticker=ticker_sym,
                    event_type="fda_approval",
                    event_title=title,
                    event_date=event_date,
                    source="openFDA",
                    url=url,
                )
                if _backfill(event_id, ticker_sym, event_date, title):
                    count += 1
                    existing.add(event_date.strftime("%Y-%m-%d"))
                    print(f"    + FDA {sub_type} {event_date.date()}  {title[:60]}")
                time.sleep(FDA_DELAY)

        total = data.get("meta", {}).get("results", {}).get("total", 0)
        skip += len(results)
        if skip >= total or len(results) < 100:
            break

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Phase C: FDA Drug Recalls / Enforcement (negative signals)
# ─────────────────────────────────────────────────────────────────────────────

def collect_fda_recalls(ticker_sym, company_search, limit=100):
    """Collect FDA drug recall events (Class I/II/III) from openFDA enforcement."""
    existing = _existing_dates(ticker_sym)
    count    = 0
    skip     = 0

    while skip < limit:
        try:
            r = requests.get(
                f"{FDA_BASE}/drug/enforcement.json",
                params={
                    "search": f'recalling_firm:"{company_search}"',
                    "limit":  min(100, limit - skip),
                    "skip":   skip,
                },
                headers=_HEADERS,
                timeout=15,
            )
            if r.status_code != 200:
                break
            data = r.json()
        except Exception as e:
            print(f"    ! FDA recall error: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for rec in results:
            date_str = rec.get("recall_initiation_date", "")
            event_date = _parse_fda_date(date_str)
            if not event_date or event_date < datetime(2015, 1, 1):
                continue

            nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
            if nearby & existing:
                continue

            classification = rec.get("classification", "Class II")
            product = (rec.get("product_description") or "drug product")[:80]
            reason  = (rec.get("reason_for_recall") or "")[:100]
            title   = f"FDA Recall {classification}: {product}"
            if reason:
                title = f"{title} — {reason}"
            title = title[:200]

            event_id = tracker.track_event(
                ticker=ticker_sym,
                event_type="fda_recall",
                event_title=title,
                event_date=event_date,
                source="FDA Enforcement",
                url=rec.get("openfda", {}).get("spl_id", [""])[0] or "",
            )
            if _backfill(event_id, ticker_sym, event_date, title):
                count += 1
                existing.add(event_date.strftime("%Y-%m-%d"))
                print(f"    + Recall {classification} {event_date.date()}  {product[:50]}")
            time.sleep(FDA_DELAY)

        total = data.get("meta", {}).get("results", {}).get("total", 0)
        skip += len(results)
        if skip >= total or len(results) < 100:
            break

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["A", "B", "C", "all"], default="all",
                   help="A=Federal Register, B=FDA Approvals, C=FDA Recalls (default: all)")
    return p.parse_args()


def main():
    args  = parse_args()
    phase = args.phase.upper()
    run_a = phase in ("A", "ALL")
    run_b = phase in ("B", "ALL")
    run_c = phase in ("C", "ALL")

    before = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  Expanded FOIA/Regulatory Collection")
    print(f"  Phase A (Federal Register): {run_a}")
    print(f"  Phase B (FDA Approvals):    {run_b}")
    print(f"  Phase C (FDA Recalls):      {run_c}")
    print(f"  Dataset before: {before:,} events")
    print(f"{'='*62}\n")

    grand_total = 0

    # ── Phase A: Federal Register ─────────────────────────────────────────
    if run_a:
        print("\n--- Phase A: Federal Register ---\n")
        for i, item in enumerate(ALL_TICKERS):
            ticker_sym = item["ticker"]
            company    = item["company"]
            print(f"[{i+1}/{len(ALL_TICKERS)}] {company} ({ticker_sym})")
            n = collect_federal_register(ticker_sym, company, limit=200)
            print(f"  => +{n} Federal Register events")
            grand_total += n
            time.sleep(1)

    # ── Phase B: openFDA Drug Approvals ──────────────────────────────────
    if run_b:
        print("\n--- Phase B: FDA Drug Approvals ---\n")
        pharma_list = list(PHARMA_TICKERS.items())
        for i, (ticker_sym, company) in enumerate(pharma_list):
            print(f"[{i+1}/{len(pharma_list)}] {company} ({ticker_sym})")
            n = collect_fda_approvals(ticker_sym, company, limit=150)
            print(f"  => +{n} FDA approval events")
            grand_total += n
            time.sleep(1)

    # ── Phase C: FDA Recalls ──────────────────────────────────────────────
    if run_c:
        print("\n--- Phase C: FDA Recalls ---\n")
        pharma_list = list(PHARMA_TICKERS.items())
        for i, (ticker_sym, company) in enumerate(pharma_list):
            print(f"[{i+1}/{len(pharma_list)}] {company} ({ticker_sym})")
            n = collect_fda_recalls(ticker_sym, company, limit=100)
            print(f"  => +{n} FDA recall events")
            grand_total += n
            time.sleep(1)

    after = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  Done!")
    print(f"  Dataset: {before:,} -> {after:,}  (+{after - before} events)")
    print(f"  Events with full price data: {grand_total}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
