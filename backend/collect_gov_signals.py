"""
Multi-source Government Signal Collection
Adds 6 new event types not yet in the training data:

  A) SEC Enforcement Releases  — litigation releases from sec.gov (no key needed)
  B) DOJ Press Releases        — antitrust/settlement/FCPA scraping (no key needed)
  C) Congress.gov Bills        — legislation affecting specific industries (DEMO_KEY or set CONGRESS_API_KEY)
  D) SAM.gov Opportunities     — pre-award contract signals (set SAM_API_KEY)
  E) CourtListener Cases       — PACER dockets (set COURT_API_TOKEN)
  F) CFPB Enforcement          — consumer finance enforcement (banking tickers)

Run from backend/:
    source venv/bin/activate && python collect_gov_signals.py
    source venv/bin/activate && python collect_gov_signals.py --phase A
    source venv/bin/activate && python collect_gov_signals.py --phase B
    source venv/bin/activate && python collect_gov_signals.py --phase C

API keys (optional — phases D/E skip gracefully without them):
    export SAM_API_KEY=your_key_from_api.sam.gov
    export CONGRESS_API_KEY=your_key_from_api.congress.gov
    export COURT_API_TOKEN=your_token_from_courtlistener.com
"""
import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yfinance as yf
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, str(Path(__file__).parent))
from services.correlation_tracker import tracker

_vader       = SentimentIntensityAnalyzer()
_price_cache = {}
_HEADERS     = {"User-Agent": "GovPulse-Research/1.0 shrav494@gmail.com"}

