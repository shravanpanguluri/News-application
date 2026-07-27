#!/usr/bin/env python3
"""
CONTINUOUS DATA COLLECTION SYSTEM
Runs hourly to accumulate real training data for ML model.

What it does:
1. Tracks new government events (contracts, SEC, FDA, FOIA)
2. Collects stock price data at 1/7/30 day intervals
3. Retrains ML model weekly when enough new data
4. Monitors accuracy improvement over time

How to run:
- Manual: python continuous_data_collector.py
- Hourly: Add to crontab: 0 * * * * cd /path/to/backend && python continuous_data_collector.py
- Windows: Use Task Scheduler to run hourly
"""
import yfinance as yf
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import time
import sys

# Company watchlist (start with 15, expand as needed)
WATCHLIST = [
    # Defense
    {"ticker": "LMT", "name": "LOCKHEED MARTIN", "sector": "Defense"},
    {"ticker": "BA", "name": "BOEING", "sector": "Defense"},
    {"ticker": "NOC", "name": "NORTHROP GRUMMAN", "sector": "Defense"},
    {"ticker": "GD", "name": "GENERAL DYNAMICS", "sector": "Defense"},
    {"ticker": "RTX", "name": "RAYTHEON", "sector": "Defense"},
    
    # Healthcare
    {"ticker": "PFE", "name": "PFIZER", "sector": "Healthcare"},
    {"ticker": "JNJ", "name": "JOHNSON & JOHNSON", "sector": "Healthcare"},
    {"ticker": "MRK", "name": "MERCK", "sector": "Healthcare"},
    {"ticker": "UNH", "name": "UNITEDHEALTH", "sector": "Healthcare"},
    
    # Technology
    {"ticker": "AAPL", "name": "APPLE", "sector": "Technology"},
    {"ticker": "MSFT", "name": "MICROSOFT", "sector": "Technology"},
    {"ticker": "GOOGL", "name": "ALPHABET", "sector": "Technology"},
    
    # Finance
    {"ticker": "JPM", "name": "JPMORGAN", "sector": "Finance"},
    {"ticker": "BAC", "name": "BANK OF AMERICA", "sector": "Finance"},
    
    # Energy
    {"ticker": "XOM", "name": "EXXON MOBIL", "sector": "Energy"},
]


