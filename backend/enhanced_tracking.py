#!/usr/bin/env python3
"""
Enhanced Automated Tracking with Price Data Collection
Run this every hour to:
1. Track government events
2. Collect stock price data
3. Calculate correlations
4. Train prediction model
5. Export patent evidence
"""
import requests
import json
import yfinance as yf
from datetime import datetime, timedelta
import time
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
DATA_DIR = Path("tracking_data")
DATA_DIR.mkdir(exist_ok=True)

def get_current_price(ticker: str) -> float:
    """Get current stock price"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return 0.0
    except Exception as e:
        print(f"  ✗ Error getting price for {ticker}: {e}")
        return 0.0

def track_foia_events():
    """Track FOIA events for major companies"""
    print("\n📄 Tracking FOIA events...")
    
    companies = [
        ("LMT", "LOCKHEED MARTIN"),
        ("BA", "BOEING"),
        ("NOC", "NORTHROP GRUMMAN"),
        ("GD", "GENERAL DYNAMICS"),
        ("RTX", "RAYTHEON"),
        ("PFE", "PFIZER"),
        ("JNJ", "JOHNSON & JOHNSON"),
        ("AAPL", "APPLE"),
        ("MSFT", "MICROSOFT"),
        ("GOOGL", "ALPHABET"),
        ("AMZN", "AMAZON"),
        ("TSLA", "TESLA"),
    ]
    
    tracked = 0
    for ticker, company in companies:
        try:
            # Get FOIA documents
            foia_response = requests.get(
                f"{BACKEND_URL}/api/foia/ticker/{ticker}",
                params={"company_name": company},
                timeout=30
            )
            
            if foia_response.status_code == 200:
                foia_docs = foia_response.json()
                
                # Track recent FOIA events
                for doc in foia_docs[:3]:  # Top 3 per company
                    event_desc = f"FOIA: {doc.get('title', 'Document')}"
                    
                    track_response = requests.post(
                        f"{BACKEND_URL}/api/correlation/track",
                        params={
                            "ticker": ticker,
                            "event_type": "FOIA",
                            "event_description": event_desc,
                            "company_name": company
                        },
                        timeout=10
                    )
                    
                    if track_response.status_code == 200:
                        tracked += 1
            
            # Small delay
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error tracking FOIA for {ticker}: {e}")
    
    print(f"  ✓ Tracked {tracked} FOIA events")

def track_contract_events():
    """Track federal contract events"""
    print("\n🏛️ Tracking federal contracts...")
    
    companies = [
        ("LMT", "LOCKHEED MARTIN"),
        ("BA", "BOEING"),
        ("NOC", "NORTHROP GRUMMAN"),
        ("GD", "GENERAL DYNAMICS"),
        ("RTX", "RAYTHEON"),
    ]
    
    tracked = 0
    for ticker, company in companies:
        try:
            # Get contracts
            contracts_response = requests.get(
                f"{BACKEND_URL}/api/usaspending/contracts/{ticker}",
                params={"company_name": company},
                timeout=60
            )
            
            if contracts_response.status_code == 200:
                contracts = contracts_response.json()
                
                # Track recent contract events
                for contract in contracts[:3]:
                    amount = contract.get("Award Amount", 0)
                    desc = contract.get("Description", "Federal Contract")
                    event_desc = f"Federal contract: {desc} - ${amount:,.2f}"
                    
                    track_response = requests.post(
                        f"{BACKEND_URL}/api/correlation/track",
                        params={
                            "ticker": ticker,
                            "event_type": "FEDERAL_CONTRACT",
                            "event_description": event_desc,
                            "company_name": company
                        },
                        timeout=10
                    )
                    
                    if track_response.status_code == 200:
                        tracked += 1
            
            time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ Error tracking contracts for {ticker}: {e}")
    
    print(f"  ✓ Tracked {tracked} contract events")

def track_regulatory_events():
    """Track regulatory events"""
    print("\n⚖️ Tracking regulatory events...")
    
    companies = [
        ("PFE", "Pfizer"),
        ("JNJ", "Johnson & Johnson"),
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("GOOGL", "Google"),
    ]
    
    tracked = 0
    for ticker, company in companies:
        try:
            # Get SEC filings
            sec_response = requests.get(
                f"{BACKEND_URL}/api/regulatory/sec/{ticker}",
                params={"limit": 3},
                timeout=30
            )
            
            if sec_response.status_code == 200:
                sec_filings = sec_response.json()
                
                for filing in sec_filings[:2]:
                    event_desc = f"SEC: {filing.get('description', 'Filing')} ({filing.get('form_type', 'N/A')})"
                    
                    track_response = requests.post(
                        f"{BACKEND_URL}/api/correlation/track",
                        params={
                            "ticker": ticker,
                            "event_type": "SEC_FILING",
                            "event_description": event_desc,
                            "company_name": company
                        },
                        timeout=10
                    )
                    
                    if track_response.status_code == 200:
                        tracked += 1
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error tracking regulatory for {ticker}: {e}")
    
    print(f"  ✓ Tracked {tracked} regulatory events")

def update_price_data():
    """Update price data for tracked events"""
    print("\n💰 Updating price data for tracked events...")
    
    try:
        # Get all tracked events
        accuracy_response = requests.get(
            f"{BACKEND_URL}/api/correlation/accuracy/stats",
            timeout=10
        )
        
        if accuracy_response.status_code != 200:
            print("  ✗ Failed to get correlation data")
            return
        
        accuracy_data = accuracy_response.json()
        total_events = accuracy_data.get("total_events", 0)
        
        if total_events == 0:
            print("  ⚠️ No events to update")
            return
        
        print(f"  ℹ️ Total events tracked: {total_events}")
        print(f"  ℹ️ Price updates will be calculated as events age")
        
        # For now, just log - price updates happen automatically as events age
        # In production, you'd have a background job that updates prices at 1/7/30 day intervals
        
    except Exception as e:
        print(f"  ✗ Error updating price data: {e}")

def train_prediction_model():
    """Train the prediction model if we have enough data"""
    print("\n🤖 Training prediction model...")
    
    try:
        # Train model
        train_response = requests.post(
            f"{BACKEND_URL}/api/predict/train",
            timeout=30
        )
        
        if train_response.status_code == 200:
            result = train_response.json()
            status = result.get("status", "unknown")
            
            if status == "trained":
                train_acc = result.get("train_accuracy", 0)
                test_acc = result.get("test_accuracy", 0)
                print(f"  ✓ Model trained: {train_acc:.1%} train, {test_acc:.1%} test")
            else:
                message = result.get("message", "Unknown")
                print(f"  ⚠️ {message}")
        else:
            print(f"  ✗ Training failed: {train_response.status_code}")
            
    except Exception as e:
        print(f"  ✗ Error training model: {e}")

def export_evidence():
    """Export correlation evidence for patent"""
    print("\n📄 Exporting patent evidence...")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/correlation/export",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Save with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = DATA_DIR / f"evidence_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            summary = data.get("summary", {})
            print(f"  ✓ Evidence exported to {filename}")
            print(f"  ✓ Events tracked: {summary.get('total_events_tracked', 0)}")
        else:
            print(f"  ✗ Export failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ Error exporting evidence: {e}")

def get_tracking_summary():
    """Get and display tracking summary"""
    print("\n📊 Tracking Summary:")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/correlation/evidence/summary",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Total events: {data.get('total_events_tracked', 0)}")
            print(f"  With price data: {data.get('total_with_price_data', 0)}")
            print(f"  Tracking active: {data.get('tracking_active', False)}")
        else:
            print(f"  ✗ Failed to get summary")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")

def main():
    print("="*70)
    print("  PREDOVEX ENHANCED AUTOMATED TRACKING")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Check backend
    try:
        health = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        if health.status_code != 200:
            print("\n✗ Backend not running")
            print("  Start: cd backend && uvicorn main:app --port 8000")
            return
    except Exception as e:
        print(f"\n✗ Cannot connect to backend: {e}")
        return
    
    print("\n✓ Backend is running")
    
    # Run tracking
    track_foia_events()
    track_contract_events()
    track_regulatory_events()
    
    # Update prices
    update_price_data()
    
    # Train model
    train_prediction_model()
    
    # Export evidence
    export_evidence()
    
    # Summary
    get_tracking_summary()
    
    print("\n" + "="*70)
    print("  ✓ Tracking cycle complete")
    print("  Next run: In 1 hour")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