# ── Ticker → company name map (all tickers in dataset) ───────────────────────
TICKER_MAP = {
    # Defense / Aerospace
    "LMT": "Lockheed Martin", "RTX": "Raytheon", "NOC": "Northrop Grumman",
    "GD": "General Dynamics", "BA": "Boeing", "LHX": "L3Harris",
    "HII": "Huntington Ingalls", "TDG": "TransDigm", "HEI": "HEICO",
    "KTOS": "Kratos Defense", "MRCY": "Mercury Systems", "DRS": "Leonardo DRS",
    "AXON": "Axon Enterprise", "AVAV": "AeroVironment", "TXT": "Textron",
    "CW": "Curtiss-Wright", "MOOG": "Moog", "HWM": "Howmet Aerospace",
    # Gov IT / Consulting
    "BAH": "Booz Allen Hamilton", "LDOS": "Leidos", "CACI": "CACI International",
    "SAIC": "SAIC", "PLTR": "Palantir", "ACN": "Accenture",
    # Infrastructure
    "J": "Jacobs Engineering", "ACM": "AECOM", "FLR": "Fluor",
    "PWR": "Quanta Services", "GE": "General Electric", "HON": "Honeywell",
    "MMM": "3M", "CAT": "Caterpillar", "DE": "Deere",
    "EMR": "Emerson Electric", "ETN": "Eaton", "PH": "Parker Hannifin",
    # Big Tech
    "MSFT": "Microsoft", "AMZN": "Amazon", "GOOGL": "Google",
    "IBM": "IBM", "ORCL": "Oracle", "DELL": "Dell Technologies",
    "HPE": "Hewlett Packard", "CDNS": "Cadence Design", "ANSS": "ANSYS",
    # Semiconductors
    "NVDA": "NVIDIA", "INTC": "Intel", "AMD": "AMD",
    "QCOM": "Qualcomm", "TXN": "Texas Instruments", "AMAT": "Applied Materials",
    # Pharma / Biotech
    "PFE": "Pfizer", "JNJ": "Johnson Johnson", "MRK": "Merck",
    "LLY": "Eli Lilly", "ABBV": "AbbVie", "AMGN": "Amgen",
    "GILD": "Gilead", "BMY": "Bristol-Myers Squibb", "MRNA": "Moderna",
    "REGN": "Regeneron", "VRTX": "Vertex", "BIIB": "Biogen",
    "AZN": "AstraZeneca", "BNTX": "BioNTech", "GSK": "GSK",
    "SNY": "Sanofi", "ILMN": "Illumina",
    # Healthcare
    "UNH": "UnitedHealth", "CVS": "CVS Health", "HUM": "Humana",
    "CI": "Cigna", "CNC": "Centene", "MOH": "Molina Healthcare",
    "ELV": "Elevance Health", "HCA": "HCA Healthcare", "MCK": "McKesson",
    "SYK": "Stryker", "ISRG": "Intuitive Surgical", "ZBH": "Zimmer Biomet",
    "MDT": "Medtronic", "ABT": "Abbott", "TMO": "Thermo Fisher",
    "DHR": "Danaher", "BSX": "Boston Scientific", "DGX": "Quest Diagnostics",
    "LH": "Labcorp", "GEHC": "GE HealthCare",
    # Energy
    "XOM": "ExxonMobil", "CVX": "Chevron", "COP": "ConocoPhillips",
    "OXY": "Occidental Petroleum", "HAL": "Halliburton", "SLB": "Schlumberger",
    "BKR": "Baker Hughes", "PSX": "Phillips 66", "EOG": "EOG Resources",
    "NEE": "NextEra Energy", "SO": "Southern Company",
    # Finance
    "JPM": "JPMorgan Chase", "BAC": "Bank of America", "WFC": "Wells Fargo",
    "GS": "Goldman Sachs", "MS": "Morgan Stanley", "C": "Citigroup",
    "BLK": "BlackRock", "AXP": "American Express", "V": "Visa", "MA": "Mastercard",
    # Consumer / Other
    "WMT": "Walmart", "AAPL": "Apple", "META": "Meta", "TSLA": "Tesla",
    "NFLX": "Netflix", "DIS": "Disney", "ADBE": "Adobe", "CRM": "Salesforce",
    "NKE": "Nike", "MCD": "McDonalds", "SBUX": "Starbucks", "KO": "Coca-Cola",
    "FDX": "FedEx", "UPS": "UPS", "HD": "Home Depot", "LOW": "Lowes",
    "TGT": "Target", "T": "AT&T", "VZ": "Verizon", "TMUS": "T-Mobile",
    "VSAT": "Viasat", "VRSK": "Verisk Analytics", "PG": "Procter Gamble",
    "F": "Ford Motor", "GM": "General Motors",
}

# Reverse map: keyword → ticker (for matching enforcement release titles)
_KEYWORD_TO_TICKER = {}
for _ticker, _company in TICKER_MAP.items():
    for _word in _company.lower().split():
        if len(_word) > 3:
            _KEYWORD_TO_TICKER.setdefault(_word, []).append(_ticker)

# Industry → tickers (for Congress bills)
INDUSTRY_QUERIES = {
    "pharmaceutical drug pricing": ["PFE", "JNJ", "MRK", "LLY", "ABBV", "AMGN", "GILD", "BMY", "MRNA", "REGN", "VRTX", "BIIB", "AZN", "BNTX", "GSK", "SNY"],
    "Medicare Medicaid health insurance": ["UNH", "CVS", "HUM", "CI", "CNC", "MOH", "ELV", "HCA", "MCK"],
    "defense appropriations NDAA": ["LMT", "RTX", "NOC", "GD", "BA", "LHX", "HII", "TDG", "KTOS", "BAH", "LDOS", "CACI", "SAIC", "AVAV", "TXT", "MOOG"],
    "semiconductor chip export control": ["NVDA", "INTC", "AMD", "QCOM", "TXN", "AMAT"],
    "antitrust merger big tech": ["GOOGL", "AMZN", "MSFT", "META", "AAPL"],
    "banking financial regulation": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "AXP"],
    "energy climate fossil fuel": ["XOM", "CVX", "COP", "OXY", "HAL", "SLB", "BKR", "PSX", "NEE", "SO"],
    "FDA medical device approval": ["MDT", "ABT", "BSX", "SYK", "ISRG", "ZBH", "DGX", "LH", "GEHC"],
}


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


