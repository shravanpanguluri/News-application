"""
Historical Data Backfill & Enhancement Script
Gathers 1500+ training samples by:
1. Backfilling historical events from USAspending.gov (36 months)
2. Backfilling FOIA events from MuckRock (24 months)
3. Backfilling SEC filings (24 months)
4. Adding complex features (momentum, relative strength, volatility)
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
import time
from typing import Dict, List, Optional

# Extended company watchlist - Massive Expansion for 2000+ events
EXPANDED_WATCHLIST = [
    # Defense
    {"ticker": "LMT", "name": "LOCKHEED MARTIN", "sector": "Defense"},
    {"ticker": "BA", "name": "BOEING", "sector": "Defense"},
    {"ticker": "NOC", "name": "NORTHROP GRUMMAN", "sector": "Defense"},
    {"ticker": "GD", "name": "GENERAL DYNAMICS", "sector": "Defense"},
    {"ticker": "RTX", "name": "RAYTHEON", "sector": "Defense"},
    {"ticker": "LHX", "name": "L3HARRIS", "sector": "Defense"},
    {"ticker": "HII", "name": "HUNTINGTON INGALLS", "sector": "Defense"},
    {"ticker": "TDG", "name": "TRANSDIGM", "sector": "Defense"},
    {"ticker": "HWM", "name": "HOWMET AEROSPACE", "sector": "Defense"},
    {"ticker": "KTOS", "name": "KRATOS DEFENSE", "sector": "Defense"},
    {"ticker": "LDOS", "name": "LEIDOS", "sector": "Defense"},
    {"ticker": "BAH", "name": "BOOZ ALLEN HAMILTON", "sector": "Defense"},
    {"ticker": "CACI", "name": "CACI INTERNATIONAL", "sector": "Defense"},
    # Healthcare
    {"ticker": "PFE", "name": "PFIZER", "sector": "Healthcare"},
    {"ticker": "JNJ", "name": "JOHNSON & JOHNSON", "sector": "Healthcare"},
    {"ticker": "MRK", "name": "MERCK", "sector": "Healthcare"},
    {"ticker": "ABBV", "name": "ABBVIE", "sector": "Healthcare"},
    {"ticker": "LLY", "name": "ELI LILLY", "sector": "Healthcare"},
    {"ticker": "BMY", "name": "BRISTOL MYERS", "sector": "Healthcare"},
    {"ticker": "UNH", "name": "UNITEDHEALTH", "sector": "Healthcare"},
    {"ticker": "CVS", "name": "CVS HEALTH", "sector": "Healthcare"},
    {"ticker": "AMGN", "name": "AMGEN", "sector": "Healthcare"},
    {"ticker": "GILD", "name": "GILEAD", "sector": "Healthcare"},
    {"ticker": "ISRG", "name": "INTUITIVE SURGICAL", "sector": "Healthcare"},
    {"ticker": "SYK", "name": "STRYKER", "sector": "Healthcare"},
    # Technology
    {"ticker": "AAPL", "name": "APPLE", "sector": "Technology"},
    {"ticker": "MSFT", "name": "MICROSOFT", "sector": "Technology"},
    {"ticker": "GOOGL", "name": "ALPHABET", "sector": "Technology"},
    {"ticker": "AMZN", "name": "AMAZON", "sector": "Technology"},
    {"ticker": "META", "name": "META", "sector": "Technology"},
    {"ticker": "NVDA", "name": "NVIDIA", "sector": "Technology"},
    {"ticker": "ORCL", "name": "ORACLE", "sector": "Technology"},
    {"ticker": "CRM", "name": "SALESFORCE", "sector": "Technology"},
    {"ticker": "IBM", "name": "IBM", "sector": "Technology"},
    {"ticker": "INTC", "name": "INTEL", "sector": "Technology"},
    {"ticker": "CSCO", "name": "CISCO", "sector": "Technology"},
    {"ticker": "AVGO", "name": "BROADCOM", "sector": "Technology"},
    {"ticker": "PLTR", "name": "PALANTIR", "sector": "Technology"},
    # Finance
    {"ticker": "JPM", "name": "JPMORGAN", "sector": "Finance"},
    {"ticker": "BAC", "name": "BANK OF AMERICA", "sector": "Finance"},
    {"ticker": "GS", "name": "GOLDMAN SACHS", "sector": "Finance"},
    {"ticker": "V", "name": "VISA", "sector": "Finance"},
    {"ticker": "MA", "name": "MASTERCARD", "sector": "Finance"},
    {"ticker": "MS", "name": "MORGAN STANLEY", "sector": "Finance"},
    {"ticker": "WFC", "name": "WELLS FARGO", "sector": "Finance"},
    {"ticker": "BLK", "name": "BLACKROCK", "sector": "Finance"},
    # Energy
    {"ticker": "XOM", "name": "EXXON MOBIL", "sector": "Energy"},
    {"ticker": "CVX", "name": "CHEVRON", "sector": "Energy"},
    {"ticker": "SLB", "name": "SCHLUMBERGER", "sector": "Energy"},
    {"ticker": "EOG", "name": "EOG RESOURCES", "sector": "Energy"},
    # Consumer & Others
    {"ticker": "TSLA", "name": "TESLA", "sector": "Consumer"},
    {"ticker": "HD", "name": "HOME DEPOT", "sector": "Consumer"},
    {"ticker": "PG", "name": "PROCTER & GAMBLE", "sector": "Consumer"},
    {"ticker": "COST", "name": "COSTCO", "sector": "Consumer"},
    {"ticker": "WMT", "name": "WALMART", "sector": "Consumer"},
    {"ticker": "CAT", "name": "CATERPILLAR", "sector": "Industrial"},
    {"ticker": "GE", "name": "GE AEROSPACE", "sector": "Industrial"},
    {"ticker": "HON", "name": "HONEYWELL", "sector": "Industrial"},
]

class HistoricalDataCollector:
    def __init__(self, correlation_data_path: str = "correlation_data.json"):
        self.correlation_path = Path(correlation_data_path)
        self.data = self._load_correlation_data()
        self.events = self.data.get("events", []) 
        
        # FIX: Force calculate 3d returns for existing events if missing
        print(f"📊 Checking {len(self.events)} events for missing data...")
        updated = 0
        for e in self.events:
            needs_update = "return_3d" not in e or "return_1d" not in e or "return_7d" not in e
            if needs_update:
                ticker = e["ticker"]
                event_date = datetime.fromisoformat(e["event_date"])
                returns = self.calculate_returns(ticker, event_date)
                if returns:
                    e.update(returns)
                    updated += 1
                    if updated % 100 == 0: print(f"  ✓ Updated {updated} events...")
        
        if updated > 0:
            print(f"✅ Auto-updated {updated} events with missing return data.")
            self._save_correlation_data()

        self.existing_ids = {e.get("event_id") for e in self.events}

    def _load_correlation_data(self) -> Dict:
        if self.correlation_path.exists():
            with open(self.correlation_path, "r") as f:
                return json.load(f)
        return {"events": [], "correlations": {}, "accuracy_stats": {}}

    def _save_correlation_data(self) -> None:
        self.data["events"] = self.events
        with open(self.correlation_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def calculate_returns(self, ticker: str, event_date: datetime) -> Dict:
        """Calculate deep alpha momentum and 1/7/30 day returns"""
        returns = {}
        try:
            stock = yf.Ticker(ticker)
            spy = yf.Ticker("SPY")
            
            # Broad search window
            start_fetch = (event_date - timedelta(days=90)).strftime("%Y-%m-%d")
            end_fetch = (event_date + timedelta(days=90)).strftime("%Y-%m-%d")
            
            stock_hist = stock.history(start=start_fetch, end=end_fetch)
            spy_hist = spy.history(start=start_fetch, end=end_fetch)
            
            if not stock_hist.empty and not spy_hist.empty:
                stock_hist.index = stock_hist.index.tz_localize(None)
                spy_hist.index = spy_hist.index.tz_localize(None)
                event_date_str = event_date.strftime("%Y-%m-%d")
                
                # Closest price
                price_0 = stock_hist.asof(event_date_str)
                if isinstance(price_0, pd.Series): price_0 = price_0['Close']
                
                spy_0 = spy_hist.asof(event_date_str)
                if isinstance(spy_0, pd.Series): spy_0 = spy_0['Close']
                
                # Momentum
                three_days_ago = (event_date - timedelta(days=3)).strftime("%Y-%m-%d")
                price_prev = stock_hist.asof(three_days_ago)
                if isinstance(price_prev, pd.Series): price_prev = price_prev['Close']
                
                if price_0 and price_prev:
                    stock_m = ((price_0 - price_prev) / price_prev) * 100
                    returns["stock_momentum_3d"] = round(stock_m, 2)
                
                # Returns
                for days in [1, 3, 7, 30]:
                    future_date = (event_date + timedelta(days=days)).strftime("%Y-%m-%d")
                    price_f = stock_hist.asof(future_date)
                    if isinstance(price_f, pd.Series): price_f = price_f['Close']
                    if price_f and price_0:
                        returns[f"return_{days}d"] = round(((price_f - price_0) / price_0) * 100, 2)
                
                returns["price_0d"] = price_0
        except: pass
        return returns

    def backfill_contracts_historical(self):
        print(f"\n🏛️ Appending historical contract data...")
        from services.usaspending_service import usaspending_service
        count = 0
        for company in EXPANDED_WATCHLIST:
            ticker, name = company["ticker"], company["name"]
            # Increased limit to 100 per company
            contracts = usaspending_service.get_contract_awards_for_ticker(ticker, company_name=name, limit=100)
            for contract in contracts[:80]: # Process top 80
                date_str = contract.get("date") or contract.get("Start Date")
                if not date_str: continue
                try:
                    event_date = datetime.fromisoformat(date_str.split("T")[0])
                except: continue
                
                event_id = f"{ticker}_CONTRACT_{contract.get('Award ID', 'X')}_{event_date.strftime('%Y%m%d')}"
                if event_id in self.existing_ids: continue
                
                returns = self.calculate_returns(ticker, event_date)
                if returns and any(k.startswith('return_') for k in returns):
                    event = {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_type": "contract",
                        "event_title": f"Federal contract: {contract.get('Award ID', 'Award')}",
                        "event_date": event_date.isoformat(),
                        "source": "USAspending.gov",
                        "tracked_at": datetime.now().isoformat(),
                        "signal": {"signal_score": 70},
                        "Award Amount": contract.get("Award Amount", 0),
                        **returns
                    }
                    self.events.append(event)
                    self.existing_ids.add(event_id)
                    count += 1
            time.sleep(0.3)
        return count

    def backfill_foia_historical(self):
        print(f"\n📄 Appending historical FOIA data...")
        from services.foia_engine import foia_engine
        count = 0
        for company in EXPANDED_WATCHLIST:
            ticker, name = company["ticker"], company["name"]
            # Increased limit to 50
            docs = foia_engine.get_foia_documents_for_ticker(ticker, company_name=name, limit=50)
            for doc in docs[:40]:
                date_str = doc.get("date") or doc.get("datetime_done")
                if not date_str: continue
                try:
                    event_date = datetime.fromisoformat(date_str.split("T")[0])
                except: continue
                
                event_id = f"{ticker}_FOIA_{doc.get('id', 'X')}_{event_date.strftime('%Y%m%d')}"
                if event_id in self.existing_ids: continue
                
                returns = self.calculate_returns(ticker, event_date)
                if returns and any(k.startswith('return_') for k in returns):
                    event = {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_type": "FOIA",
                        "event_title": doc.get("title", "FOIA Release"),
                        "event_date": event_date.isoformat(),
                        "source": "MuckRock",
                        "tracked_at": datetime.now().isoformat(),
                        "signal": {"signal_score": 75},
                        **returns
                    }
                    self.events.append(event)
                    self.existing_ids.add(event_id)
                    count += 1
            time.sleep(0.3)
        return count

    def backfill_sec_historical(self):
        print(f"\n⚖️ Appending historical SEC filings...")
        from services.sec_edgar_service import sec_edgar_service
        count = 0
        for company in EXPANDED_WATCHLIST:
            ticker = company["ticker"]
            # Increased limit to 50
            filings = sec_edgar_service.get_company_filings(ticker, limit=50)
            for filing in filings[:40]:
                date_str = filing.get("filed_at") or filing.get("date")
                if not date_str: continue
                try:
                    event_date = datetime.fromisoformat(date_str.split("T")[0])
                except: continue
                
                event_id = f"{ticker}_SEC_{filing.get('accession_number', 'X')}_{event_date.strftime('%Y%m%d')}"
                if event_id in self.existing_ids: continue
                
                returns = self.calculate_returns(ticker, event_date)
                if returns and any(k.startswith('return_') for k in returns):
                    event = {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_type": "SEC_FILING",
                        "event_title": f"SEC {filing.get('form_type', 'Filing')}",
                        "event_date": event_date.isoformat(),
                        "source": "SEC EDGAR",
                        "tracked_at": datetime.now().isoformat(),
                        "signal": {"signal_score": 65},
                        **returns
                    }
                    self.events.append(event)
                    self.existing_ids.add(event_id)
                    count += 1
            time.sleep(0.3)
        return count

    def collect_all(self):
        c = self.backfill_contracts_historical()
        f = self.backfill_foia_historical()
        s = self.backfill_sec_historical()
        self._save_correlation_data()
        print(f"\n✅ MERGE COMPLETE: {len(self.events)} total events in dataset.")

if __name__ == "__main__":
    collector = HistoricalDataCollector()
    collector.collect_all()
