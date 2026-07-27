"""
Automated Intelligence Pipeline - End-to-End Data Collection
Connects all intelligence sources → event tracking → price collection → ML training

Pipeline stages:
1. COLLECT: Fetch FOIA, SEC filings, contracts, regulatory actions
2. ANALYZE: NLP signal extraction on each document
3. TRACK: Log events to correlation tracker
4. PRICE: Collect stock prices at 1/7/30 day intervals
5. TRAIN: Retrain ML model when sufficient data exists
6. PREDICT: Generate predictions for new events

This is the ORCHESTRATION layer that makes the system work end-to-end.
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import time

# Import all services
from services.foia_engine import foia_engine
from services.usaspending_service import usaspending_service
from services.sec_edgar_service import sec_edgar_service
from services.regulatory_monitor import regulatory_monitor
from services.correlation_tracker import tracker as correlation_tracker
from services.price_collector import PriceCollector
from services.gov_event_predictor import gov_event_predictor
from services.nlp_signal_engine import nlp_signal_engine


class IntelligencePipeline:
    """
    Automated Intelligence Pipeline

    Orchestrates the full data collection → analysis → training → prediction cycle.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent

        self.price_collector = PriceCollector()
        self.pipeline_log: List[Dict] = []

        # Default watchlist of companies to monitor
        self.watchlist = [
            {"ticker": "LMT", "company": "Lockheed Martin"},
            {"ticker": "BA", "company": "Boeing"},
            {"ticker": "NOC", "company": "Northrop Grumman"},
            {"ticker": "GD", "company": "General Dynamics"},
            {"ticker": "RTX", "company": "RTX Corp"},
            {"ticker": "PFE", "company": "Pfizer"},
            {"ticker": "JNJ", "company": "Johnson & Johnson"},
            {"ticker": "UNH", "company": "UnitedHealth Group"},
            {"ticker": "AAPL", "company": "Apple"},
            {"ticker": "MSFT", "company": "Microsoft"},
            {"ticker": "GOOGL", "company": "Alphabet"},
            {"ticker": "AMZN", "company": "Amazon"},
            {"ticker": "TSLA", "company": "Tesla"},
            {"ticker": "JPM", "company": "JPMorgan Chase"},
            {"ticker": "XOM", "company": "Exxon Mobil"},
        ]

    def _log(self, stage: str, message: str, ticker: str = "", data: Optional[Dict] = None):
        """Log pipeline stage execution"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": stage,
            "message": message,
            "ticker": ticker,
            "data": data or {},
        }
        self.pipeline_log.append(entry)
        print(f"  [{stage}] {message}")

    def collect_foia_events(self, ticker: str, company: str) -> List[Dict]:
        """
        Stage 1: Collect FOIA events for a company

        Args:
            ticker: Stock ticker
            company: Company name

        Returns:
            List of tracked event IDs
        """
        self._log("COLLECT_FOIA", f"Fetching FOIA data for {company} ({ticker})", ticker)

        events = []

        # Get FOIA documents
        foia_docs = foia_engine.get_foia_documents_for_ticker(ticker, company, limit=20)

        for doc in foia_docs:
            # Analyze with NLP engine
            nlp_analysis = nlp_signal_engine.analyze_document(doc)

            # Track event with NLP signal data
            event_id = correlation_tracker.track_event(
                ticker=ticker,
                event_type="FOIA",
                event_title=doc.get("title", "FOIA Document"),
                event_date=datetime.fromisoformat(doc.get("date", datetime.utcnow().isoformat())[:19]) if doc.get("date") and "T" not in doc.get("date", "") else datetime.utcnow(),
                source=doc.get("source", "MuckRock"),
                url=doc.get("url", ""),
            )

            # Enrich event with NLP data
            for event in correlation_tracker.data["events"]:
                if event["event_id"] == event_id:
                    event["nlp_analysis"] = nlp_analysis
                    event["document"] = doc
                    correlation_tracker._save_data()
                    break

            events.append({
                "event_id": event_id,
                "nlp_signal": nlp_analysis,
                "document": doc,
            })

        self._log("COLLECT_FOIA", f"Tracked {len(events)} FOIA events for {ticker}", ticker,
                  {"count": len(events)})

        return events

    def collect_sec_events(self, ticker: str, company: str) -> List[Dict]:
        """
        Stage 1: Collect SEC filing events for a company

        Args:
            ticker: Stock ticker
            company: Company name

        Returns:
            List of tracked event IDs
        """
        self._log("COLLECT_SEC", f"Fetching SEC filings for {company} ({ticker})", ticker)

        events = []

        # Get SEC filings
        filings = sec_edgar_service.get_filings_for_ticker(ticker, limit=15)

        for filing in filings:
            # Analyze with NLP engine
            nlp_analysis = nlp_signal_engine.analyze_document({
                "title": filing.get("description", ""),
                "summary": f"{filing.get('form_type', '')} filing - {filing.get('description', '')}",
                "text": filing.get("description", ""),
            })

            # Track event
            event_id = correlation_tracker.track_event(
                ticker=ticker,
                event_type="SEC_FILING",
                event_title=f"{filing.get('form_type', 'SEC')} - {filing.get('description', '')[:100]}",
                event_date=datetime.fromisoformat(filing.get("filing_date", datetime.utcnow().isoformat())[:19]) if filing.get("filing_date") else datetime.utcnow(),
                source="SEC EDGAR",
                url=filing.get("filing_url", ""),
            )

            # Enrich event
            for event in correlation_tracker.data["events"]:
                if event["event_id"] == event_id:
                    event["nlp_analysis"] = nlp_analysis
                    event["filing"] = filing
                    event["signal"] = filing.get("signal", {})
                    correlation_tracker._save_data()
                    break

            events.append({
                "event_id": event_id,
                "nlp_signal": nlp_analysis,
                "filing": filing,
            })

        self._log("COLLECT_SEC", f"Tracked {len(events)} SEC events for {ticker}", ticker,
                  {"count": len(events)})

        return events

    def collect_contract_events(self, ticker: str, company: str) -> List[Dict]:
        """
        Stage 1: Collect contract events for a company

        Args:
            ticker: Stock ticker
            company: Company name

        Returns:
            List of tracked event IDs
        """
        self._log("COLLECT_CONTRACT", f"Fetching contract data for {company} ({ticker})", ticker)

        events = []

        # Get contract awards
        contracts = usaspending_service.get_contract_awards_for_ticker(
            ticker, company, limit=10
        )

        for contract in contracts:
            contract_amount = contract.get("Award Amount", 0) or 0
            description = contract.get("Description", "") or ""

            # Analyze with NLP engine
            nlp_analysis = nlp_signal_engine.analyze_document({
                "title": f"Federal Contract Award - ${contract_amount:,.0f}",
                "summary": description,
                "text": description,
            })

            # Track event
            event_date_str = contract.get("Start Date", contract.get("Last Modified Date", ""))
            try:
                event_date = datetime.fromisoformat(event_date_str[:19]) if event_date_str else datetime.utcnow()
            except:
                event_date = datetime.utcnow()

            event_id = correlation_tracker.track_event(
                ticker=ticker,
                event_type="FEDERAL_CONTRACT",
                event_title=f"Contract ${contract_amount:,.0f} - {description[:80]}",
                event_date=event_date,
                source="USAspending.gov",
                url="",
            )

            # Enrich event
            for event in correlation_tracker.data["events"]:
                if event["event_id"] == event_id:
                    event["nlp_analysis"] = nlp_analysis
                    event["contract"] = contract
                    event["signal"] = contract.get("signal", {})
                    event["Award Amount"] = contract_amount
                    correlation_tracker._save_data()
                    break

            events.append({
                "event_id": event_id,
                "nlp_signal": nlp_analysis,
                "contract": contract,
            })

        self._log("COLLECT_CONTRACT", f"Tracked {len(events)} contract events for {ticker}", ticker,
                  {"count": len(events)})

        return events

    def collect_regulatory_events(self, ticker: str, company: str) -> List[Dict]:
        """
        Stage 1: Collect regulatory events for a company

        Args:
            ticker: Stock ticker
            company: Company name

        Returns:
            List of tracked event IDs
        """
        self._log("COLLECT_REGULATORY", f"Fetching regulatory data for {company} ({ticker})", ticker)

        events = []

        # Get SEC filings via regulatory monitor
        sec_filings = regulatory_monitor.search_sec_filings(company, limit=5)
        for filing in sec_filings:
            nlp_analysis = nlp_signal_engine.analyze_document({
                "title": filing.get("title", ""),
                "summary": filing.get("description", ""),
                "text": filing.get("description", ""),
            })

            event_id = correlation_tracker.track_event(
                ticker=ticker,
                event_type="REGULATORY",
                event_title=filing.get("title", "SEC Filing"),
                event_date=datetime.utcnow(),
                source="SEC EDGAR",
                url=filing.get("url", ""),
            )

            for event in correlation_tracker.data["events"]:
                if event["event_id"] == event_id:
                    event["nlp_analysis"] = nlp_analysis
                    event["regulatory_filing"] = filing
                    correlation_tracker._save_data()
                    break

            events.append({
                "event_id": event_id,
                "nlp_signal": nlp_analysis,
            })

        self._log("COLLECT_REGULATORY", f"Tracked {len(events)} regulatory events for {ticker}", ticker,
                  {"count": len(events)})

        return events

    def collect_all_sources(self, ticker: str, company: str) -> Dict:
        """
        Collect events from ALL intelligence sources for a company

        Args:
            ticker: Stock ticker
            company: Company name

        Returns:
            Summary dict with all collected events
        """
        self._log("COLLECT_ALL", f"Starting full collection for {company} ({ticker})", ticker)

        foia_events = self.collect_foia_events(ticker, company)
        sec_events = self.collect_sec_events(ticker, company)
        contract_events = self.collect_contract_events(ticker, company)
        regulatory_events = self.collect_regulatory_events(ticker, company)

        total = len(foia_events) + len(sec_events) + len(contract_events) + len(regulatory_events)

        summary = {
            "ticker": ticker,
            "company": company,
            "foia_events": len(foia_events),
            "sec_events": len(sec_events),
            "contract_events": len(contract_events),
            "regulatory_events": len(regulatory_events),
            "total_events": total,
            "events": {
                "foia": foia_events,
                "sec": sec_events,
                "contract": contract_events,
                "regulatory": regulatory_events,
            }
        }

        self._log("COLLECT_ALL", f"Total: {total} events for {ticker}", ticker,
                  {"foia": len(foia_events), "sec": len(sec_events),
                   "contract": len(contract_events), "regulatory": len(regulatory_events)})

        return summary

    def update_prices(self) -> Dict:
        """
        Stage 2: Update stock prices for all tracked events

        Returns:
            Price collection summary
        """
        self._log("UPDATE_PRICES", "Collecting stock prices for all tracked events")

        summary = self.price_collector.collect_all_prices()

        self._log("UPDATE_PRICES", f"Price collection complete", data=summary)

        return summary

    def train_model(self) -> Dict:
        """
        Stage 3: Train/retrain ML model on accumulated data

        Returns:
            Training metrics
        """
        self._log("TRAIN_MODEL", "Starting model training")

        # Reload correlation data
        correlation_data = self.price_collector.data

        events_with_prices = len([
            e for e in correlation_data.get("events", [])
            if e.get("return_7d") is not None
        ])

        self._log("TRAIN_MODEL", f"Found {events_with_prices} events with 7-day price data")

        if events_with_prices < 20:
            self._log("TRAIN_MODEL",
                      f"Insufficient data: {events_with_prices}/20 events with prices. "
                      f"Need more tracked events with mature price data.")
            return {
                "status": "insufficient_data",
                "events_with_prices": events_with_prices,
                "required": 20,
                "message": f"Need {20 - events_with_prices} more events with 7-day price data",
            }

        metrics = gov_event_predictor.train_model(correlation_data)

        self._log("TRAIN_MODEL", f"Model trained: {metrics.get('test_accuracy', 'N/A')} test accuracy",
                  data=metrics)

        return metrics

    def generate_predictions(self, ticker: str) -> List[Dict]:
        """
        Stage 4: Generate predictions for recent events

        Args:
            ticker: Stock ticker

        Returns:
            List of predictions
        """
        self._log("PREDICT", f"Generating predictions for {ticker}")

        # Get recent events for ticker
        events = correlation_tracker.get_events_for_ticker(ticker, limit=10)

        predictions = []
        for event in events:
            event_type = event.get("event_type", "UNKNOWN")
            event_title = event.get("event_title", "")

            # Extract signal score from NLP analysis if available
            nlp_analysis = event.get("nlp_analysis", {})
            signal_score = nlp_analysis.get("signal_score", 50)

            # Extract contract amount if available
            contract_amount = event.get("Award Amount", 0) or 0

            prediction = gov_event_predictor.predict_for_ticker(
                ticker=ticker,
                event_type=event_type,
                signal_score=signal_score,
                contract_amount=contract_amount,
            )

            predictions.append({
                **prediction,
                "event_id": event.get("event_id"),
                "event_title": event_title,
                "event_type": event_type,
                "event_date": event.get("event_date"),
                "nlp_signal_score": signal_score,
            })

        self._log("PREDICT", f"Generated {len(predictions)} predictions for {ticker}")

        return predictions

    def run_full_pipeline(self, watchlist: Optional[List[Dict]] = None) -> Dict:
        """
        Run the complete intelligence pipeline

        Args:
            watchlist: List of {"ticker": ..., "company": ...} dicts

        Returns:
            Full pipeline results
        """
        start_time = datetime.utcnow()
        self._log("PIPELINE", "=" * 60)
        self._log("PIPELINE", "Starting full intelligence pipeline run")

        companies = watchlist or self.watchlist

        # Stage 1: Collect from all sources
        collection_results = {}
        total_events = 0

        for item in companies:
            ticker = item["ticker"]
            company = item["company"]

            try:
                result = self.collect_all_sources(ticker, company)
                collection_results[ticker] = result
                total_events += result["total_events"]

                # Rate limiting - be respectful to APIs
                time.sleep(1)

            except Exception as e:
                self._log("PIPELINE", f"Error collecting {ticker}: {e}", ticker)
                collection_results[ticker] = {"error": str(e), "total_events": 0}

        self._log("PIPELINE", f"Collection complete: {total_events} total events")

        # Stage 2: Update prices
        price_summary = self.update_prices()

        # Stage 3: Train model (if enough data)
        training_metrics = self.train_model()

        # Stage 4: Generate predictions for each company
        all_predictions = {}
        for item in companies:
            ticker = item["ticker"]
            try:
                predictions = self.generate_predictions(ticker)
                all_predictions[ticker] = predictions
                time.sleep(0.5)
            except Exception as e:
                self._log("PIPELINE", f"Error predicting {ticker}: {e}", ticker)
                all_predictions[ticker] = {"error": str(e)}

        # Stage 5: Get correlation accuracy
        accuracy = correlation_tracker.get_accuracy_statistics()

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        results = {
            "pipeline_run_id": datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            "status": "completed",
            "elapsed_seconds": elapsed,
            "collection": {
                "companies_processed": len(companies),
                "total_events_collected": total_events,
                "results": collection_results,
            },
            "price_collection": price_summary,
            "training": training_metrics,
            "predictions": all_predictions,
            "accuracy": accuracy,
            "pipeline_log": self.pipeline_log[-50:],  # Last 50 log entries
        }

        # Save pipeline results
        output_path = self.data_dir / "pipeline_results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        self._log("PIPELINE", f"Pipeline complete in {elapsed:.1f}s. Results saved to {output_path}")

        return results

    def run_single_company(self, ticker: str, company: str) -> Dict:
        """
        Run pipeline for a single company

        Args:
            ticker: Stock ticker
            company: Company name

        Returns:
            Pipeline results for this company
        """
        self._log("SINGLE", f"Running pipeline for {company} ({ticker})")

        # Collect
        collection = self.collect_all_sources(ticker, company)

        # Update prices
        price_summary = self.update_prices()

        # Train if enough data
        training_metrics = self.train_model()

        # Predict
        predictions = self.generate_predictions(ticker)

        # Accuracy
        accuracy = correlation_tracker.get_accuracy_statistics()

        return {
            "ticker": ticker,
            "company": company,
            "collection": collection,
            "price_collection": price_summary,
            "training": training_metrics,
            "predictions": predictions,
            "accuracy": accuracy,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Initialize global pipeline
intelligence_pipeline = IntelligencePipeline()


if __name__ == "__main__":
    print("🔄 Automated Intelligence Pipeline")
    print("=" * 60)

    # Run for a single company as demo
    print("\n📋 Running pipeline for Lockheed Martin (LMT)...")
    result = intelligence_pipeline.run_single_company("LMT", "Lockheed Martin")

    print(f"\n📊 Pipeline Results:")
    print(f"   Events collected: {result['collection']['total_events']}")
    print(f"   Price data: {result['price_collection']}")
    print(f"   Training: {result['training'].get('status', 'N/A')}")
    print(f"   Predictions: {len(result['predictions']) if isinstance(result['predictions'], list) else 'N/A'}")
    print(f"   Accuracy: {result['accuracy']}")
