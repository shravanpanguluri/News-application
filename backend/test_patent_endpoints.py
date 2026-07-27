#!/usr/bin/env python3
"""
Test Script for Patent-Critical API Endpoints
Tests FOIA, Regulatory, and Correlation tracking endpoints
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_foia_endpoints():
    print_section("FOIA INTELLIGENCE ENGINE ENDPOINTS")
    
    # Test 1: Recent FOIA releases
    print("1. Testing GET /api/foia/recent")
    response = requests.get(f"{BASE_URL}/api/foia/recent", params={"limit": 5})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} recent FOIA releases")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 2: Search FOIA by company
    print("\n2. Testing GET /api/foia/company/Lockheed Martin")
    response = requests.get(f"{BASE_URL}/api/foia/company/Lockheed Martin", params={"limit": 5})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} FOIA requests mentioning Lockheed Martin")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 3: Get FOIA documents for ticker
    print("\n3. Testing GET /api/foia/ticker/PFE")
    response = requests.get(f"{BASE_URL}/api/foia/ticker/PFE")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} documents for PFE")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 4: Get FOIA signals for ticker
    print("\n4. Testing GET /api/foia/signals/PFE")
    response = requests.get(f"{BASE_URL}/api/foia/signals/PFE")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Total documents: {data.get('total_documents', 0)}")
        print(f"   ✓ High strength signals: {data.get('high_strength_signals', 0)}")
        print(f"   ✓ Medium strength signals: {data.get('medium_strength_signals', 0)}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 5: Search Federal Register
    print("\n5. Testing GET /api/foia/federal-register")
    response = requests.get(f"{BASE_URL}/api/foia/federal-register", params={
        "query": "SEC enforcement",
        "limit": 5
    })
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} Federal Register documents")
    else:
        print(f"   ✗ Error: {response.text}")

def test_regulatory_endpoints():
    print_section("REGULATORY MONITOR ENDPOINTS")
    
    # Test 1: SEC filings
    print("1. Testing GET /api/regulatory/sec/AAPL")
    response = requests.get(f"{BASE_URL}/api/regulatory/sec/AAPL", params={"limit": 5})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} SEC filings for AAPL")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 2: FDA enforcement
    print("\n2. Testing GET /api/regulatory/fda/Pfizer")
    response = requests.get(f"{BASE_URL}/api/regulatory/fda/Pfizer", params={"limit": 5})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} FDA enforcement actions")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 3: Regulatory risk score
    print("\n3. Testing GET /api/regulatory/risk/PFE")
    response = requests.get(f"{BASE_URL}/api/regulatory/risk/PFE")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Risk Score: {data.get('risk_score', 'N/A')}/100")
        print(f"   ✓ Risk Level: {data.get('risk_level', 'N/A')}")
        print(f"   ✓ SEC Component: {data.get('breakdown', {}).get('sec_risk_score', 0)}")
        print(f"   ✓ FDA Component: {data.get('breakdown', {}).get('fda_risk_score', 0)}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 4: Regulatory alerts
    print("\n4. Testing GET /api/regulatory/alerts/PFE")
    response = requests.get(f"{BASE_URL}/api/regulatory/alerts/PFE")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Total alerts: {data.get('total_alerts', 0)}")
    else:
        print(f"   ✗ Error: {response.text}")

def test_correlation_endpoints():
    print_section("CORRELATION TRACKING ENDPOINTS")
    
    # Test 1: Track a new event
    print("1. Testing POST /api/correlation/track")
    response = requests.post(f"{BASE_URL}/api/correlation/track", params={
        "ticker": "AAPL",
        "event_type": "SEC_FILING",
        "event_description": "Apple files 10-K annual report",
        "company_name": "Apple Inc"
    })
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Event tracked: {data.get('event_id', 'N/A')}")
        print(f"   ✓ Ticker: {data.get('ticker', 'N/A')}")
        print(f"   ✓ Event type: {data.get('event_type', 'N/A')}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 2: Get correlation data for ticker
    print("\n2. Testing GET /api/correlation/AAPL")
    response = requests.get(f"{BASE_URL}/api/correlation/AAPL")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Total events for AAPL: {data.get('total_events', 0)}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 3: Get correlation accuracy
    print("\n3. Testing GET /api/correlation/accuracy")
    response = requests.get(f"{BASE_URL}/api/correlation/accuracy")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Total events tracked: {data.get('total_events', 0)}")
        print(f"   ✓ Events with price data: {data.get('with_price_data', 0)}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 4: Export correlation evidence
    print("\n4. Testing GET /api/correlation/export")
    response = requests.get(f"{BASE_URL}/api/correlation/export")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Evidence exported successfully")
        print(f"   ✓ Generated at: {data.get('generated_at', 'N/A')}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    # Test 5: Get evidence summary
    print("\n5. Testing GET /api/correlation/evidence/summary")
    response = requests.get(f"{BASE_URL}/api/correlation/evidence/summary")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Total events tracked: {data.get('total_events_tracked', 0)}")
        print(f"   ✓ Tracking active: {data.get('tracking_active', False)}")
    else:
        print(f"   ✗ Error: {response.text}")

def main():
    print("\n" + "="*60)
    print("  PREDOVEX PATENT-CRITICAL API ENDPOINT TESTER")
    print("="*60)
    print(f"  Base URL: {BASE_URL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # Check if backend is running
        health = requests.get(f"{BASE_URL}/docs", timeout=5)
        if health.status_code == 200:
            print("\n✓ Backend is running")
        else:
            print("\n✗ Backend may not be running properly")
            return
    except Exception as e:
        print(f"\n✗ Cannot connect to backend: {e}")
        return
    
    # Run all tests
    test_foia_endpoints()
    test_regulatory_endpoints()
    test_correlation_endpoints()
    
    print_section("TEST SUMMARY")
    print("✓ All endpoint tests completed")
    print("\nNext Steps:")
    print("  1. Visit http://localhost:8000/docs for interactive API documentation")
    print("  2. Start accumulating correlation data for patent evidence")
    print("  3. Build frontend UI to display FOIA and regulatory data")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
