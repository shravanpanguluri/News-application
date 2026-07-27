"""
SEC EDGAR Integration Service - Company Filings & Ticker Mapping
Provides:
- Company name → CIK → Ticker mapping via SEC EDGAR
- Real-time filing retrieval (10-K, 8-K, 10-Q, etc.)
- Filing metadata extraction for signal analysis
- Fuzzy company name matching against SEC database

This is a CRITICAL patent component: accurate company identification
and regulatory filing integration.
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path
import time
import re


class SECEdgarService:
    """
    SEC EDGAR Intelligence Engine

    Tracks:
    - Company CIK numbers and ticker mappings
    - SEC filings (10-K, 8-K, 10-Q, DEF 14A, etc.)
    - Insider trading (Form 4)
    - Material event disclosures (8-K)
    - Annual/quarterly reports (10-K/10-Q)
    """

    def __init__(self):
        self.edgar_base = "https://www.sec.gov/cgi-bin"
        self.edgar_api = "https://data.sec.gov"
        self.edgar_full = "https://www.sec.gov/Archives"
        self.timeout = 15
        self.headers = {
            "User-Agent": "Predovex admin@predovex.io",
            "Accept-Encoding": "gzip, deflate",
        }

        # Cache for company lookups
        self._cik_cache: Dict[str, Dict] = {}
        self._company_ticker_map: Dict[str, str] = {}
        self._ticker_company_map: Dict[str, str] = {}

        # Known CIK numbers for major companies (SEC search API is unreliable)
        self._cik_mappings: Dict[str, str] = {
            # Defense
            "LMT": "0000936468", "BA": "0000012927", "NOC": "0001133421",
            "GD": "0000040533", "RTX": "0000101829", "LHX": "0001739940",
            "HII": "0001501585", "TDG": "0001069185",
            # Technology
            "AAPL": "0000320193", "MSFT": "0000789019", "GOOGL": "0001652044",
            "AMZN": "0001018724", "NVDA": "0001045810", "META": "0001326801",
            "TSLA": "0001318605", "ORCL": "0001341439", "CRM": "0001108524",
            "IBM": "0000051143", "INTC": "0000050863", "AMD": "0000002488",
            "ADBE": "0000796343", "NFLX": "0001065280", "PYPL": "0001633917",
            # Healthcare
            "JNJ": "0000200406", "PFE": "0000078003", "MRK": "0000310158",
            "ABBV": "0001551152", "LLY": "0000059478", "UNH": "0000731766",
            "BMY": "0000014272", "AMGN": "0000318154", "GILD": "0000882095",
            "CVS": "0000064803",
            # Finance
            "JPM": "0000019617", "BAC": "0000070858", "GS": "0000886982",
            "MS": "0000895421", "WFC": "0000072971", "C": "0000831001",
            "BLK": "0001364742", "AXP": "0000004962", "V": "0001403161",
            "MA": "0001141391",
            # Energy
            "XOM": "0000034088", "CVX": "0000093410", "COP": "0001163165",
            "SLB": "0000087347", "EOG": "0000821189",
            # Consumer
            "HD": "0000354950", "PG": "0000080424", "KO": "0000021344",
            "WMT": "0000104169", "MCD": "0000063908", "NKE": "0000320187",
            "DIS": "0001744489", "SBUX": "0000829224", "TGT": "0000027419",
            "LOW": "0000060667",
            # Industrial
            "CAT": "0000018230", "GE": "0000040545", "MMM": "0000066740",
            "HON": "0000773840", "UPS": "0001090727", "FDX": "0001048911",
            # Telecom
            "T": "0000732717", "VZ": "0000732712", "TMUS": "0001283699",
            # Healthcare — additional
            "AMAT": "0000006955", "REGN": "0000872589", "HUM": "0000049071",
            "CI": "0000723254", "AZN": "0000901832", "MRNA": "0001682852",
            "BNTX": "0001776197", "SNY": "0000718286", "GSK": "0000883975",
            # Defense & IT services
            "BAH": "0001443646", "LDOS": "0001336920", "CACI": "0000016058",
            "PLTR": "0001321655", "KTOS": "0001069258", "MRCY": "0000866829",
            "SPR": "0001364885",
            # Engineering & infrastructure
            "J": "0000052822", "ACM": "0001193311", "FLR": "0000037996",
            "PWR": "0001050606", "HWM": "0000004281",
            # Energy
            "HAL": "0000045012", "BKR": "0001701605", "OKE": "0001061219",
            "NEE": "0000753308", "SO": "0000092122",
            # Satellite & tech
            "VSAT": "0000797721",
            # Previously missing — wave3 / expansion tickers
            "ELV":  "0001156039",  # Elevance Health (formerly Anthem)
            "HCA":  "0000860730",  # HCA Healthcare
            "MCK":  "0000927653",  # McKesson
            "SYK":  "0000310764",  # Stryker
            "ISRG": "0001035267",  # Intuitive Surgical
            "ZBH":  "0001136869",  # Zimmer Biomet
            "DGX":  "0001022079",  # Quest Diagnostics
            "LH":   "0000920148",  # Labcorp
            "ILMN": "0001110803",  # Illumina
            "GEHC": "0001932393",  # GE HealthCare Technologies
            "AVAV": "0001054374",  # AeroVironment
            "TXT":  "0000217346",  # Textron
            "CW":   "0000026535",  # Curtiss-Wright
            "MOOG": "0000067887",  # Moog Inc
            "CDNS": "0000813672",  # Cadence Design Systems
            "ANSS": "0000820081",  # ANSYS
            "VRSK": "0001442145",  # Verisk Analytics
            "HEI":  "0000046619",  # HEICO
            "AXON": "0001069183",  # Axon Enterprise
            "DRS":  "0001854401",  # Leonardo DRS
            "HPE":  "0001645590",  # Hewlett Packard Enterprise
            "DELL": "0001571123",  # Dell Technologies
            "ACN":  "0001467373",  # Accenture
            "TXN":  "0000097476",  # Texas Instruments
            "VRTX": "0000875320",  # Vertex Pharmaceuticals
            "MOH":  "0001179929",  # Molina Healthcare
            "CNC":  "0001071739",  # Centene
            "MDT":  "0001613103",  # Medtronic
            "ABT":  "0000001800",  # Abbott Laboratories
            "TMO":  "0000097745",  # Thermo Fisher Scientific
            "DHR":  "0000313616",  # Danaher
            "BSX":  "0000316206",  # Boston Scientific
            "BIIB": "0000875045",  # Biogen
            "DE":   "0000315189",  # Deere & Company
            "EMR":  "0000032604",  # Emerson Electric
            "ETN":  "0001551182",  # Eaton
            "PH":   "0000076334",  # Parker Hannifin
            "PSX":  "0001534701",  # Phillips 66
            "GM":   "0001467858",  # General Motors
            "OXY":  "0000797468",  # Occidental Petroleum
            "OKE":  "0001061219",  # ONEOK
            "QCOM": "0000804328",  # Qualcomm
        }

        # Load persistent company mappings
        self._load_company_mappings()

    def _load_company_mappings(self):
        """Load known company ↔ ticker mappings"""
        # Comprehensive mapping of common companies
        known_mappings = {
            # Defense
            "LOCKHEED MARTIN CORP": "LMT",
            "BOEING CO": "BA",
            "NORTHROP GRUMMAN CORP": "NOC",
            "GENERAL DYNAMICS CORP": "GD",
            "RTX CORP": "RTX",
            "L3HARRIS TECHNOLOGIES INC": "LHX",
            "HUNTINGTON INGALLS INDUSTRIES INC": "HII",
            "TRANSDIGM GROUP INC": "TDG",
            # Technology
            "APPLE INC": "AAPL",
            "MICROSOFT CORP": "MSFT",
            "ALPHABET INC": "GOOGL",
            "AMAZON COM INC": "AMZN",
            "NVIDIA CORP": "NVDA",
            "META PLATFORMS INC": "META",
            "TESLA INC": "TSLA",
            "ORACLE CORP": "ORCL",
            "SALESFORCE INC": "CRM",
            "INTERNATIONAL BUSINESS MACHINES CORP": "IBM",
            "INTEL CORP": "INTC",
            "ADVANCED MICRO DEVICES INC": "AMD",
            "ADOBE INC": "ADBE",
            "NETFLIX INC": "NFLX",
            "PAYPAL HOLDINGS INC": "PYPL",
            # Healthcare
            "JOHNSON & JOHNSON": "JNJ",
            "PFIZER INC": "PFE",
            "MERCK & CO INC": "MRK",
            "ABBVIE INC": "ABBV",
            "ELI LILLY & CO": "LLY",
            "UNITEDHEALTH GROUP INC": "UNH",
            "BRISTOL-MYERS SQUIBB CO": "BMY",
            "AMGEN INC": "AMGN",
            "GILEAD SCIENCES INC": "GILD",
            "CVS HEALTH CORP": "CVS",
            # Finance
            "JPMORGAN CHASE & CO": "JPM",
            "BANK OF AMERICA CORP": "BAC",
            "GOLDMAN SACHS GROUP INC": "GS",
            "MORGAN STANLEY": "MS",
            "WELLS FARGO & CO": "WFC",
            "CITIGROUP INC": "C",
            "BLACKROCK INC": "BLK",
            "AMERICAN EXPRESS CO": "AXP",
            "VISA INC": "V",
            "MASTERCARD INC": "MA",
            # Energy
            "EXXON MOBIL CORP": "XOM",
            "CHEVRON CORP": "CVX",
            "CONOCOPHILLIPS": "COP",
            "SCHLUMBERGER NV": "SLB",
            "EOG RESOURCES INC": "EOG",
            # Consumer
            "HOME DEPOT INC": "HD",
            "PROCTER & GAMBLE CO": "PG",
            "COCA COLA CO": "KO",
            "WALMART INC": "WMT",
            "MCDONALDS CORP": "MCD",
            "NIKE INC": "NKE",
            "WALT DISNEY CO": "DIS",
            "STARBUCKS CORP": "SBUX",
            "TARGET CORP": "TGT",
            "LOWES COS INC": "LOW",
            # Industrial
            "CATERPILLAR INC": "CAT",
            "GENERAL ELECTRIC CO": "GE",
            "3M CO": "MMM",
            "HONEYWELL INTERNATIONAL INC": "HON",
            "UNITED PARCEL SERVICE INC": "UPS",
            "FEDEX CORP": "FDX",
            # Telecom
            "AT&T INC": "T",
            "VERIZON COMMUNICATIONS INC": "VZ",
            "T-MOBILE US INC": "TMUS",
        }

        self._company_ticker_map = known_mappings
        # Build reverse map
        for company, ticker in known_mappings.items():
            self._ticker_company_map[ticker] = company

    def _normalize_name(self, name: str) -> str:
        """Normalize company name for matching"""
        name = name.upper().strip()
        # Remove common suffixes/prefixes
        name = re.sub(r'\b(CORP|CORPORATION|INC|INCORPORATED|CO|COMPANY|LTD|LIMITED|LLC|PLC)\b\.?', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _fuzzy_match_company(self, company_name: str) -> Optional[str]:
        """
        Fuzzy match company name to known SEC company names

        Returns matched company name or None
        """
        normalized = self._normalize_name(company_name)

        # Exact match first
        if normalized in self._company_ticker_map:
            return normalized

        # Try partial match - check if any known company contains the search term
        search_term = normalized
        for company_name in self._company_ticker_map:
            if search_term in company_name or company_name in search_term:
                return company_name

        # Try word-by-word matching
        words = normalized.split()
        if len(words) >= 2:
            for company_name in self._company_ticker_map:
                company_words = company_name.split()
                # Check if at least 2 words match
                matches = sum(1 for w in words if any(w in cw or cw in w for cw in company_words))
                if matches >= 2:
                    return company_name

        return None

    def get_ticker_for_company(self, company_name: str) -> Optional[str]:
        """
        Get stock ticker for a company name using SEC EDGAR mappings

        Args:
            company_name: Company name (e.g., "Lockheed Martin")

        Returns:
            Ticker symbol or None
        """
        # Check direct ticker input
        if company_name.upper() in self._ticker_company_map:
            return company_name.upper()

        # Try fuzzy match
        matched_company = self._fuzzy_match_company(company_name)
        if matched_company:
            return self._company_ticker_map.get(matched_company)

        # Try SEC EDGAR lookup
        cik = self._lookup_cik_by_name(company_name)
        if cik:
            # Get company facts which includes ticker
            facts = self._get_company_facts(cik)
            if facts:
                ticker = facts.get("ticker")
                if ticker:
                    # Cache the mapping
                    normalized = self._normalize_name(company_name)
                    self._company_ticker_map[normalized] = ticker
                    self._ticker_company_map[ticker] = normalized
                    return ticker

        return None

    def get_company_for_ticker(self, ticker: str) -> Optional[str]:
        """
        Get company name for a ticker symbol

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company name or None
        """
        ticker = ticker.upper()
        if ticker in self._ticker_company_map:
            return self._ticker_company_map[ticker]

        # Try SEC EDGAR lookup
        cik = self._lookup_cik_by_ticker(ticker)
        if cik:
            facts = self._get_company_facts(cik)
            if facts:
                name = facts.get("name")
                if name:
                    self._ticker_company_map[ticker] = name
                    self._company_ticker_map[self._normalize_name(name)] = ticker
                    return name

        return None

    def _lookup_cik_by_name(self, company_name: str) -> Optional[str]:
        """
        Look up CIK number by company name using SEC EDGAR API

        Args:
            company_name: Company name

        Returns:
            CIK number or None
        """
        try:
            # First check internal mappings
            normalized = self._normalize_name(company_name)
            if normalized in self._company_ticker_map:
                ticker = self._company_ticker_map[normalized]
                # Try to find CIK by ticker using the submissions API
                cik = self._lookup_cik_by_ticker(ticker)
                if cik:
                    return cik

            # Use SEC company name search API (new endpoint)
            url = f"{self.edgar_base}/lookup"
            params = {"company": company_name}

            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                # Parse CIK from response
                text = response.text
                cik_match = re.search(r'CIK=(\d+)', text)
                if cik_match:
                    cik = cik_match.group(1)
                    print(f"SEC EDGAR: Found CIK {cik} for '{company_name}'")
                    return cik

            return None

        except Exception as e:
            print(f"SEC EDGAR CIK lookup error: {e}")
            return None

    def _lookup_cik_by_ticker(self, ticker: str) -> Optional[str]:
        """
        Look up CIK number by ticker symbol

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK number or None
        """
        # First check hardcoded CIK mappings
        ticker_upper = ticker.upper()
        if ticker_upper in self._cik_mappings:
            cik = self._cik_mappings[ticker_upper]
            print(f"SEC EDGAR: Found CIK {cik} for ticker '{ticker}' (from mapping)")
            return cik

        # Try SEC full-text search API as fallback
        try:
            url = "https://efts.sec.gov/LATEST/search-index"
            params = {
                "q": f"ticker:{ticker}",
                "dateRange": "custom",
                "startdt": "2020-01-01",
                "enddt": "2026-12-31",
                "page": "1",
                "from": "0",
                "size": "1"
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", {}).get("hits", [])
                if hits:
                    cik = hits[0].get("_source", {}).get("ciks", [None])[0]
                    if cik:
                        print(f"SEC EDGAR: Found CIK {cik} for ticker '{ticker}'")
                        return str(cik)

            return None

        except Exception as e:
            print(f"SEC EDGAR ticker lookup error: {e}")
            return None

    def _get_company_facts(self, cik: str) -> Optional[Dict]:
        """
        Get company facts from SEC EDGAR API including ticker

        Args:
            cik: CIK number

        Returns:
            Company facts dict or None
        """
        try:
            # Pad CIK with zeros
            cik_padded = cik.zfill(10)

            url = f"{self.edgar_api}/submissions/CIK{cik_padded}.json"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                return {
                    "cik": data.get("cik"),
                    "name": data.get("name"),
                    "ticker": data.get("tickers", [None])[0] if data.get("tickers") else None,
                    "sic": data.get("sic"),
                    "sic_description": data.get("sicDescription"),
                    "fiscal_year_end": data.get("fiscalYearEnd"),
                    "filings": data.get("filings", {}).get("recent", {})
                }

            return None

        except Exception as e:
            print(f"SEC EDGAR company facts error: {e}")
            return None

    def get_company_filings(self, company_name: str,
                           filing_type: Optional[str] = None,
                           limit: int = 20) -> List[Dict]:
        """
        Get SEC filings for a company

        Args:
            company_name: Company name or ticker
            filing_type: Type of filing (10-K, 8-K, 10-Q, DEF 14A, 4, etc.)
            limit: Max results

        Returns:
            List of filings
        """
        # Try to find CIK — always attempt ticker lookup first
        cik = self._lookup_cik_by_ticker(company_name.upper())
        if not cik:
            cik = self._lookup_cik_by_name(company_name)

        if not cik:
            print(f"SEC EDGAR: Could not find CIK for '{company_name}'")
            return []

        return self._get_filings_by_cik(cik, filing_type, limit)

    def _get_filings_by_cik(self, cik: str,
                           filing_type: Optional[str] = None,
                           limit: int = 20) -> List[Dict]:
        """
        Get filings by CIK number

        Args:
            cik: CIK number
            filing_type: Type of filing (optional)
            limit: Max results

        Returns:
            List of filings
        """
        try:
            cik_padded = cik.zfill(10)
            url = f"{self.edgar_api}/submissions/CIK{cik_padded}.json"

            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code != 200:
                print(f"SEC EDGAR API error: {response.status_code}")
                return []

            data = response.json()
            recent_filings = data.get("filings", {}).get("recent", {})

            filings_list = []
            forms = recent_filings.get("form", [])
            dates = recent_filings.get("filingDate", [])
            descriptions = recent_filings.get("description", [])
            accession_numbers = recent_filings.get("accessionNumber", [])
            file_numbers = recent_filings.get("filmNumber", [])

            for i, form_type in enumerate(forms):
                # Filter by filing type if specified
                if filing_type and form_type != filing_type:
                    continue

                # Build filing URL
                accession_no = accession_numbers[i].replace("-", "") if i < len(accession_numbers) else ""
                filing_url = f"{self.edgar_full}/edgar/data/{cik}/{accession_no}/{accession_numbers[i]}.txt"
                html_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_numbers[i]}&xbrl_type=v"

                filing = {
                    "type": "sec_filing",
                    "form_type": form_type,
                    "filing_date": dates[i] if i < len(dates) else "",
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "cik": cik,
                    "company_name": data.get("name", ""),
                    "ticker": data.get("tickers", [None])[0] if data.get("tickers") else None,
                    "accession_number": accession_numbers[i] if i < len(accession_numbers) else "",
                    "file_number": file_numbers[i] if i < len(file_numbers) else "",
                    "filing_url": html_url,
                    "document_url": filing_url,
                    "source": "SEC EDGAR",
                }

                filings_list.append(filing)

                if len(filings_list) >= limit:
                    break

            print(f"SEC EDGAR: Found {len(filings_list)} filings for CIK {cik}")
            return filings_list

        except Exception as e:
            print(f"SEC EDGAR filings error: {e}")
            return []

    def get_recent_8k_filings(self, limit: int = 50) -> List[Dict]:
        """
        Get recent 8-K filings (material events) across all companies

        8-K filings are CRITICAL for patent claims - they report material events
        that could affect stock prices.

        Args:
            limit: Max results

        Returns:
            List of 8-K filings
        """
        try:
            # Use SEC RSS feed for recent filings
            url = "https://www.sec.gov/cgi-bin/current-q11-2024"

            # Alternative: Use the structured API for recent filings
            # We'll search through company submissions
            # For now, use a broader approach

            filings = []

            # Search through top companies' recent 8-Ks
            top_companies = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                "JPM", "BAC", "GS", "JNJ", "PFE", "UNH", "XOM", "CVX",
                "LMT", "BA", "NOC", "HD", "WMT", "V", "MA", "PG", "KO"
            ]

            for ticker in top_companies:
                cik = self._lookup_cik_by_ticker(ticker)
                if cik:
                    eight_k_filings = self._get_filings_by_cik(cik, "8-K", limit=3)
                    filings.extend(eight_k_filings)

                if len(filings) >= limit:
                    break

            print(f"SEC EDGAR: Found {len(filings)} recent 8-K filings")
            return filings[:limit]

        except Exception as e:
            print(f"SEC EDGAR 8-K search error: {e}")
            return []

    def get_insider_trading_filings(self, company_name: str,
                                   limit: int = 20) -> List[Dict]:
        """
        Get Form 4 insider trading filings for a company

        Form 4 filings show insider buying/selling - a strong signal.

        Args:
            company_name: Company name or ticker
            limit: Max results

        Returns:
            List of Form 4 filings
        """
        return self.get_company_filings(company_name, filing_type="4", limit=limit)

    def analyze_filing_for_signals(self, filing: Dict) -> Dict:
        """
        Analyze SEC filing for trading signals

        Args:
            filing: SEC filing dict

        Returns:
            Signal dict
        """
        form_type = filing.get("form_type", "")
        description = (filing.get("description", "") or "").lower()

        # Signal strength by filing type
        type_signals = {
            "8-K": {"base_score": 70, "reason": "Material event disclosure"},
            "10-K": {"base_score": 40, "reason": "Annual report - comprehensive"},
            "10-Q": {"base_score": 35, "reason": "Quarterly report"},
            "DEF 14A": {"base_score": 30, "reason": "Proxy statement - governance"},
            "4": {"base_score": 60, "reason": "Insider trading activity"},
            "S-1": {"base_score": 50, "reason": "IPO/new securities registration"},
            "SC 13D": {"base_score": 65, "reason": "Activist investor position"},
            "SC 13G": {"base_score": 45, "reason": "Passive investor position"},
        }

        signal_info = type_signals.get(form_type, {"base_score": 25, "reason": "Other filing"})

        # Look for material keywords in description
        material_keywords = {
            "acquisition": 15, "merger": 15, "bankruptcy": 20,
            "restructuring": 10, "layoff": 10, "recall": 15,
            "investigation": 15, "settlement": 10, "fine": 15,
            "penalty": 15, "violation": 10, "fraud": 20,
            "default": 15, "impairment": 10, "write-down": 10,
            "contract": 5, "award": 5, "approval": 5,
            "fda": 10, "clinical": 8, "trial": 8,
            "revenue": 3, "earnings": 3, "guidance": 5,
        }

        keyword_score = 0
        found_keywords = []
        for keyword, score in material_keywords.items():
            if keyword in description:
                keyword_score += score
                found_keywords.append(keyword)

        # Cap keyword score
        keyword_score = min(keyword_score, 30)

        # Final score
        final_score = min(signal_info["base_score"] + keyword_score, 100)

        # Determine signal strength
        if final_score >= 70:
            strength = "HIGH"
        elif final_score >= 40:
            strength = "MEDIUM"
        else:
            strength = "LOW"

        return {
            "document_title": filing.get("description", ""),
            "form_type": form_type,
            "signal_strength": strength,
            "signal_score": final_score,
            "material_keywords_found": found_keywords,
            "date": filing.get("filing_date"),
            "source": "SEC EDGAR",
            "url": filing.get("filing_url", ""),
            "reason": signal_info["reason"],
        }

    def get_filings_for_ticker(self, ticker: str,
                              filing_type: Optional[str] = None,
                              limit: int = 20) -> List[Dict]:
        """
        Get SEC filings for a ticker symbol with signal analysis

        Args:
            ticker: Stock ticker symbol
            filing_type: Type of filing (optional)
            limit: Max results

        Returns:
            List of filings with signals
        """
        filings = self.get_company_filings(ticker, filing_type, limit)

        # Add signal analysis
        analyzed_filings = []
        for filing in filings:
            signal = self.analyze_filing_for_signals(filing)
            filing_with_signal = {**filing, "signal": signal}
            analyzed_filings.append(filing_with_signal)

        return analyzed_filings

    def get_all_company_tickers(self) -> Dict[str, str]:
        """
        Get complete company name → ticker mapping

        Returns:
            Dict mapping company names to tickers
        """
        return dict(self._company_ticker_map)

    def search_companies(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for companies by name

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching companies with tickers
        """
        query_normalized = self._normalize_name(query)
        results = []

        for company_name, ticker in self._company_ticker_map.items():
            if query_normalized in company_name or query.lower() in company_name.lower():
                results.append({
                    "company_name": company_name,
                    "ticker": ticker,
                    "match_score": 1.0 if query_normalized == company_name else 0.7
                })

        # Sort by match quality
        results.sort(key=lambda x: x["match_score"], reverse=True)

        return results[:limit]


# Initialize global service
sec_edgar_service = SECEdgarService()


if __name__ == "__main__":
    print("🏛️ SEC EDGAR Integration - Demo")
    print("=" * 60)

    # Demo: Get ticker for company name
    print("\n1. Ticker lookup:")
    ticker = sec_edgar_service.get_ticker_for_company("Lockheed Martin")
    print(f"   Lockheed Martin → {ticker}")

    ticker = sec_edgar_service.get_ticker_for_company("Apple")
    print(f"   Apple → {ticker}")

    # Demo: Get company for ticker
    print("\n2. Company lookup:")
    company = sec_edgar_service.get_company_for_ticker("LMT")
    print(f"   LMT → {company}")

    # Demo: Get SEC filings
    print("\n3. SEC filings for LMT:")
    filings = sec_edgar_service.get_filings_for_ticker("LMT", limit=5)
    for f in filings[:3]:
        print(f"   - {f.get('form_type')}: {f.get('description', '')[:80]}")
        print(f"     Signal: {f.get('signal', {}).get('signal_strength')}")

    # Demo: Search companies
    print("\n4. Company search:")
    results = sec_edgar_service.search_companies("Martin", limit=5)
    for r in results:
        print(f"   - {r['company_name']} → {r['ticker']}")
