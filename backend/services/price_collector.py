"""
Stock Price Collection Service
Collects real stock prices for tracked events at 1/7/30 day intervals
This is CRITICAL for ML model training and patent evidence.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path


class PriceCollector:
    """
    Collects and manages stock price data for tracked government events.
    
    For each tracked event, we need:
    - Price at event date (day 0)
    - Price at 1 day after
    - Price at 7 days after
    - Price at 30 days after
    
    This allows us to calculate returns and train the ML model.
    """

    def __init__(self, correlation_data_path: Optional[str] = None):
        # Use absolute path based on service file location
        if correlation_data_path:
            self.correlation_path = Path(correlation_data_path)
        else:
            # Default to backend directory
            self.correlation_path = Path(__file__).parent.parent / "correlation_data.json"
        
        self.data = self._load_correlation_data()

    def _load_correlation_data(self) -> Dict:
        """Load correlation tracking data"""
        if self.correlation_path.exists():
            with open(self.correlation_path, "r") as f:
                return json.load(f)
        return {"events": [], "correlations": {}, "accuracy_stats": {}}

    def _save_correlation_data(self):
        """Save correlation data back to file"""
        with open(self.correlation_path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def get_stock_price(self, ticker: str, date: str) -> Optional[float]:
        """
        Get stock closing price for a specific date
        
        Args:
            ticker: Stock ticker symbol
            date: Date in ISO format or YYYY-MM-DD
            
        Returns:
            Closing price or None
        """
        try:
            # Parse date
            if "T" in date:
                date_str = date.split("T")[0]
            else:
                date_str = date[:10]
            
            # Get historical data
            stock = yf.Ticker(ticker)
            
            # Get 5 days of data around the target date
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            start_date = (target_date - timedelta(days=5)).strftime("%Y-%m-%d")
            end_date = (target_date + timedelta(days=5)).strftime("%Y-%m-%d")
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                print(f"  ⚠️ No price data for {ticker} on {date_str}")
                return None
            
            # Just take the first available close price
            price = hist['Close'].iloc[0]
            
            return float(price)
            
        except Exception as e:
            print(f"  ✗ Error getting price for {ticker} on {date}: {e}")
            return None

    def update_event_prices(self, event: Dict) -> Dict:
        """
        Update price data for a single event
        
        Args:
            event: Event dict from correlation tracker
            
        Returns:
            Updated event dict
        """
        ticker = event.get("ticker", "")
        event_date_str = event.get("event_date", "")
        event_id = event.get("event_id", "")
        
        if not ticker or not event_date_str:
            return event
        
        # Normalize date string (remove timezone info for simplicity)
        if "T" in event_date_str:
            base_date_str = event_date_str.split("T")[0]
        else:
            base_date_str = event_date_str[:10]
        
        # Get event date price (day 0)
        if event.get("price_0d") is None:
            price_0 = self.get_stock_price(ticker, base_date_str)
            if price_0:
                event["price_0d"] = price_0
                print(f"  ✓ {event_id}: Day 0 price = ${price_0:.2f}")
        
        # Get 1-day price
        if event.get("price_1d") is None and event.get("price_0d"):
            try:
                event_date = datetime.strptime(base_date_str, "%Y-%m-%d")
                day_1_date = (event_date + timedelta(days=1)).strftime("%Y-%m-%d")
                price_1 = self.get_stock_price(ticker, day_1_date)
                
                if price_1:
                    event["price_1d"] = price_1
                    return_1d = ((price_1 - event["price_0d"]) / event["price_0d"]) * 100
                    event["return_1d"] = round(return_1d, 2)
                    print(f"  ✓ {event_id}: Day 1 price = ${price_1:.2f}, return = {return_1d:.2f}%")
            except Exception as e:
                print(f"  ✗ Error calculating 1-day return for {event_id}: {e}")
        
        # Get 7-day price
        if event.get("price_7d") is None and event.get("price_0d"):
            try:
                event_date = datetime.strptime(base_date_str, "%Y-%m-%d")
                day_7_date = (event_date + timedelta(days=7)).strftime("%Y-%m-%d")
                
                # Check if 7 days have passed
                if datetime.utcnow() >= event_date + timedelta(days=7):
                    price_7 = self.get_stock_price(ticker, day_7_date)
                    
                    if price_7:
                        event["price_7d"] = price_7
                        return_7d = ((price_7 - event["price_0d"]) / event["price_0d"]) * 100
                        event["return_7d"] = round(return_7d, 2)
                        print(f"  ✓ {event_id}: Day 7 price = ${price_7:.2f}, return = {return_7d:.2f}%")
            except Exception as e:
                print(f"  ✗ Error calculating 7-day return for {event_id}: {e}")
        
        # Get 30-day price
        if event.get("price_30d") is None and event.get("price_0d"):
            try:
                event_date = datetime.strptime(base_date_str, "%Y-%m-%d")
                day_30_date = (event_date + timedelta(days=30)).strftime("%Y-%m-%d")
                
                # Check if 30 days have passed
                if datetime.utcnow() >= event_date + timedelta(days=30):
                    price_30 = self.get_stock_price(ticker, day_30_date)
                    
                    if price_30:
                        event["price_30d"] = price_30
                        return_30d = ((price_30 - event["price_0d"]) / event["price_0d"]) * 100
                        event["return_30d"] = round(return_30d, 2)
                        print(f"  ✓ {event_id}: Day 30 price = ${price_30:.2f}, return = {return_30d:.2f}%")
            except Exception as e:
                print(f"  ✗ Error calculating 30-day return for {event_id}: {e}")
        
        return event

    def collect_all_prices(self) -> Dict:
        """
        Collect price data for all tracked events
        
        Returns:
            Summary of price collection
        """
        print("\n💰 Collecting stock prices for all tracked events...")
        print("="*70)
        
        events = self.data.get("events", [])
        
        if not events:
            print("⚠️ No events to update")
            return {"total_events": 0, "updated": 0}
        
        updated_count = 0
        total_events = len(events)
        
        for i, event in enumerate(events):
            print(f"\n[{i+1}/{total_events}] Processing {event.get('event_id', 'Unknown')}...")
            
            # Skip if already has all price data
            if all(event.get(f"return_{d}d") is not None for d in [1, 7, 30]):
                print(f"  ✓ Already has all price data")
                continue
            
            # Update prices
            updated_event = self.update_event_prices(event)
            
            if updated_event != event:
                updated_count += 1
        
        # Save updated data
        self._save_correlation_data()
        
        summary = {
            "total_events": total_events,
            "updated": updated_count,
            "with_day_0": len([e for e in events if e.get("price_0d")]),
            "with_day_1": len([e for e in events if e.get("return_1d") is not None]),
            "with_day_7": len([e for e in events if e.get("return_7d") is not None]),
            "with_day_30": len([e for e in events if e.get("return_30d") is not None]),
        }
        
        print("\n" + "="*70)
        print(f"💰 Price Collection Summary:")
        print(f"  Total events: {summary['total_events']}")
        print(f"  Updated: {summary['updated']}")
        print(f"  With Day 0 price: {summary['with_day_0']}")
        print(f"  With Day 1 return: {summary['with_day_1']}")
        print(f"  With Day 7 return: {summary['with_day_7']}")
        print(f"  With Day 30 return: {summary['with_day_30']}")
        print("="*70)
        
        return summary

    def get_training_ready_events(self, min_days: int = 7) -> List[Dict]:
        """
        Get events that have price data ready for ML training
        
        Args:
            min_days: Minimum days of price data required (1, 7, or 30)
            
        Returns:
            List of events with price data
        """
        events = self.data.get("events", [])
        
        # Filter events with required price data
        if min_days == 1:
            ready = [e for e in events if e.get("return_1d") is not None]
        elif min_days == 7:
            ready = [e for e in events if e.get("return_7d") is not None]
        elif min_days == 30:
            ready = [e for e in events if e.get("return_30d") is not None]
        else:
            ready = events
        
        print(f"\n📊 Found {len(ready)} events with {min_days}-day price data")
        return ready


# Initialize global price collector
price_collector = PriceCollector()


if __name__ == "__main__":
    print("💰 Stock Price Collector - Manual Run")
    print("="*70)
    
    # Collect all prices
    summary = price_collector.collect_all_prices()
    
    # Get training-ready events
    ready_events = price_collector.get_training_ready_events(min_days=7)
    
    if ready_events:
        print(f"\n✓ {len(ready_events)} events ready for ML training!")
    else:
        print("\n⚠️ No events ready for ML training yet")
        print("  Events need time to accumulate price data")
        print("  Run this script daily to collect prices as events age")