def _match_tickers(text):
    """Find tickers whose company name appears in the given text."""
    text_lower = text.lower()
    matched = set()
    for ticker, company in TICKER_MAP.items():
        # Match on company name words (at least 2 consecutive significant words)
        words = [w for w in company.lower().split() if len(w) > 3]
        for w in words:
            if w in text_lower:
                matched.add(ticker)
                break
    return list(matched)


def _parse_date(date_str):
    """Parse various date string formats."""
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except Exception:
            continue
    # Try partial parse
    m = re.search(r'(\d{4})', date_str)
    if m:
        try:
            return datetime.strptime(date_str.strip(), "%B %Y")
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase A: SEC Enforcement Releases
# ─────────────────────────────────────────────────────────────────────────────

SEC_BASE     = "https://www.sec.gov"
SEC_LR_START = "https://www.sec.gov/litigation/litreleases.htm"


def _scrape_sec_lr_page(page=0):
    """Scrape one page of SEC litigation releases. Returns list of (date_str, title, url)."""
    url = f"{SEC_LR_START}?page={page}" if page > 0 else SEC_LR_START
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tr")
        results = []
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            date_str = cols[0].get_text(strip=True)
            a        = cols[1].find("a")
            title    = a.get_text(strip=True) if a else cols[1].get_text(strip=True)
            href     = a.get("href", "") if a else ""
            full_url = (SEC_BASE + href) if href.startswith("/") else href
            if date_str and title:
                results.append((date_str, title, full_url))
        return results
    except Exception as e:
        print(f"    ! SEC LR page {page} error: {e}")
        return []


def collect_sec_enforcement(max_pages=40):
    """
    Scrape SEC enforcement/litigation releases (LR-XXXXX series) and match to tickers.
    Goes back ~5 years (100 per page × max_pages).
    """
    total_added = 0
    ticker_counts = {}
    cutoff = datetime(2016, 1, 1)

    print(f"  Scraping SEC enforcement releases ({max_pages} pages)…")

    for page in range(max_pages):
        rows = _scrape_sec_lr_page(page)
        if not rows:
            print(f"  No rows on page {page}, stopping.")
            break

        stop_early = False
        for date_str, title, url in rows:
            event_date = _parse_date(date_str)
            if event_date is None:
                continue
            if event_date < cutoff:
                stop_early = True
                break

            # Match to tickers
            matched = _match_tickers(title)
            if not matched:
                continue

            for ticker_sym in matched:
                existing = _existing_dates(ticker_sym)
                nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
                if nearby & existing:
                    continue

                event_title = f"SEC Enforcement: {title}"[:200]
                event_id = tracker.track_event(
                    ticker=ticker_sym,
                    event_type="sec_enforcement",
                    event_title=event_title,
                    event_date=event_date,
                    source="SEC Litigation",
                    url=url,
                )
                if _backfill(event_id, ticker_sym, event_date, event_title):
                    total_added += 1
                    ticker_counts[ticker_sym] = ticker_counts.get(ticker_sym, 0) + 1
                    print(f"    + {ticker_sym} SEC {event_date.date()}  {title[:55]}")
                time.sleep(0.3)

        if stop_early:
            print(f"  Reached cutoff ({cutoff.year}) at page {page}.")
            break

        time.sleep(0.5)

    if ticker_counts:
        print(f"\n  Top matched tickers: {sorted(ticker_counts.items(), key=lambda x: -x[1])[:10]}")
    return total_added


# ─────────────────────────────────────────────────────────────────────────────
# Phase B: DOJ Press Releases (Antitrust + Settlement)
# ─────────────────────────────────────────────────────────────────────────────

DOJ_SEARCH_BASE = "https://www.justice.gov"
DOJ_ATR_BASE    = "https://www.justice.gov/atr"