class ContinuousDataCollector:
    """
    Runs hourly to collect real government events and stock prices.
    Designed for long-term data accumulation (weeks/months).
    """

    def __init__(self):
        self.correlation_path = Path("correlation_data.json")
        self.data = self._load_data()
        self.events = self.data.get("events", [])
        self.stats_path = Path("collection_stats.json")
        self.stats = self._load_stats()

    def _load_data(self) -> Dict:
        if self.correlation_path.exists():
            with open(self.correlation_path, "r") as f:
                return json.load(f)
        return {"events": [], "correlations": {}, "accuracy_stats": {}}

    def _save_data(self):
        self.data["events"] = self.events
        with open(self.correlation_path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def _load_stats(self) -> Dict:
        if self.stats_path.exists():
            with open(self.stats_path, "r") as f:
                return json.load(f)
        return {
            "collection_runs": 0,
            "last_collection": None,
            "events_added_total": 0,
            "model_retrains": 0,
            "accuracy_history": []
        }

    def _save_stats(self):
        with open(self.stats_path, "w") as f:
            json.dump(self.stats, f, indent=2, default=str)

    def get_stock_price_data(self, ticker: str, date: datetime) -> Optional[Dict]:
        """Get stock price and forward returns"""
        try:
            stock = yf.Ticker(ticker)
            start_date = (date - timedelta(days=5)).strftime("%Y-%m-%d")
            end_date = (date + timedelta(days=40)).strftime("%Y-%m-%d")
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 35:
                return None
            
            price_0 = hist['Close'].iloc[0]
            returns = {"price_0d": float(price_0)}
            
            for days in [1, 7, 30]:
                if days < len(hist):
                    price_future = hist['Close'].iloc[days]
                    return_pct = ((price_future - price_0) / price_0) * 100
                    returns[f"price_{days}d"] = float(price_future)
                    returns[f"return_{days}d"] = round(float(return_pct), 2)
            
            return returns if "return_7d" in returns else None
            
        except Exception as e:
            print(f"  ✗ Price error for {ticker}: {e}")
            return None

    def collect_contracts(self):
        """Collect new federal contracts"""
        print("\n🏛️ Collecting federal contracts...")
        
        try:
            from services.usaspending_service import usaspending_service
        except ImportError:
            print("  ⚠️ USAspending service not available")
            return 0
        
        new_events = 0
        
        for company in WATCHLIST[:10]:  # Top 10 for speed
            ticker = company["ticker"]
            name = company["name"]
            
            try:
                contracts = usaspending_service.get_contract_awards_for_ticker(
                    ticker, name, limit=5
                )
                
                for contract in contracts[:3]:  # Top 3 per company
                    date_str = contract.get("date", contract.get("Start Date", ""))
                    if not date_str:
                        continue
                    
                    try:
                        if "T" in date_str:
                            event_date = datetime.fromisoformat(date_str.split("T")[0])
                        else:
                            event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    except:
                        continue
                    
                    # Skip if older than 7 days (no price data available)
                    if (datetime.utcnow() - event_date).days < 7:
                        continue
                    
                    event_id = f"{ticker}_CONTRACT_{contract.get('Award ID', '')}"
                    if any(e.get("event_id") == event_id for e in self.events):
                        continue
                    
                    # Get price data
                    price_data = self.get_stock_price_data(ticker, event_date)
                    if not price_data or "return_7d" not in price_data:
                        continue
                    
                    amount = contract.get("Award Amount", 0) or 0
                    signal_score = 90 if amount > 100_000_000 else \
                                  75 if amount > 50_000_000 else \
                                  60 if amount > 10_000_000 else 40
                    
                    event = {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_type": "contract",
                        "event_title": f"Federal contract: {contract.get('Award ID', 'Unknown')}",
                        "event_date": event_date.isoformat(),
                        "source": "USAspending.gov",
                        "url": "",
                        "tracked_at": datetime.utcnow().isoformat(),
                        **price_data,
                        "signal": {"signal_score": signal_score},
                        "Award Amount": amount,
                    }
                    
                    self.events.append(event)
                    new_events += 1
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  ✗ Error for {ticker}: {e}")
        
        print(f"  ✓ Added {new_events} contract events")
        return new_events

    def collect_sec_filings(self):
        """Collect new SEC filings"""
        print("\n📋 Collecting SEC filings...")
        
        try:
            from services.regulatory_monitor import regulatory_monitor
        except ImportError:
            print("  ⚠️ Regulatory monitor not available")
            return 0
        
        new_events = 0
        
        for company in WATCHLIST[:10]:
            ticker = company["ticker"]
            name = company["name"]
            
            try:
                filings = regulatory_monitor.search_sec_filings(name, limit=5)
                
                for filing in filings[:3]:
                    filing_date = filing.get("filed_at", filing.get("date", ""))
                    if not filing_date:
                        continue
                    
                    try:
                        if isinstance(filing_date, (int, float)):
                            event_date = datetime.fromtimestamp(filing_date / 1000)
                        elif "T" in str(filing_date):
                            event_date = datetime.fromisoformat(str(filing_date).split("T")[0])
                        else:
                            event_date = datetime.strptime(str(filing_date)[:10], "%Y-%m-%d")
                    except:
                        continue
                    
                    if (datetime.utcnow() - event_date).days < 7:
                        continue
                    
                    event_id = f"{ticker}_SEC_{filing.get('id', filing.get('title', ''))}"
                    if any(e.get("event_id") == event_id for e in self.events):
                        continue
                    
                    price_data = self.get_stock_price_data(ticker, event_date)
                    if not price_data or "return_7d" not in price_data:
                        continue
                    
                    event = {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_type": "sec_filing",
                        "event_title": f"SEC filing: {filing.get('title', 'Unknown')}",
                        "event_date": event_date.isoformat(),
                        "source": "SEC EDGAR",
                        "url": "",
                        "tracked_at": datetime.utcnow().isoformat(),
                        **price_data,
                        "signal": {"signal_score": 50},
                        "Award Amount": 0,
                    }
                    
                    self.events.append(event)
                    new_events += 1
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  ✗ Error for {ticker}: {e}")
        
        print(f"  ✓ Added {new_events} SEC filing events")
        return new_events

    def update_existing_events(self):
        """Update price data for existing events at 7/30 day marks"""
        print("\n💰 Updating price data for existing events...")
        
        updated = 0
        
        for event in self.events:
            if event.get("return_30d") is not None:
                continue  # Already has all price data
            
            ticker = event.get("ticker", "")
            event_date_str = event.get("event_date", "")
            
            if not ticker or not event_date_str:
                continue
            
            try:
                if "T" in event_date_str:
                    event_date = datetime.fromisoformat(event_date_str.split("T")[0])
                else:
                    event_date = datetime.strptime(event_date_str[:10], "%Y-%m-%d")
            except:
                continue
            
            # Check if 30 days have passed
            days_since = (datetime.utcnow() - event_date).days
            
            if days_since >= 30 and event.get("return_7d") is None:
                # Get all price data
                price_data = self.get_stock_price_data(ticker, event_date)
                if price_data:
                    event.update(price_data)
                    updated += 1
            elif days_since >= 7 and event.get("return_7d") is None:
                # Get 7-day price
                price_data = self.get_stock_price_data(ticker, event_date)
                if price_data and "return_7d" in price_data:
                    event["price_7d"] = price_data.get("price_7d")
                    event["return_7d"] = price_data.get("return_7d")
                    updated += 1
        
        print(f"  ✓ Updated {updated} events with new price data")
        return updated

    def retrain_model_if_needed(self):
        """Retrain model if we have enough new REAL data"""
        # Filter to only REAL events (not synthetic)
        real_events = [e for e in self.events if e.get("source") != "Synthetic-Enhanced"]
        events_with_prices = len([e for e in real_events if e.get("return_7d") is not None])
        
        # Retrain if we have 50+ REAL events with prices
        if events_with_prices >= 50:
            print(f"\n🤖 Retraining ML model with {events_with_prices} REAL events...")
            
            try:
                from services.gov_event_predictor import GovernmentEventPredictor
                
                # Create temp data with only real events
                real_data = {**self.data, "events": real_events}
                
                predictor = GovernmentEventPredictor()
                metrics = predictor.train_model(real_data)
                
                if metrics.get("status") == "trained":
                    self.stats["model_retrains"] += 1
                    self.stats["accuracy_history"].append({
                        "date": datetime.utcnow().isoformat(),
                        "train_accuracy": metrics.get("train_accuracy"),
                        "test_accuracy": metrics.get("test_accuracy"),
                        "training_samples": events_with_prices
                    })
                    
                    print(f"  ✓ Model retrained: {metrics.get('test_accuracy'):.1%} test accuracy")
                    return metrics
                else:
                    print(f"  ⚠️ Training failed: {metrics.get('message')}")
                    return None
                    
            except Exception as e:
                print(f"  ✗ Error retraining: {e}")
                return None
        else:
            print(f"\n🤖 Model retrain skipped (only {events_with_prices}/50 REAL events with prices)")
            return None

    def run_collection_cycle(self):
        """Run one complete collection cycle"""
        print("\n" + "="*70)
        print("  CONTINUOUS DATA COLLECTION CYCLE")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        results = {}
        
        # Collect new events
        results["contracts"] = self.collect_contracts()
        results["sec_filings"] = self.collect_sec_filings()
        results["price_updates"] = self.update_existing_events()
        
        # Save data
        self._save_data()
        
        # Update stats
        self.stats["collection_runs"] += 1
        self.stats["last_collection"] = datetime.utcnow().isoformat()
        self.stats["events_added_total"] += results["contracts"] + results["sec_filings"]
        
        # Retrain if needed
        retrain_result = self.retrain_model_if_needed()
        
        # Save stats
        self._save_stats()
        
        # Summary
        total_events = len(self.events)
        events_with_prices = len([e for e in self.events if e.get("return_7d") is not None])
        
        print("\n" + "="*70)
        print("  COLLECTION CYCLE COMPLETE")
        print("="*70)
        print(f"  New contracts: {results['contracts']}")
        print(f"  New SEC filings: {results['sec_filings']}")
        print(f"  Price updates: {results['price_updates']}")
        print(f"  ─────────────────────────────────")
        print(f"  Total events: {total_events}")
        print(f"  Events with 7-day prices: {events_with_prices}")
        print(f"  Collection runs: {self.stats['collection_runs']}")
        print(f"  Model retrains: {self.stats['model_retrains']}")
        print("="*70)
        
        return {
            **results,
            "total_events": total_events,
            "events_with_prices": events_with_prices,
            "model_retrained": retrain_result is not None
        }


def main():
    """Main entry point"""
    collector = ContinuousDataCollector()
    summary = collector.run_collection_cycle()
    
    print(f"\n✅ Collection cycle complete!")
    print(f"   Total events: {summary['total_events']}")
    print(f"   With price data: {summary['events_with_prices']}")
    
    if summary['model_retrained']:
        print(f"   🎉 Model retrained with new data!")


if __name__ == "__main__":
    main()
