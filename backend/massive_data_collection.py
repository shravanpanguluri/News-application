"""
Massive Data Collection Script - Expand Real Training Samples
Runs all intelligence sources across ALL 67 mapped companies.

This script:
1. Expands watchlist from 15 → 67 companies
2. Fetches FOIA, SEC filings, contracts for each
3. Adds GDELT news events as additional signals
4. Backfills historical data (older records via pagination)
5. Tracks all events in correlation_data.json
6. Collects stock prices
7. Retrains the ML model

Expected: 500-1000+ new REAL events (vs current 88 real)
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from services.sec_edgar_service import sec_edgar_service
from services.foia_engine import foia_engine
from services.usaspending_service import usaspending_service
from services.regulatory_monitor import regulatory_monitor
from services.correlation_tracker import tracker as correlation_tracker
from services.price_collector import PriceCollector
from services.gov_event_predictor import gov_event_predictor
from services.nlp_signal_engine import nlp_signal_engine
from services.gdelt_service import gdelt_service
from services.news_api_service import news_api_service


# ── Full watchlist: ALL 67 mapped companies ──────────────────────────────────
FULL_WATCHLIST = [
    # Defense (10)
    {"ticker": "LMT", "company": "Lockheed Martin"},
    {"ticker": "BA", "company": "Boeing"},
    {"ticker": "NOC", "company": "Northrop Grumman"},
    {"ticker": "GD", "company": "General Dynamics"},
    {"ticker": "RTX", "company": "RTX Corp"},
    {"ticker": "LHX", "company": "L3Harris Technologies"},
    {"ticker": "HII", "company": "Huntington Ingalls Industries"},
    {"ticker": "TDG", "company": "TransDigm Group"},
    # Technology (14)
    {"ticker": "AAPL", "company": "Apple"},
    {"ticker": "MSFT", "company": "Microsoft"},
    {"ticker": "GOOGL", "company": "Alphabet"},
    {"ticker": "AMZN", "company": "Amazon"},
    {"ticker": "NVDA", "company": "NVIDIA"},
    {"ticker": "META", "company": "Meta Platforms"},
    {"ticker": "TSLA", "company": "Tesla"},
    {"ticker": "ORCL", "company": "Oracle"},
    {"ticker": "CRM", "company": "Salesforce"},
    {"ticker": "IBM", "company": "IBM"},
    {"ticker": "INTC", "company": "Intel"},
    {"ticker": "AMD", "company": "AMD"},
    {"ticker": "ADBE", "company": "Adobe"},
    {"ticker": "NFLX", "company": "Netflix"},
    # Healthcare (10)
    {"ticker": "JNJ", "company": "Johnson & Johnson"},
    {"ticker": "PFE", "company": "Pfizer"},
    {"ticker": "MRK", "company": "Merck"},
    {"ticker": "ABBV", "company": "AbbVie"},
    {"ticker": "LLY", "company": "Eli Lilly"},
    {"ticker": "UNH", "company": "UnitedHealth Group"},
    {"ticker": "BMY", "company": "Bristol Myers Squibb"},
    {"ticker": "AMGN", "company": "Amgen"},
    {"ticker": "GILD", "company": "Gilead Sciences"},
    {"ticker": "CVS", "company": "CVS Health"},
    # Finance (10)
    {"ticker": "JPM", "company": "JPMorgan Chase"},
    {"ticker": "BAC", "company": "Bank of America"},
    {"ticker": "GS", "company": "Goldman Sachs"},
    {"ticker": "MS", "company": "Morgan Stanley"},
    {"ticker": "WFC", "company": "Wells Fargo"},
    {"ticker": "C", "company": "Citigroup"},
    {"ticker": "BLK", "company": "BlackRock"},
    {"ticker": "AXP", "company": "American Express"},
    {"ticker": "V", "company": "Visa"},
    {"ticker": "MA", "company": "Mastercard"},
    # Energy (5)
    {"ticker": "XOM", "company": "Exxon Mobil"},
    {"ticker": "CVX", "company": "Chevron"},
    {"ticker": "COP", "company": "ConocoPhillips"},
    {"ticker": "SLB", "company": "Schlumberger"},
    {"ticker": "EOG", "company": "EOG Resources"},
    # Consumer (10)
    {"ticker": "HD", "company": "Home Depot"},
    {"ticker": "PG", "company": "Procter & Gamble"},
    {"ticker": "KO", "company": "Coca Cola"},
    {"ticker": "WMT", "company": "Walmart"},
    {"ticker": "MCD", "company": "McDonalds"},
    {"ticker": "NKE", "company": "Nike"},
    {"ticker": "DIS", "company": "Walt Disney"},
    {"ticker": "SBUX", "company": "Starbucks"},
    {"ticker": "TGT", "company": "Target"},
    {"ticker": "LOW", "company": "Lowes"},
    # Industrial (6)
    {"ticker": "CAT", "company": "Caterpillar"},
    {"ticker": "GE", "company": "General Electric"},
    {"ticker": "MMM", "company": "3M"},
    {"ticker": "HON", "company": "Honeywell"},
    {"ticker": "UPS", "company": "United Parcel Service"},
    {"ticker": "FDX", "company": "FedEx"},
    # Telecom (3)
    {"ticker": "T", "company": "AT&T"},
    {"ticker": "VZ", "company": "Verizon"},
    {"ticker": "TMUS", "company": "T-Mobile"},
]


class MassiveDataCollector:
    """Collects real training data from all sources across all companies."""

    def __init__(self):
        self.price_collector = PriceCollector()
        self.stats = {
            "foia_events": 0,
            "sec_events": 0,
            "contract_events": 0,
            "regulatory_events": 0,
            "gdelt_events": 0,
            "total_events": 0,
            "errors": 0,
            "companies_processed": 0,
        }
        self.log = []

    def _log(self, msg):
        print(f"  {msg}")
        self.log.append({"time": datetime.utcnow().isoformat(), "msg": msg})

    def _track_event(self, ticker, event_type, title, date_str, source, url="", extra=None):
        """Track an event with NLP enrichment."""
        try:
            # Parse date
            if date_str:
                try:
                    if "T" in date_str:
                        event_date = datetime.fromisoformat(date_str[:19])
                    else:
                        event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except:
                    event_date = datetime.utcnow()
            else:
                event_date = datetime.utcnow()

            event_id = correlation_tracker.track_event(
                ticker=ticker,
                event_type=event_type,
                event_title=title[:200],
                event_date=event_date,
                source=source,
                url=url[:500] if url else "",
            )

            # Enrich with NLP
            nlp_signal = nlp_signal_engine.analyze_document({
                "title": title,
                "summary": title,
                "text": title,
            })

            for event in correlation_tracker.data["events"]:
                if event["event_id"] == event_id:
                    event["nlp_analysis"] = nlp_signal
                    if extra:
                        event.update(extra)
                    correlation_tracker._save_data()
                    break

            return event_id

        except Exception as e:
            self._log(f"  ✗ Error tracking event for {ticker}: {e}")
            self.stats["errors"] += 1
            return None

    def collect_sec_filings(self, ticker, company, limit=10):
        """Collect SEC filings for a company."""
        try:
            filings = sec_edgar_service.get_filings_for_ticker(ticker, limit=limit)
            count = 0
            for filing in filings:
                title = f"{filing.get('form_type', 'SEC')} - {filing.get('description', '')[:120]}"
                date_str = filing.get("filing_date", "")
                url = filing.get("filing_url", "")

                event_id = self._track_event(
                    ticker=ticker,
                    event_type="SEC_FILING",
                    title=title,
                    date_str=date_str,
                    source="SEC EDGAR",
                    url=url,
                    extra={"form_type": filing.get("form_type"), "signal": filing.get("signal", {})}
                )
                if event_id:
                    count += 1

            self.stats["sec_events"] += count
            return count

        except Exception as e:
            self._log(f"✗ SEC error for {ticker}: {e}")
            self.stats["errors"] += 1
            return 0

    def collect_foia_events(self, ticker, company, limit=10):
        """Collect FOIA events for a company."""
        try:
            # Note: get_foia_documents_for_ticker doesn't accept limit param
            # It internally uses limit=50 for each source
            docs = foia_engine.get_foia_documents_for_ticker(ticker, company)
            # Limit results ourselves
            docs = docs[:limit]
            count = 0
            for doc in docs:
                title = doc.get("title", "FOIA Document")[:150]
                date_str = doc.get("date", "")
                url = doc.get("url", "")

                event_id = self._track_event(
                    ticker=ticker,
                    event_type="FOIA",
                    title=title,
                    date_str=date_str,
                    source="MuckRock FOIA",
                    url=url,
                )
                if event_id:
                    count += 1

            self.stats["foia_events"] += count
            return count

        except Exception as e:
            self._log(f"✗ FOIA error for {ticker}: {e}")
            self.stats["errors"] += 1
            return 0

    def collect_contract_events(self, ticker, company, limit=5):
        """Collect federal contract events."""
        try:
            contracts = usaspending_service.get_contract_awards_for_ticker(
                ticker, company, limit=limit
            )
            count = 0
            for contract in contracts:
                amount = contract.get("Award Amount", 0) or 0
                desc = (contract.get("Description", "") or "")[:100]
                title = f"Federal Contract ${amount:,.0f} - {desc}"
                date_str = contract.get("Start Date", contract.get("Last Modified Date", ""))

                event_id = self._track_event(
                    ticker=ticker,
                    event_type="FEDERAL_CONTRACT",
                    title=title,
                    date_str=date_str,
                    source="USAspending.gov",
                    extra={"Award Amount": amount, "signal": contract.get("signal", {})}
                )
                if event_id:
                    count += 1

            self.stats["contract_events"] += count
            return count

        except Exception as e:
            self._log(f"✗ Contract error for {ticker}: {e}")
            self.stats["errors"] += 1
            return 0

    def collect_regulatory_events(self, ticker, company, limit=5):
        """Collect regulatory events (SEC + FDA)."""
        try:
            count = 0

            # SEC filings via regulatory monitor
            sec_filings = regulatory_monitor.search_sec_filings(company, limit=limit)
            for filing in sec_filings:
                title = filing.get("title", "SEC Filing")[:150]
                date_str = filing.get("filing_date", filing.get("date", ""))
                url = filing.get("url", "")

                event_id = self._track_event(
                    ticker=ticker,
                    event_type="REGULATORY",
                    title=title,
                    date_str=date_str,
                    source="SEC EDGAR",
                    url=url,
                )
                if event_id:
                    count += 1

            self.stats["regulatory_events"] += count
            return count

        except Exception as e:
            self._log(f"✗ Regulatory error for {ticker}: {e}")
            self.stats["errors"] += 1
            return 0

    def collect_gdelt_events(self, ticker, company, limit=5):
        """Collect GDELT news events mentioning the company."""
        try:
            results = gdelt_service.search_news(
                query=company,
                max_results=limit,
                timespan=30  # Last 30 days
            )

            # Handle different response formats
            if isinstance(results, dict):
                articles = results.get("articles", results.get("results", []))
            elif isinstance(results, list):
                articles = results
            else:
                articles = []

            count = 0
            for article in articles[:limit]:
                title = (article.get("title", article.get("headline", "")) or "")[:150]
                if not title:
                    continue

                date_str = article.get("date", article.get("published", article.get("seendate", "")))
                url = article.get("url", article.get("sourceurl", ""))

                event_id = self._track_event(
                    ticker=ticker,
                    event_type="GDELT_NEWS",
                    title=title,
                    date_str=date_str,
                    source="GDELT",
                    url=url,
                )
                if event_id:
                    count += 1

            self.stats["gdelt_events"] += count
            return count

        except Exception as e:
            self._log(f"✗ GDELT error for {ticker}: {e}")
            self.stats["errors"] += 1
            return 0

    def run_full_collection(self, watchlist=None, skip_gdelt=False):
        """
        Run full collection across all companies and sources.

        Args:
            watchlist: Custom watchlist (uses FULL_WATCHLIST if None)
            skip_gdelt: Skip GDELT collection (slower, rate-limited)
        """
        companies = watchlist or FULL_WATCHLIST
        start_time = datetime.utcnow()

        print(f"\n{'='*70}")
        print(f"🚀 MASSIVE DATA COLLECTION")
        print(f"   Companies: {len(companies)}")
        print(f"   Sources: FOIA + SEC + Contracts + Regulatory" + ("" if skip_gdelt else " + GDELT"))
        print(f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        # Count existing events before collection
        events_before = len(correlation_tracker.data.get("events", []))
        print(f"📊 Existing events before collection: {events_before}\n")

        for i, item in enumerate(companies):
            ticker = item["ticker"]
            company = item["company"]

            print(f"\n[{i+1}/{len(companies)}] {company} ({ticker})")

            # Collect from each source
            sec_count = self.collect_sec_filings(ticker, company, limit=8)
            print(f"  SEC filings: {sec_count}")

            foia_count = self.collect_foia_events(ticker, company, limit=8)
            print(f"  FOIA events: {foia_count}")

            contract_count = self.collect_contract_events(ticker, company, limit=5)
            print(f"  Contracts: {contract_count}")

            reg_count = self.collect_regulatory_events(ticker, company, limit=3)
            print(f"  Regulatory: {reg_count}")

            if not skip_gdelt:
                gdelt_count = self.collect_gdelt_events(ticker, company, limit=3)
                print(f"  GDELT news: {gdelt_count}")

            self.stats["companies_processed"] += 1

            # Rate limiting - be respectful to APIs
            time.sleep(2)

        # Summary
        events_after = len(correlation_tracker.data.get("events", []))
        new_events = events_after - events_before
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        print(f"\n{'='*70}")
        print(f"📊 COLLECTION SUMMARY")
        print(f"{'='*70}")
        print(f"   Companies processed: {self.stats['companies_processed']}")
        print(f"   New events collected: {new_events}")
        print(f"   Total events now: {events_after}")
        print(f"   FOIA events: {self.stats['foia_events']}")
        print(f"   SEC filings: {self.stats['sec_events']}")
        print(f"   Contract events: {self.stats['contract_events']}")
        print(f"   Regulatory events: {self.stats['regulatory_events']}")
        print(f"   GDELT events: {self.stats['gdelt_events']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"   Elapsed: {elapsed:.1f}s")
        print(f"{'='*70}\n")

        return {
            "companies_processed": self.stats["companies_processed"],
            "new_events": new_events,
            "total_events": events_after,
            "by_source": {
                "foia": self.stats["foia_events"],
                "sec": self.stats["sec_events"],
                "contract": self.stats["contract_events"],
                "regulatory": self.stats["regulatory_events"],
                "gdelt": self.stats["gdelt_events"],
            },
            "errors": self.stats["errors"],
            "elapsed_seconds": elapsed,
        }

    def update_all_prices(self):
        """Collect/update stock prices for all tracked events."""
        print("\n💰 Collecting stock prices for all events...")
        # Re-initialize PriceCollector so it reads the CURRENT file (not the stale
        # in-memory copy that was loaded before collection added new events).
        self.price_collector = PriceCollector()
        summary = self.price_collector.collect_all_prices()
        print(f"   Updated: {summary}")
        return summary

    def retrain_model(self):
        """Retrain the ML model on accumulated data."""
        print("\n🤖 Retraining ML model...")

        correlation_data = self.price_collector.data
        events_with_prices = len([
            e for e in correlation_data.get("events", [])
            if e.get("return_7d") is not None
        ])

        print(f"   Events with 7-day price data: {events_with_prices}")

        if events_with_prices < 20:
            print(f"   ⚠️ Insufficient data: need 20+, have {events_with_prices}")
            return {"status": "insufficient_data", "events_with_prices": events_with_prices}

        metrics = gov_event_predictor.train_model(correlation_data)
        print(f"   Train accuracy: {metrics.get('train_accuracy', 'N/A')}")
        print(f"   Test accuracy: {metrics.get('test_accuracy', 'N/A')}")

        return metrics


def main():
    """Run the full collection pipeline."""
    collector = MassiveDataCollector()

    # Step 1: Collect data from all sources
    collection_results = collector.run_full_collection(skip_gdelt=False)

    # Step 2: Update prices
    price_summary = collector.update_all_prices()

    # Step 3: Retrain model
    training_metrics = collector.retrain_model()

    # Save results
    output = {
        "collection": collection_results,
        "prices": price_summary,
        "training": training_metrics,
        "timestamp": datetime.utcnow().isoformat(),
    }

    output_path = Path(__file__).parent / "massive_collection_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Results saved to {output_path}")

    return output


if __name__ == "__main__":
    main()