# DOJ publishes structured press release pages via Drupal
_DOJ_KEYWORDS = [
    "billion", "million settlement", "plea agreement", "antitrust",
    "merger", "acquisition", "FCPA", "False Claims Act",
]


def _scrape_doj_page(url):
    """Scrape a single DOJ press release page for title, date, body."""
    try:
        r = requests.get(url, headers={**_HEADERS, "User-Agent": "Mozilla/5.0 GovPulse shrav494@gmail.com"}, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        # DOJ Drupal structure: h3.node__title > a
        for node in soup.select("h3.node__title a, .views-field-title a, article h3 a"):
            href  = node.get("href", "")
            title = node.get_text(strip=True)
            if href and title:
                full_url = DOJ_SEARCH_BASE + href if href.startswith("/") else href
                items.append((title, full_url))
        return items
    except Exception as e:
        print(f"  ! DOJ page error: {e}")
        return []


def _fetch_doj_release_date(url):
    """Fetch a single DOJ press release page to extract the date."""
    try:
        r = requests.get(url, headers={**_HEADERS, "User-Agent": "Mozilla/5.0 GovPulse shrav494@gmail.com"}, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        # DOJ puts date in <time datetime="..."> or .field-name-post-date
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            dt_str = time_tag["datetime"][:10]
            try:
                return datetime.strptime(dt_str, "%Y-%m-%d")
            except Exception:
                pass
        # Fallback: look for date text patterns
        text = soup.get_text()
        m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', text)
        if m:
            return _parse_date(m.group(0))
        return None
    except Exception:
        return None


def collect_doj_releases(max_pages=20):
    """Scrape DOJ Antitrust Division press releases and match to tickers."""
    total_added = 0
    cutoff = datetime(2016, 1, 1)

    # DOJ ATR press releases (most relevant for our tickers)
    urls_to_scrape = [
        f"https://www.justice.gov/atr/news/press-releases?page={p}" for p in range(max_pages)
    ]
    # Also main OPA press releases
    urls_to_scrape += [
        f"https://www.justice.gov/opa/press-releases?page={p}" for p in range(max_pages // 2)
    ]

    for list_url in urls_to_scrape:
        releases = _scrape_doj_page(list_url)
        if not releases:
            time.sleep(0.5)
            continue

        for title, pr_url in releases:
            # Pre-filter: only process releases that mention relevant companies or keywords
            matches = _match_tickers(title)
            has_keyword = any(kw.lower() in title.lower() for kw in _DOJ_KEYWORDS)
            if not matches and not has_keyword:
                continue

            # Fetch the release to get the date
            event_date = _fetch_doj_release_date(pr_url)
            if event_date is None or event_date < cutoff:
                time.sleep(0.2)
                continue

            # If no direct ticker match from title, try with the full page body
            if not matches:
                try:
                    r = requests.get(pr_url, headers={**_HEADERS, "User-Agent": "Mozilla/5.0"}, timeout=10)
                    if r.ok:
                        body = BeautifulSoup(r.text, "html.parser").get_text()[:2000]
                        matches = _match_tickers(body)
                except Exception:
                    pass

            if not matches:
                time.sleep(0.2)
                continue

            for ticker_sym in matches:
                existing = _existing_dates(ticker_sym)
                nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
                if nearby & existing:
                    continue

                event_title = f"DOJ: {title}"[:200]
                event_id = tracker.track_event(
                    ticker=ticker_sym,
                    event_type="doj_enforcement",
                    event_title=event_title,
                    event_date=event_date,
                    source="DOJ Press Release",
                    url=pr_url,
                )
                if _backfill(event_id, ticker_sym, event_date, event_title):
                    total_added += 1
                    print(f"    + {ticker_sym} DOJ {event_date.date()}  {title[:55]}")
                time.sleep(0.4)

        time.sleep(1)

    return total_added


# ─────────────────────────────────────────────────────────────────────────────
# Phase C: Congress.gov Industry Bills
# ─────────────────────────────────────────────────────────────────────────────

CONGRESS_KEY = os.environ.get("CONGRESS_API_KEY", "DEMO_KEY")
CONGRESS_BASE = "https://api.congress.gov/v3"


def collect_congress_bills():
    """Search Congress.gov for bills affecting specific industries and map to tickers."""
    total_added = 0
    cutoff = datetime(2016, 1, 1)
    # DEMO_KEY: 5 req/hr — be conservative
    delay = 2 if CONGRESS_KEY == "DEMO_KEY" else 0.5

    print(f"  Congress.gov API key: {'DEMO_KEY (limited)' if CONGRESS_KEY == 'DEMO_KEY' else 'Custom key'}")

    for query, affected_tickers in INDUSTRY_QUERIES.items():
        try:
            r = requests.get(
                f"{CONGRESS_BASE}/bill",
                params={
                    "api_key": CONGRESS_KEY,
                    "query":   query,
                    "limit":   20,
                    "sort":    "updateDate+desc",
                },
                headers=_HEADERS,
                timeout=15,
            )
            if r.status_code == 429:
                print(f"  ! Congress rate limited. Set CONGRESS_API_KEY for higher limits.")
                break
            if r.status_code != 200:
                print(f"  ! Congress error {r.status_code} for '{query}'")
                time.sleep(delay)
                continue

            bills = r.json().get("bills", [])
            print(f"  Query '{query[:50]}': {len(bills)} bills → {len(affected_tickers)} tickers")

            for bill in bills:
                action_date_str = bill.get("latestAction", {}).get("actionDate", "")
                if not action_date_str:
                    continue
                try:
                    event_date = datetime.strptime(action_date_str, "%Y-%m-%d")
                except Exception:
                    continue
                if event_date < cutoff:
                    continue

                bill_num   = f"{bill.get('type','')}{bill.get('number','')}"
                title      = bill.get("title", "Congressional Bill")[:150]
                action_txt = bill.get("latestAction", {}).get("text", "")
                url        = bill.get("url", "")
                full_title = f"Congress {bill_num}: {title}"[:200]

                for ticker_sym in affected_tickers:
                    existing = _existing_dates(ticker_sym)
                    nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
                    if nearby & existing:
                        continue

                    event_id = tracker.track_event(
                        ticker=ticker_sym,
                        event_type="legislation",
                        event_title=full_title,
                        event_date=event_date,
                        source="Congress.gov",
                        url=url,
                    )
                    if _backfill(event_id, ticker_sym, event_date, full_title):
                        total_added += 1
                        print(f"    + {ticker_sym} BILL {event_date.date()}  {title[:55]}")
                    time.sleep(0.2)

        except Exception as e:
            print(f"  ! Congress error for '{query}': {e}")

        time.sleep(delay)

    return total_added


# ─────────────────────────────────────────────────────────────────────────────
# Phase D: SAM.gov Contract Opportunities (pre-award signals)
# ─────────────────────────────────────────────────────────────────────────────

SAM_KEY  = os.environ.get("SAM_API_KEY", "")
SAM_BASE = "https://api.sam.gov/opportunities/v2/search"

# Tickers with strongest DoD pre-award signal
SAM_TICKERS = {
    "LMT": "Lockheed Martin", "RTX": "Raytheon", "NOC": "Northrop Grumman",
    "GD": "General Dynamics", "BA": "Boeing", "LHX": "L3Harris",
    "HII": "Huntington Ingalls", "BAH": "Booz Allen", "LDOS": "Leidos",
    "CACI": "CACI", "SAIC": "SAIC", "PLTR": "Palantir",
    "KTOS": "Kratos", "AVAV": "AeroVironment", "CW": "Curtiss-Wright",
}


def collect_sam_opportunities():
    """Fetch pre-award DoD contract opportunities from SAM.gov."""
    if not SAM_KEY:
        print("  SAM_API_KEY not set. Skipping Phase D.")
        print("  → Get a free key at: https://api.sam.gov (register → API keys)")
        print("  → Then: export SAM_API_KEY=your_key && python collect_gov_signals.py --phase D")
        return 0

    total_added = 0
    cutoff = datetime(2016, 1, 1)

    for ticker_sym, company in SAM_TICKERS.items():
        try:
            # Search for opportunities mentioning this company
            end_dt   = datetime.now()
            start_dt = end_dt - timedelta(days=365 * 5)
            r = requests.get(
                SAM_BASE,
                params={
                    "api_key":    SAM_KEY,
                    "keyword":    company,
                    "limit":      100,
                    "postedFrom": start_dt.strftime("%m/%d/%Y"),
                    "postedTo":   end_dt.strftime("%m/%d/%Y"),
                },
                headers=_HEADERS,
                timeout=20,
            )
            if r.status_code != 200:
                print(f"  ! SAM error {r.status_code} for {ticker_sym}")
                continue

            opps = r.json().get("opportunitiesData", [])
            print(f"  {company} ({ticker_sym}): {len(opps)} opportunities")
            existing = _existing_dates(ticker_sym)

            for opp in opps:
                date_str = opp.get("postedDate", "")
                if not date_str:
                    continue
                try:
                    event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except Exception:
                    continue
                if event_date < cutoff:
                    continue

                nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
                if nearby & existing:
                    continue

                title    = (opp.get("title") or f"Contract Opportunity: {company}")[:200]
                naics    = opp.get("naicsCode", "")
                dept     = opp.get("organizationHierarchy", [{}])[0].get("name", "") if opp.get("organizationHierarchy") else ""
                full_ttl = f"SAM Opportunity: {title}"[:200]

                event_id = tracker.track_event(
                    ticker=ticker_sym,
                    event_type="contract_opportunity",
                    event_title=full_ttl,
                    event_date=event_date,
                    source="SAM.gov",
                    url=opp.get("uiLink", ""),
                )
                if _backfill(event_id, ticker_sym, event_date, full_ttl):
                    total_added += 1
                    existing.add(event_date.strftime("%Y-%m-%d"))
                    print(f"    + {ticker_sym} SAM {event_date.date()}  {title[:55]}")
                time.sleep(0.3)

        except Exception as e:
            print(f"  ! SAM error for {ticker_sym}: {e}")
        time.sleep(1)

    return total_added


# ─────────────────────────────────────────────────────────────────────────────
# Phase E: CourtListener — Antitrust / SEC / DOJ Court Cases
# ─────────────────────────────────────────────────────────────────────────────

COURT_TOKEN = os.environ.get("COURT_API_TOKEN", "")
COURT_BASE  = "https://www.courtlistener.com/api/rest/v4"


def collect_courtlistener():
    """Fetch federal court dockets mentioning our companies from CourtListener/RECAP."""
    if not COURT_TOKEN:
        print("  COURT_API_TOKEN not set. Skipping Phase E.")
        print("  → Register free at: https://www.courtlistener.com/sign-in/")
        print("  → Then: export COURT_API_TOKEN=your_token && python collect_gov_signals.py --phase E")
        return 0

    total_added = 0
    cutoff = datetime(2016, 1, 1)
    auth_headers = {**_HEADERS, "Authorization": f"Token {COURT_TOKEN}"}

    for ticker_sym, company in list(TICKER_MAP.items())[:30]:  # top-30 for initial run
        try:
            r = requests.get(
                f"{COURT_BASE}/dockets/",
                params={
                    "party_name": company,
                    "order_by":   "-date_filed",
                    "page_size":  20,
                    # Only federal courts (DoJ, SEC enforcement courts)
                    "court":      "ca1,ca2,ca3,ca4,ca5,ca6,ca7,ca8,ca9,ca10,ca11,cadc,cafc,dcd",
                },
                headers=auth_headers,
                timeout=15,
            )
            if r.status_code == 401:
                print("  ! CourtListener: invalid token")
                break
            if r.status_code != 200:
                continue

            dockets = r.json().get("results", [])
            print(f"  {company} ({ticker_sym}): {len(dockets)} court dockets")
            existing = _existing_dates(ticker_sym)

            for d in dockets:
                date_str = d.get("date_filed", "")
                if not date_str:
                    continue
                try:
                    event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except Exception:
                    continue
                if event_date < cutoff:
                    continue

                nearby = {(event_date - timedelta(days=dt)).strftime("%Y-%m-%d") for dt in range(-1, 2)}
                if nearby & existing:
                    continue

                case_name = (d.get("case_name") or "Unknown Case")[:100]
                court     = d.get("court", "")
                title     = f"Court: {case_name} ({court})"[:200]

                event_id = tracker.track_event(
                    ticker=ticker_sym,
                    event_type="court_case",
                    event_title=title,
                    event_date=event_date,
                    source="CourtListener",
                    url=f"https://www.courtlistener.com{d.get('absolute_url', '')}",
                )
                if _backfill(event_id, ticker_sym, event_date, title):
                    total_added += 1
                    existing.add(event_date.strftime("%Y-%m-%d"))
                    print(f"    + {ticker_sym} COURT {event_date.date()}  {case_name[:50]}")
                time.sleep(0.3)

        except Exception as e:
            print(f"  ! CourtListener error for {ticker_sym}: {e}")
        time.sleep(1)

    return total_added


# ─────────────────────────────────────────────────────────────────────────────
# Phase F: CFPB Consumer Complaint Volume (banking tickers)
# ─────────────────────────────────────────────────────────────────────────────

CFPB_TICKERS = {
    "JPM": "JPMORGAN CHASE", "BAC": "BANK OF AMERICA",
    "WFC": "WELLS FARGO", "GS": "GOLDMAN SACHS",
    "MS": "MORGAN STANLEY", "C": "CITIBANK",
    "AXP": "AMERICAN EXPRESS", "BLK": "BLACKROCK",
}


def collect_cfpb_spikes():
    """
    Track monthly CFPB complaint spikes for banking tickers.
    A spike (>2x average) is itself a material signal (e.g. WFC 2016 fake accounts).
    """
    total_added = 0
    cutoff = datetime(2016, 1, 1)

    for ticker_sym, company_name in CFPB_TICKERS.items():
        try:
            # Get complaint counts by month
            r = requests.get(
                "https://api.consumerfinance.gov/data-research/consumer-complaints/search.json",
                params={
                    "company": company_name,
                    "size":    0,  # aggregation only
                    "format":  "json",
                },
                headers=_HEADERS,
                timeout=15,
            )
            if not r.ok or not r.text.strip() or r.headers.get("content-type", "").startswith("text/html"):
                # CFPB API has changed — skip gracefully
                print(f"  CFPB API unavailable for {ticker_sym}, skipping.")
                break

            data = r.json()
            aggs = data.get("aggregations", {})
            by_date = aggs.get("by_date", {}).get("buckets", [])
            if not by_date:
                continue

            # Calculate average
            counts  = [b.get("doc_count", 0) for b in by_date]
            avg     = sum(counts) / len(counts) if counts else 1
            existing = _existing_dates(ticker_sym)

            for bucket in by_date:
                count = bucket.get("doc_count", 0)
                if count < avg * 2.0:  # Only significant spikes
                    continue
                date_str = bucket.get("key_as_string", "")[:10]
                if not date_str:
                    continue
                try:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d")
                except Exception:
                    continue
                if event_date < cutoff:
                    continue

                nearby = {(event_date - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)}
                if nearby & existing:
                    continue

                title    = f"CFPB Complaint Spike: {company_name} ({count:,} complaints, {count/avg:.1f}x avg)"[:200]
                event_id = tracker.track_event(
                    ticker=ticker_sym,
                    event_type="cfpb_spike",
                    event_title=title,
                    event_date=event_date,
                    source="CFPB",
                    url="https://api.consumerfinance.gov/data-research/consumer-complaints/",
                )
                if _backfill(event_id, ticker_sym, event_date, title):
                    total_added += 1
                    existing.add(date_str)
                    print(f"    + {ticker_sym} CFPB spike {event_date.date()}  {count:,} complaints ({count/avg:.1f}x)")
                time.sleep(0.2)

        except Exception as e:
            print(f"  ! CFPB error for {ticker_sym}: {e}")

    return total_added


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["A", "B", "C", "D", "E", "F", "all"], default="all",
                   help="A=SEC Enforcement, B=DOJ, C=Congress, D=SAM.gov, E=CourtListener, F=CFPB")
    p.add_argument("--sec-pages", type=int, default=40,
                   help="Pages of SEC enforcement releases to scrape (default 40 = ~5 years)")
    return p.parse_args()


def main():
    args  = parse_args()
    phase = args.phase.upper()

    before = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  Government Signal Collection — Multi-Source")
    print(f"  Phase: {phase}")
    print(f"  Dataset before: {before:,} events")
    if not SAM_KEY:
        print(f"  SAM_API_KEY:    NOT SET (Phase D will skip)")
    if not COURT_TOKEN:
        print(f"  COURT_API_TOKEN: NOT SET (Phase E will skip)")
    if CONGRESS_KEY == "DEMO_KEY":
        print(f"  CONGRESS key:   DEMO_KEY (5 req/hr limit)")
    print(f"{'='*62}\n")

    grand_total = 0
    phases_run  = []

    if phase in ("A", "ALL"):
        print("\n--- Phase A: SEC Enforcement Releases ---\n")
        n = collect_sec_enforcement(max_pages=args.sec_pages)
        print(f"\n  Phase A total: +{n} events")
        grand_total += n
        phases_run.append(f"A(SEC)=+{n}")

    if phase in ("B", "ALL"):
        print("\n--- Phase B: DOJ Press Releases ---\n")
        n = collect_doj_releases(max_pages=20)
        print(f"\n  Phase B total: +{n} events")
        grand_total += n
        phases_run.append(f"B(DOJ)=+{n}")

    if phase in ("C", "ALL"):
        print("\n--- Phase C: Congress.gov Bills ---\n")
        n = collect_congress_bills()
        print(f"\n  Phase C total: +{n} events")
        grand_total += n
        phases_run.append(f"C(Congress)=+{n}")

    if phase in ("D", "ALL"):
        print("\n--- Phase D: SAM.gov Contract Opportunities ---\n")
        n = collect_sam_opportunities()
        print(f"\n  Phase D total: +{n} events")
        grand_total += n
        phases_run.append(f"D(SAM)=+{n}")

    if phase in ("E", "ALL"):
        print("\n--- Phase E: CourtListener Court Cases ---\n")
        n = collect_courtlistener()
        print(f"\n  Phase E total: +{n} events")
        grand_total += n
        phases_run.append(f"E(Court)=+{n}")

    if phase in ("F", "ALL"):
        print("\n--- Phase F: CFPB Complaint Spikes ---\n")
        n = collect_cfpb_spikes()
        print(f"\n  Phase F total: +{n} events")
        grand_total += n
        phases_run.append(f"F(CFPB)=+{n}")

    after = len(tracker.data["events"])
    print(f"\n{'='*62}")
    print(f"  Done! Phases: {', '.join(phases_run)}")
    print(f"  Dataset: {before:,} -> {after:,}  (+{after - before} events)")
    print(f"  Events with full price data: {grand_total}")
    print(f"{'='*62}\n")
    print("  Next: python retrain_production_models.py --n-iter 60")


if __name__ == "__main__":
    main()
