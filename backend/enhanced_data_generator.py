"""
Enhanced Training Data Generator
Creates 300+ realistic training samples by:
1. Using real events we already have (62 events)
2. Generating synthetic events based on real patterns
3. Adding complex features
4. Using real stock price data for returns
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Dict, List
import random

# Company watchlist with sectors
COMPANIES = [
    {"ticker": "LMT", "name": "LOCKHEED MARTIN", "sector": "Defense", "gov_sensitivity": 0.95},
    {"ticker": "BA", "name": "BOEING", "sector": "Defense", "gov_sensitivity": 0.90},
    {"ticker": "NOC", "name": "NORTHROP GRUMMAN", "sector": "Defense", "gov_sensitivity": 0.92},
    {"ticker": "GD", "name": "GENERAL DYNAMICS", "sector": "Defense", "gov_sensitivity": 0.88},
    {"ticker": "RTX", "name": "RAYTHEON", "sector": "Defense", "gov_sensitivity": 0.85},
    {"ticker": "PFE", "name": "PFIZER", "sector": "Healthcare", "gov_sensitivity": 0.75},
    {"ticker": "JNJ", "name": "JOHNSON & JOHNSON", "sector": "Healthcare", "gov_sensitivity": 0.70},
    {"ticker": "MRK", "name": "MERCK", "sector": "Healthcare", "gov_sensitivity": 0.68},
    {"ticker": "AAPL", "name": "APPLE", "sector": "Technology", "gov_sensitivity": 0.45},
    {"ticker": "MSFT", "name": "MICROSOFT", "sector": "Technology", "gov_sensitivity": 0.50},
    {"ticker": "GOOGL", "name": "ALPHABET", "sector": "Technology", "gov_sensitivity": 0.48},
    {"ticker": "TSLA", "name": "TESLA", "sector": "Consumer", "gov_sensitivity": 0.35},
    {"ticker": "XOM", "name": "EXXON MOBIL", "sector": "Energy", "gov_sensitivity": 0.55},
    {"ticker": "JPM", "name": "JPMORGAN", "sector": "Finance", "gov_sensitivity": 0.60},
    {"ticker": "BAC", "name": "BANK OF AMERICA", "sector": "Finance", "gov_sensitivity": 0.58},
]

EVENT_TYPES = ["contract", "foia", "sec_filing", "regulatory"]

class EnhancedDataGenerator:
    """
    Generates enhanced training data with:
    - Real stock price movements
    - Complex temporal features
    - Cross-event correlations
    - Realistic feature distributions
    """

    def __init__(self):
        self.correlation_path = Path("correlation_data.json")
        self.data = self._load_data()
        self.real_events = self.data.get("events", [])

    def _load_data(self) -> Dict:
        if self.correlation_path.exists():
            with open(self.correlation_path, "r") as f:
                return json.load(f)
        return {"events": [], "correlations": {}, "accuracy_stats": {}}

    def get_real_price_data(self, ticker: str, date: datetime) -> Dict:
        """Get real stock price and calculate returns"""
        try:
            stock = yf.Ticker(ticker)
            start_date = (date - timedelta(days=40)).strftime("%Y-%m-%d")
            end_date = (date + timedelta(days=40)).strftime("%Y-%m-%d")
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 35:
                return None
            
            # Simple approach: just get the first price and calculate forward returns
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
            return None

    def generate_synthetic_events(self, target_count: int = 300) -> List[Dict]:
        """Generate realistic synthetic events based on real patterns"""
        print(f"\n🎯 Generating {target_count} synthetic events with real price data...")
        print("="*70)
        
        synthetic_events = []
        event_id_counter = len(self.real_events)
        
        # Generate events for each company
        events_per_company = target_count // len(COMPANIES)
        
        for company in COMPANIES:
            ticker = company["ticker"]
            sector = company["sector"]
            gov_sensitivity = company["gov_sensitivity"]
            
            print(f"\n📄 Generating events for {ticker} ({sector})...")
            
            for i in range(events_per_company):
                # Random event date in past 6 months
                days_ago = random.randint(30, 180)  # Ensure 7-day returns available
                event_date = datetime.utcnow() - timedelta(days=days_ago)
                
                # Random event type (weighted by sector)
                if sector == "Defense":
                    event_type = random.choices(
                        ["contract", "foia", "sec_filing", "regulatory"],
                        weights=[0.6, 0.2, 0.1, 0.1]
                    )[0]
                elif sector == "Healthcare":
                    event_type = random.choices(
                        ["contract", "foia", "sec_filing", "regulatory"],
                        weights=[0.2, 0.3, 0.2, 0.3]
                    )[0]
                else:
                    event_type = random.choices(
                        ["contract", "foia", "sec_filing", "regulatory"],
                        weights=[0.3, 0.2, 0.3, 0.2]
                    )[0]
                
                # Get real price data
                price_data = self.get_real_price_data(ticker, event_date)
                
                if not price_data or "return_7d" not in price_data:
                    continue  # Skip if no price data
                
                # Generate realistic features
                contract_amount = 0
                signal_score = 50
                
                if event_type == "contract":
                    # Realistic contract amounts
                    contract_amount = random.choice([
                        random.uniform(1_000_000, 10_000_000),
                        random.uniform(10_000_000, 50_000_000),
                        random.uniform(50_000_000, 100_000_000),
                        random.uniform(100_000_000, 500_000_000),
                    ])
                    
                    # Signal score based on amount
                    if contract_amount > 100_000_000:
                        signal_score = random.randint(75, 95)
                    elif contract_amount > 50_000_000:
                        signal_score = random.randint(60, 80)
                    elif contract_amount > 10_000_000:
                        signal_score = random.randint(45, 65)
                    else:
                        signal_score = random.randint(20, 50)
                elif event_type == "foia":
                    signal_score = random.randint(30, 70)
                elif event_type == "sec_filing":
                    signal_score = random.randint(40, 75)
                else:  # regulatory
                    signal_score = random.randint(50, 85)
                
                # Create event with REAL price data and complex features
                event = {
                    "event_id": f"{ticker}_{event_type.upper()}_{event_id_counter}",
                    "ticker": ticker,
                    "event_type": event_type,
                    "event_title": f"{'Contract' if event_type == 'contract' else 'Event'} for {company['name']}",
                    "event_date": event_date.isoformat(),
                    "source": "Synthetic-Enhanced",
                    "url": "",
                    "tracked_at": datetime.utcnow().isoformat(),
                    
                    # Real price data
                    **price_data,
                    
                    # Real features
                    "signal": {"signal_score": signal_score},
                    "Award Amount": contract_amount,
                    
                    # Complex temporal features
                    "day_of_week": event_date.weekday(),
                    "month": event_date.month,
                    "quarter": (event_date.month - 1) // 3 + 1,
                    "is_month_end": 1 if event_date.day > 25 else 0,
                    
                    # Company features
                    "company_gov_sensitivity": gov_sensitivity,
                    "total_company_events": events_per_company,
                    "events_last_7d": random.randint(0, 3),
                    "events_last_30d": random.randint(1, 10),
                    
                    # Contract features
                    "contract_amount_normalized": min(contract_amount / 1_000_000_000, 1.0),
                    "days_since_last_event": random.randint(1, 60),
                    "total_gov_spending_30d": random.uniform(0, 0.5),
                    "avg_signal_score_30d": signal_score + random.uniform(-10, 10),
                }
                
                synthetic_events.append(event)
                event_id_counter += 1
                
                # Rate limiting for API calls
                if i % 5 == 0:
                    time.sleep(0.2)
        
        print(f"\n✓ Generated {len(synthetic_events)} synthetic events with real price data")
        return synthetic_events

    def combine_and_save(self):
        """Combine real and synthetic events, save for training"""
        print("\n" + "="*70)
        print("  COMBINING REAL + SYNTHETIC DATA")
        print("="*70)
        
        # Generate synthetic events
        synthetic_events = self.generate_synthetic_events(target_count=300)
        
        # Combine with real events
        all_events = self.real_events + synthetic_events
        
        # Update data
        self.data["events"] = all_events
        
        # Save
        with open(self.correlation_path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)
        
        # Summary
        total = len(all_events)
        with_prices = len([e for e in all_events if e.get("return_7d") is not None])
        
        print("\n" + "="*70)
        print("  DATA COLLECTION COMPLETE")
        print("="*70)
        print(f"  Real events: {len(self.real_events)}")
        print(f"  Synthetic events: {len(synthetic_events)}")
        print(f"  Total events: {total}")
        print(f"  Events with 7-day prices: {with_prices}")
        print("="*70)
        
        return {
            "real_events": len(self.real_events),
            "synthetic_events": len(synthetic_events),
            "total_events": total,
            "events_with_prices": with_prices
        }


if __name__ == "__main__":
    import time
    generator = EnhancedDataGenerator()
    summary = generator.combine_and_save()
    
    print(f"\n✅ Enhanced dataset ready!")
    print(f"   Total events: {summary['total_events']}")
    print(f"   With price data: {summary['events_with_prices']}")
    print(f"\n   Next: Train ML model with enhanced dataset")
