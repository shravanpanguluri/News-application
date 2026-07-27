"""
Ticker Mapper Service - Unified Company Name to Ticker Mapping
Integrates SEC EDGAR, manual mappings, and fuzzy matching for high-accuracy mapping.
"""
from typing import Optional, Dict, List
from services.sec_edgar_service import sec_edgar_service
import re
import json
from pathlib import Path

class TickerMapper:
    """Unified company name → stock ticker mapping service"""
    
    def __init__(self, mapping_file: Optional[str] = None):
        # Additional manual mappings not in SEC service
        self.MANUAL_MAPPINGS = {
            "lockheed martin": "LMT",
            "boeing": "BA",
            "northrop grumman": "NOC",
            "general dynamics": "GD",
            "raytheon": "RTX",
            "rtx": "RTX",
            "pfizer": "PFE",
            "moderna": "MRNA",
            "johnson & johnson": "JNJ",
            "amazon": "AMZN",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "meta": "META",
            "facebook": "META",
            "apple": "AAPL",
            "tesla": "TSLA",
            "palantir": "PLTR",
            "spacex": "TSLA", # Proxy
            "anduril": "PLTR", # Proxy
        }
        
        # Mapping file for persistence
        if mapping_file:
            self.mapping_file = Path(mapping_file)
        else:
            self.mapping_file = Path(__file__).parent.parent / "models" / "ticker_mappings.json"
            
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_mappings()

    def _load_mappings(self):
        """Load additional mappings from file"""
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r') as f:
                    file_mappings = json.load(f)
                    self.MANUAL_MAPPINGS.update(file_mappings)
            except Exception as e:
                print(f"⚠️ Error loading ticker mappings: {e}")

    def _save_mappings(self):
        """Save mappings to file"""
        try:
            with open(self.mapping_file, 'w') as f:
                json.dump(self.MANUAL_MAPPINGS, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving ticker mappings: {e}")

    def get_ticker(self, company_name: str) -> Optional[str]:
        """
        Get stock ticker for company name
        
        Args:
            company_name: Full company name
            
        Returns:
            Ticker symbol or None
        """
        if not company_name:
            return None
            
        name_lower = company_name.lower().strip()
        
        # 1. Try manual mappings first
        if name_lower in self.MANUAL_MAPPINGS:
            return self.MANUAL_MAPPINGS[name_lower]
            
        # 2. Try cleaning name
        clean_name = re.sub(r'\b(inc|corp|llc|ltd|incorporated|corporation|company|co)\b\.?', '', name_lower).strip()
        if clean_name in self.MANUAL_MAPPINGS:
            return self.MANUAL_MAPPINGS[clean_name]
            
        # 3. Use SEC EDGAR service for high-accuracy mapping
        ticker = sec_edgar_service.get_ticker_for_company(company_name)
        
        if ticker:
            # Cache the new mapping
            self.MANUAL_MAPPINGS[name_lower] = ticker
            return ticker
            
        return None

    def add_mapping(self, company_name: str, ticker: str):
        """Manually add a mapping"""
        self.MANUAL_MAPPINGS[company_name.lower().strip()] = ticker.upper().strip()
        self._save_mappings()


# Singleton instance
ticker_mapper = TickerMapper()
