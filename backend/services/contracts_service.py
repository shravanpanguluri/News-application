"""
USAspending.gov API Service - Federal Contract Data
FREE - No API key required
Provides: Federal contracts, grants, loans, and other awards
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime


class ContractsService:
    """Fetch federal contract data from USAspending.gov"""
    
    def __init__(self):
        self.base_url = "https://api.usaspending.gov/api/v2"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Predovex/1.0 (contact: info@predovex.io)"
        }
    
    def get_contracts(self, company_name: str, limit: int = 50) -> Dict:
        """
        Get federal contracts for a specific company

        Args:
            company_name: Company name (e.g., 'Lockheed Martin', 'Boeing')
            limit: Maximum number of results

        Returns:
            Dictionary with contract data
        """
        url = f"{self.base_url}/search/spending_by_award/"

        payload = {
            "filters": {
                "keywords": [company_name],
                "award_type_codes": ["A", "B", "C", "D"],  # Contracts only
                "time_period": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": datetime.now().strftime("%Y-%m-%d")
                    }
                ]
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Awarding Agency",
                "Start Date",
                "End Date",
                "Description",
                "NAICS Code",
                "PSC Code"
            ],
            "limit": limit,
            "sort": [
                {"Award Amount": "desc"}
            ]
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            contracts = []
            total_value = 0
            
            for contract in data.get('results', []):
                amount = contract.get('Award Amount') or 0
                total_value += amount
                
                contracts.append({
                    'award_id': contract.get('Award ID', 'N/A'),
                    'recipient': contract.get('Recipient Name', 'N/A'),
                    'agency': contract.get('Awarding Agency', {}).get('name', 'N/A') if isinstance(contract.get('Awarding Agency'), dict) else contract.get('Awarding Agency', 'N/A'),
                    'amount': amount,
                    'start_date': contract.get('Start Date', 'N/A'),
                    'end_date': contract.get('End Date', 'N/A'),
                    'description': contract.get('Description', '')[:200] if contract.get('Description') else 'N/A',
                    'naics_code': contract.get('NAICS Code', 'N/A'),
                    'psc_code': contract.get('PSC Code', 'N/A')
                })
            
            return {
                'company': company_name,
                'contract_count': len(contracts),
                'total_value': total_value,
                'average_contract': total_value / len(contracts) if contracts else 0,
                'contracts': contracts[:20],  # Return top 20
                'last_updated': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'company': company_name,
                'error': str(e),
                'contracts': []
            }
    
    def get_defense_contracts(self, limit: int = 50) -> Dict:
        """
        Get latest defense and national security contracts from multiple agencies
        Uses keyword searches to find contracts from different agencies

        Args:
            limit: Maximum number of results

        Returns:
            Dictionary with defense contract data
        """
        url = f"{self.base_url}/search/spending_by_award/"

        # Search keywords for different defense sectors
        defense_keywords = [
            ("Army", "Army contracts"),
            ("Navy", "Navy contracts"),
            ("Air Force", "Air Force contracts"),
            ("DARPA", "DARPA research"),
            ("NSA", "NSA security"),
            ("Missile Defense", "Missile defense"),
            ("Homeland Security", "DHS homeland"),
            ("FBI", "FBI justice"),
            ("Space Force", "Space Force"),
            ("Defense Logistics", "DLA logistics"),
        ]

        all_contracts = []
        seen_keys = set()

        for keyword, label in defense_keywords:
            try:
                payload = {
                    "filters": {
                        "keywords": [keyword],
                        "award_type_codes": ["A", "B", "C", "D"],
                        "time_period": [{
                            "start_date": "2024-01-01",
                            "end_date": "2026-12-31"
                        }]
                    },
                    "fields": [
                        "Recipient Name",
                        "Award Amount",
                        "Start Date",
                        "Awarding Agency",
                        "Description"
                    ],
                    "limit": max(10, limit // len(defense_keywords) + 2),
                }

                response = requests.post(url, json=payload, headers=self.headers, timeout=15)
                if response.ok:
                    data = response.json()
                    results = data.get('results', [])
                    if results:
                        print(f"✅ Fetched {len(results)} contracts for '{keyword}'")

                    for contract in results:
                        amount = contract.get('Award Amount') or 0
                        company = contract.get('Recipient Name', 'N/A')
                        start_date = contract.get('Start Date', 'N/A')
                        agency = contract.get('Awarding Agency', 'N/A')

                        # Deduplicate by company + amount + date
                        key = (company, amount, start_date)
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)

                        all_contracts.append({
                            'company': company,
                            'amount': amount,
                            'start_date': start_date,
                            'agency': agency if isinstance(agency, str) else 'Department of Defense',
                            'description': contract.get('Description', '')[:150] if contract.get('Description') else 'N/A'
                        })
                else:
                    print(f"⚠️ HTTP {response.status_code} for '{keyword}'")
            except Exception as e:
                print(f"⚠️ Error fetching '{keyword}': {e}")
                continue

        # Sort by amount and limit
        all_contracts.sort(key=lambda x: x['amount'], reverse=True)
        all_contracts = all_contracts[:limit]

        agencies_with_contracts = len(set(c['agency'] for c in all_contracts))
        print(f"📊 Total: {len(all_contracts)} unique contracts from {agencies_with_contracts} agencies")

        return {
            'agency': 'Defense & National Security Agencies',
            'contract_count': len(all_contracts),
            'total_value': sum(c['amount'] for c in all_contracts),
            'contracts': all_contracts,
            'period': 'Year to Date',
            'last_updated': datetime.now().isoformat()
        }

    def get_contracts_by_agency(self, agency_name: str, limit: int = 50) -> Dict:
        """
        Get contracts for a specific government agency

        Args:
            agency_name: Agency name (e.g., 'Department of Energy', 'NASA')
            limit: Maximum number of results

        Returns:
            Dictionary with agency contract data
        """
        # Agency ID mapping
        agency_ids = {
            'dod': 11,
            'defense': 11,
            'energy': 89,
            'doe': 89,
            'nasa': 80,
            'hhs': 75,
            'va': 87,
            'gsa': 47,
            'dot': 69,
            'epa': 68
        }

        agency_id = agency_ids.get(agency_name.lower(), 11)  # Default to DoD

        url = f"{self.base_url}/search/spending_by_award/"

        payload = {
            "filters": {
                "awarding_agency_id": agency_id,
                "award_type_codes": ["A", "B", "C", "D"],
                "time_period": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": datetime.now().strftime("%Y-%m-%d")
                    }
                ]
            },
            "fields": [
                "Recipient Name",
                "Award Amount",
                "Start Date",
                "Awarding Agency",
                "Description"
            ],
            "limit": limit,
            "sort": [
                {"Award Amount": "desc"}
            ]
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            contracts = []
            total_value = 0
            
            for contract in data.get('results', []):
                amount = contract.get('Award Amount') or 0
                total_value += amount
                
                contracts.append({
                    'company': contract.get('Recipient Name', 'N/A'),
                    'amount': amount,
                    'start_date': contract.get('Start Date', 'N/A'),
                    'agency': contract.get('Awarding Agency', {}).get('name', agency_name) if isinstance(contract.get('Awarding Agency'), dict) else agency_name,
                    'description': contract.get('Description', '')[:150] if contract.get('Description') else 'N/A'
                })
            
            return {
                'agency': agency_name,
                'agency_id': agency_id,
                'contract_count': len(contracts),
                'total_value': total_value,
                'contracts': contracts[:20],
                'last_updated': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'agency': agency_name,
                'error': str(e),
                'contracts': []
            }
    
    def get_top_contractors(self, limit: int = 20) -> Dict:
        """
        Get top government contractors by total award amount

        Args:
            limit: Number of top contractors to return

        Returns:
            Dictionary with top contractors
        """
        url = f"{self.base_url}/search/spending_by_award/"

        payload = {
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],
                "time_period": [
                    {
                        "start_date": "2025-01-01",
                        "end_date": datetime.now().strftime("%Y-%m-%d")
                    }
                ]
            },
            "aggregate_by": "recipient",
            "fields": [
                "Recipient Name",
                "Award Amount"
            ],
            "limit": limit,
            "sort": [
                {"Award Amount": "desc"}
            ]
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            contractors = []
            
            for contractor in data.get('results', []):
                contractors.append({
                    'rank': len(contractors) + 1,
                    'company': contractor.get('Recipient Name', 'N/A'),
                    'total_awards': contractor.get('Award Amount', 0),
                    'contract_count': contractor.get('Award Count', 1)
                })
            
            return {
                'period': '2026 YTD',
                'top_contractors': contractors,
                'last_updated': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'error': str(e),
                'contractors': []
            }


# Singleton instance
contracts_service = ContractsService()
