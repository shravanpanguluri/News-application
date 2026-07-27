"""
Regulatory Enforcement Monitor - Basic Integration
Monitors SEC, FDA, EPA enforcement actions
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class RegulatoryMonitor:
    """Regulatory Enforcement Early Warning System"""
    
    def __init__(self):
        self.sec_base = "https://efts.sec.gov/LATEST"
        self.fda_base = "https://api.fda.gov"
        self.fed_register = "https://www.federalregister.gov/api/v1"
        self.timeout = 15
    
    def search_sec_filings(self, company: str,
                          filing_type: Optional[str] = None,
                          limit: int = 50) -> List[Dict]:
        """
        Search SEC EDGAR for company filings

        Args:
            company: Company name or ticker
            filing_type: Type of filing (10-K, 8-K, etc.) - optional
            limit: Max results

        Returns:
            List of SEC filings
        """
        try:
            # Use sec_edgar_service which has better error handling
            from services.sec_edgar_service import sec_edgar_service
            filings = sec_edgar_service.get_company_filings(
                company, filing_type=filing_type, limit=limit
            )
            # Convert to expected format
            results = []
            for f in filings:
                results.append({
                    "title": f.get("description", ""),
                    "filing_date": f.get("filing_date", ""),
                    "form_type": f.get("form_type", ""),
                    "url": f.get("filing_url", ""),
                    "description": f.get("description", ""),
                })
            print(f"SEC: Found {len(results)} filings for '{company}'")
            return results

        except Exception as e:
            print(f"SEC search error: {e}")
            return []
    
    def get_fda_enforcement(self, search_term: Optional[str] = None,
                           limit: int = 100) -> List[Dict]:
        """
        Get FDA enforcement actions (recalls, warnings)
        
        Args:
            search_term: Search term (company name, drug name, etc.)
            limit: Max results
        
        Returns:
            List of FDA enforcement actions
        """
        try:
            url = f"{self.fda_base}/drug/enforcement.json"
            params = {"limit": min(limit, 100)}
            
            if search_term:
                params["search"] = f'reason_for_recall:"{search_term}"'
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"FDA: Found {len(results)} enforcement actions")
                return results
            else:
                print(f"FDA API error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"FDA enforcement error: {e}")
            return []
    
    def get_fda_drug_events(self, drug_name: str, limit: int = 100) -> List[Dict]:
        """
        Get FDA adverse drug events
        
        Args:
            drug_name: Drug brand name
            limit: Max results
        
        Returns:
            List of adverse event reports
        """
        try:
            url = f"{self.fda_base}/drug/event.json"
            params = {
                "search": f'patient.drug.openfda.brand_name:"{drug_name}"',
                "limit": min(limit, 100)
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"FDA: Found {len(results)} adverse events for '{drug_name}'")
                return results
            else:
                print(f"FDA events error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"FDA events error: {e}")
            return []
    
    def get_regulatory_risk_score(self, ticker: str, 
                                 company_name: Optional[str] = None) -> Dict:
        """
        Calculate regulatory risk score (0-100)
        Based on SEC filings, FDA actions, Federal Register mentions
        
        Args:
            ticker: Stock ticker symbol
            company_name: Full company name (optional)
        
        Returns:
            Risk score dict
        """
        search_name = company_name or ticker
        
        # SEC risk component (count recent 8-K filings)
        sec_data = self.search_sec_filings(search_name, "8-K", limit=50)
        sec_risk = min(len(sec_data) * 2, 40)  # Max 40 points
        
        # FDA risk component
        fda_data = self.get_fda_enforcement(search_name, limit=50)
        fda_risk = min(len(fda_data) * 5, 30)  # Max 30 points
        
        # Federal Register mention risk
        fr_data = self._search_federal_register_simple(search_name)
        fr_risk = min(len(fr_data) * 3, 30)  # Max 30 points
        
        total_risk = sec_risk + fda_risk + fr_risk
        
        return {
            "ticker": ticker,
            "company": search_name,
            "total_risk_score": total_risk,
            "sec_component": sec_risk,
            "fda_component": fda_risk,
            "regulatory_component": fr_risk,
            "risk_level": "HIGH" if total_risk >= 70 else "MEDIUM" if total_risk >= 40 else "LOW",
            "timestamp": datetime.now().isoformat(),
        }
    
    def _search_federal_register_simple(self, query: str) -> List[Dict]:
        """Simple Federal Register search"""
        try:
            url = f"{self.fed_register}/documents.json"
            params = {
                "per_page": 50,
                "order": "newest",
                "conditions[term]": query,
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            return []
        except:
            return []
    
    def get_regulatory_alerts_for_ticker(self, ticker: str,
                                        company_name: Optional[str] = None) -> List[Dict]:
        """
        Get all regulatory alerts for a company
        
        Args:
            ticker: Stock ticker
            company_name: Full company name (optional)
        
        Returns:
            List of regulatory alerts
        """
        search_name = company_name or ticker
        alerts = []
        
        # Get SEC filings
        sec_filings = self.search_sec_filings(search_name, limit=20)
        for filing in sec_filings:
            alert = {
                "type": "sec_filing",
                "ticker": ticker,
                "title": filing.get("display_names", ["Unknown"])[0],
                "date": filing.get("filed_at", ""),
                "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={filing.get('cik', '')}",
                "severity": "MEDIUM",
            }
            alerts.append(alert)
        
        # Get FDA enforcement
        fda_actions = self.get_fda_enforcement(search_name, limit=20)
        for action in fda_actions:
            alert = {
                "type": "fda_enforcement",
                "ticker": ticker,
                "title": action.get("reason_for_recall", "Unknown"),
                "date": action.get("recall_initiation_date", ""),
                "url": "",
                "severity": "HIGH",
            }
            alerts.append(alert)
        
        print(f"Found {len(alerts)} regulatory alerts for {ticker}")
        return alerts


# Initialize global regulatory monitor
regulatory_monitor = RegulatoryMonitor()


if __name__ == "__main__":
    print("⚖️ Regulatory Monitor - Demo")
    print("=" * 50)
    
    # Demo: Search SEC filings
    sec_filings = regulatory_monitor.search_sec_filings("AAPL", "8-K", limit=5)
    print(f"\n📄 SEC 8-K filings: {len(sec_filings)}")
    
    # Demo: Get FDA enforcement
    fda_actions = regulatory_monitor.get_fda_enforcement("Pfizer", limit=5)
    print(f"💊 FDA enforcement: {len(fda_actions)}")
    
    # Demo: Calculate risk score
    risk = regulatory_monitor.get_regulatory_risk_score("PFE", "Pfizer")
    print(f"\n📊 Regulatory Risk Score for PFE:")
    print(f"  Total: {risk['total_risk_score']}/100")
    print(f"  Level: {risk['risk_level']}")
    print(f"  SEC: {risk['sec_component']}/40")
    print(f"  FDA: {risk['fda_component']}/30")
    print(f"  Other: {risk['regulatory_component']}/30")
    
    # Demo: Get alerts
    alerts = regulatory_monitor.get_regulatory_alerts_for_ticker("AAPL", "Apple")
    print(f"\n🚨 Regulatory alerts: {len(alerts)}")
