#!/usr/bin/env python3
"""
Automated Correlation Tracking Script
Run this every hour to track government events and correlate with stock prices
"""
import requests
import json
from datetime import datetime
import time

BACKEND_URL = "http://localhost:8000"

def track_recent_foia_events():
    """Track recent FOIA releases as events"""
    print("\n📄 Tracking recent FOIA events...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/foia/recent", params={"limit": 10})
        if response.status_code == 200:
            foia_docs = response.json()
            print(f"  Found {len(foia_docs)} FOIA documents")
            
            tracked = 0
            for doc in foia_docs[:5]:  # Track top 5
                ticker = doc.get("ticker", "")
                if ticker and len(ticker) <= 5:  # Simple ticker validation
                    event_desc = doc.get("title", "FOIA Document")
                    event_date = doc.get("date", "")
                    
                    track_response = requests.get(
                        f"{BACKEND_URL}/api/correlation/track",
                        params={
                            "ticker": ticker,
                            "event_type": "FOIA",
                            "event_description": event_desc,
                            "event_date": event_date if event_date else None
                        }
                    )
                    
                    if track_response.status_code == 200:
                        tracked += 1
                        result = track_response.json()
                        print(f"  ✓ Tracked: {result.get('event_id')}")
                    else:
                        print(f"  ✗ Failed to track: {ticker}")
            
            print(f"  ✓ Tracked {tracked}/5 FOIA events")
        else:
            print(f"  ✗ Failed to fetch FOIA docs: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

def track_regulatory_events():
    """Track regulatory events for major companies"""
    print("\n⚖️ Tracking regulatory events...")
    
    # List of major companies to monitor
    companies = [
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("GOOGL", "Google"),
        ("AMZN", "Amazon"),
        ("TSLA", "Tesla"),
        ("PFE", "Pfizer"),
        ("JNJ", "Johnson & Johnson"),
        ("LMT", "Lockheed Martin"),
    ]
    
    tracked = 0
    for ticker, company in companies:
        try:
            # Check for SEC filings
            sec_response = requests.get(
                f"{BACKEND_URL}/api/regulatory/sec/{company}",
                params={"limit": 3}
            )
            
            if sec_response.status_code == 200:
                sec_filings = sec_response.json()
                if sec_filings and len(sec_filings) > 0:
                    # Track the most recent filing
                    filing = sec_filings[0]
                    event_desc = filing.get("title", f"SEC Filing - {company}")
                    
                    track_response = requests.get(
                        f"{BACKEND_URL}/api/correlation/track",
                        params={
                            "ticker": ticker,
                            "event_type": "SEC_FILING",
                            "event_description": event_desc
                        }
                    )
                    
                    if track_response.status_code == 200:
                        tracked += 1
                        result = track_response.json()
                        print(f"  ✓ Tracked: {result.get('event_id')}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error tracking {ticker}: {e}")
    
    print(f"  ✓ Tracked {tracked} regulatory events")

def get_tracking_summary():
    """Get current tracking summary"""
    print("\n📊 Current Tracking Summary:")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/correlation/evidence/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"  Total events tracked: {data.get('total_events_tracked', 0)}")
            print(f"  Events with price data: {data.get('total_with_price_data', 0)}")
            print(f"  Average accuracy: {data.get('average_accuracy', 0)}%")
            print(f"  Tracking active: {data.get('tracking_active', False)}")
        else:
            print(f"  ✗ Failed to get summary: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

def export_evidence():
    """Export correlation evidence for patent"""
    print("\n📄 Exporting correlation evidence...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/correlation/export")
        if response.status_code == 200:
            data = response.json()
            
            # Save to file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"correlation_evidence_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"  ✓ Evidence exported to {filename}")
            print(f"  ✓ Summary: {data.get('summary', {})}")
        else:
            print(f"  ✗ Failed to export: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

def main():
    print("="*60)
    print("  PREDOVEX AUTOMATED CORRELATION TRACKING")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Check if backend is running
    try:
        health = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        if health.status_code != 200:
            print("\n✗ Backend is not running or not responding")
            print("  Start backend: cd backend && uvicorn main:app --port 8000")
            return
    except Exception as e:
        print(f"\n✗ Cannot connect to backend: {e}")
        print("  Start backend: cd backend && uvicorn main:app --port 8000")
        return
    
    print("\n✓ Backend is running")
    
    # Run tracking
    track_recent_foia_events()
    track_regulatory_events()
    
    # Get summary
    get_tracking_summary()
    
    # Export evidence
    export_evidence()
    
    print("\n" + "="*60)
    print("  ✓ Tracking cycle complete")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
