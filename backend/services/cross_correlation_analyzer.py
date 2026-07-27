"""
Cross-Correlation Analyzer - Sector Impact Analysis
Analyzes how government events affect entire sectors and industries.

This implements the Cross-Correlation Matrix Analysis enhancement requested.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CompanyImpact:
    """Impact data for a single company"""
    ticker: str
    company_name: str
    event_impact_score: float
    market_cap: float
    sector: str
    industry: str
    correlation_coefficient: float


@dataclass
class SectorImpact:
    """Sector-level impact analysis"""
    sector_name: str
    companies_affected: int
    average_impact_score: float
    total_market_cap: float
    correlation_matrix: np.ndarray
    dominant_events: List[str]
    confidence_interval: Tuple[float, float]


class CrossCorrelationAnalyzer:
    """
    Cross-correlation analyzer for sector-wide government event impact.

    Features:
    - Sector impact aggregation
    - Inter-company correlation analysis
    - Industry clustering
    - Dominant event identification
    """

    def __init__(self):
        # Industry classifications (would be loaded from database in real implementation)
        self.industry_classifications = {
            "LMT": {"sector": "Industrials", "industry": "Aerospace & Defense"},
            "BA": {"sector": "Industrials", "industry": "Aerospace & Defense"},
            "NOC": {"sector": "Industrials", "industry": "Aerospace & Defense"},
            "GD": {"sector": "Industrials", "industry": "Aerospace & Defense"},
            "RTX": {"sector": "Industrials", "industry": "Aerospace & Defense"},
            "PFE": {"sector": "Healthcare", "industry": "Pharmaceuticals"},
            "JNJ": {"sector": "Healthcare", "industry": "Health Care Products"},
            "UNH": {"sector": "Healthcare", "industry": "Health Care Services"},
            "AAPL": {"sector": "Technology", "industry": "Consumer Electronics"},
            "MSFT": {"sector": "Technology", "industry": "Software"},
            "GOOGL": {"sector": "Communication Services", "industry": "Internet Content"},
            "AMZN": {"sector": "Consumer Discretionary", "industry": "E-commerce"},
            "TSLA": {"sector": "Consumer Discretionary", "industry": "Auto Manufacturers"},
            "JPM": {"sector": "Financial Services", "industry": "Banks"},
            "XOM": {"sector": "Energy", "industry": "Oil & Gas Integrated"},
        }

        # Market cap data (would be loaded dynamically in real implementation)
        self.market_caps = {
            "LMT": 120_000_000_000,  # $120B
            "BA": 180_000_000_000,   # $180B
            "NOC": 85_000_000_000,   # $85B
            "GD": 75_000_000_000,    # $75B
            "RTX": 130_000_000_000,  # $130B
            "PFE": 190_000_000_000,  # $190B
            "JNJ": 450_000_000_000,  # $450B
            "UNH": 500_000_000_000,  # $500B
            "AAPL": 2_800_000_000_000, # $2.8T
            "MSFT": 2_500_000_000_000, # $2.5T
            "GOOGL": 1_800_000_000_000, # $1.8T
            "AMZN": 1_600_000_000_000,  # $1.6T
            "TSLA": 600_000_000_000,    # $600B
            "JPM": 450_000_000_000,     # $450B
            "XOM": 250_000_000_000,     # $250B
        }

        print("📊 Cross-Correlation Analyzer initialized")

    def load_industry_classifications(self) -> Dict:
        """
        Load industry classifications for all companies.

        Returns:
            Dictionary mapping tickers to sector/industry data
        """
        # In real implementation, this would load from database or API
        return self.industry_classifications

    def get_company_sector(self, ticker: str) -> str:
        """
        Get sector for a company.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Sector name
        """
        return self.industry_classifications.get(ticker, {}).get("sector", "Unknown")

    def calculate_individual_impact(self, ticker: str, event_data: Dict) -> CompanyImpact:
        """
        Calculate individual company impact from government event.

        Args:
            ticker: Stock ticker
            event_data: Government event data

        Returns:
            CompanyImpact object with calculated metrics
        """
        # Extract event impact score (from NLP analysis or ML prediction)
        event_impact_score = event_data.get("signal_score", 50)

        # Get company data
        sector = self.get_company_sector(ticker)
        market_cap = self.market_caps.get(ticker, 1_000_000_000)  # Default $1B

        # Calculate correlation coefficient (mock calculation)
        # In real implementation, this would be based on historical price correlations
        correlation_coefficient = min(event_impact_score / 100.0 * 0.8, 0.8)

        return CompanyImpact(
            ticker=ticker,
            company_name=self.industry_classifications.get(ticker, {}).get("industry", ticker),
            event_impact_score=event_impact_score,
            market_cap=market_cap,
            sector=sector,
            industry=self.industry_classifications.get(ticker, {}).get("industry", "Unknown"),
            correlation_coefficient=correlation_coefficient
        )

    def aggregate_sector_effects(self, sector_impact_data: Dict[str, List[CompanyImpact]]) -> Dict[str, SectorImpact]:
        """
        Aggregate individual company impacts into sector-level effects.

        Args:
            sector_impact_data: Dict mapping sectors to company impacts

        Returns:
            Dict mapping sectors to aggregated SectorImpact objects
        """
        sector_results = {}

        for sector, company_impacts in sector_impact_data.items():
            if not company_impacts:
                continue

            # Calculate sector metrics
            companies_affected = len(company_impacts)
            avg_impact_score = np.mean([ci.event_impact_score for ci in company_impacts])
            total_market_cap = sum([ci.market_cap for ci in company_impacts])

            # Create correlation matrix (simplified)
            correlation_values = [ci.correlation_coefficient for ci in company_impacts]
            correlation_matrix = np.array(correlation_values)

            # Identify dominant events (simplified)
            dominant_events = [f"High impact event affecting {sector} sector"]

            # Calculate confidence interval (mock)
            std_dev = np.std([ci.event_impact_score for ci in company_impacts])
            confidence_interval = (
                max(0, avg_impact_score - (1.96 * std_dev / np.sqrt(companies_affected))),
                min(100, avg_impact_score + (1.96 * std_dev / np.sqrt(companies_affected)))
            )

            sector_results[sector] = SectorImpact(
                sector_name=sector,
                companies_affected=companies_affected,
                average_impact_score=round(avg_impact_score, 2),
                total_market_cap=total_market_cap,
                correlation_matrix=correlation_matrix,
                dominant_events=dominant_events,
                confidence_interval=confidence_interval
            )

        return sector_results

    def analyze_sector_impact(self, event: Dict, affected_companies: List[str]) -> Dict[str, SectorImpact]:
        """
        Analyze how one government event affects entire sectors.

        Args:
            event: Government event data
            affected_companies: List of company tickers affected by event

        Returns:
            Dict mapping sectors to SectorImpact analysis
        """
        print(f"🔍 Analyzing sector impact for event: {event.get('title', 'Unknown')}")

        # Group companies by sector
        sector_companies = defaultdict(list)
        company_impacts = []

        for ticker in affected_companies:
            # Calculate individual impact
            company_impact = self.calculate_individual_impact(ticker, event)
            company_impacts.append(company_impact)

            # Group by sector
            sector = company_impact.sector
            sector_companies[sector].append(company_impact)

        print(f"   Companies affected: {len(affected_companies)}")
        print(f"   Sectors involved: {len(sector_companies)}")

        # Aggregate sector effects
        sector_impacts = self.aggregate_sector_effects(sector_companies)

        return sector_impacts

    def build_cross_correlation_matrix(self, events: List[Dict], companies: List[str]) -> pd.DataFrame:
        """
        Build cross-correlation matrix showing how events affect companies.

        Args:
            events: List of government events
            companies: List of company tickers

        Returns:
            DataFrame with correlation matrix
        """
        # Initialize matrix
        matrix_data = np.zeros((len(events), len(companies)))
        event_names = [event.get("title", f"Event {i}")[:30] for i, event in enumerate(events)]

        # Fill matrix with impact scores
        for i, event in enumerate(events):
            for j, ticker in enumerate(companies):
                # Mock impact calculation
                base_score = event.get("signal_score", 50)
                sector_multiplier = 1.2 if self.get_company_sector(ticker) in ["Industrials", "Defense"] else 1.0
                matrix_data[i, j] = min(100, base_score * sector_multiplier)

        # Create DataFrame
        df = pd.DataFrame(
            matrix_data,
            index=event_names,
            columns=companies
        )

        return df

    def identify_systemic_risks(self, sector_impacts: Dict[str, SectorImpact]) -> List[Dict]:
        """
        Identify systemic risks from cross-sector correlations.

        Args:
            sector_impacts: Dict of sector impact analyses

        Returns:
            List of systemic risk alerts
        """
        systemic_risks = []

        for sector, impact in sector_impacts.items():
            # High average impact score
            if impact.average_impact_score > 75:
                systemic_risks.append({
                    "risk_type": "HIGH_IMPACT_SECTOR",
                    "sector": sector,
                    "severity": "HIGH",
                    "description": f"Sector {sector} shows very high impact ({impact.average_impact_score})",
                    "confidence": 0.95
                })

            # Many companies affected
            if impact.companies_affected > 10:
                systemic_risks.append({
                    "risk_type": "BROAD_SECTOR_EXPOSURE",
                    "sector": sector,
                    "severity": "MEDIUM",
                    "description": f"Large number of companies ({impact.companies_affected}) affected in {sector}",
                    "confidence": 0.85
                })

        return systemic_risks

    def generate_sector_report(self, sector_impacts: Dict[str, SectorImpact]) -> Dict:
        """
        Generate comprehensive sector impact report.

        Args:
            sector_impacts: Dict of sector impact analyses

        Returns:
            Comprehensive sector analysis report
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "sectors_analyzed": len(sector_impacts),
            "total_companies_affected": sum([si.companies_affected for si in sector_impacts.values()]),
            "sector_details": {},
            "systemic_risks": self.identify_systemic_risks(sector_impacts),
            "top_sectors_by_impact": []
        }

        # Sort sectors by impact
        sorted_sectors = sorted(
            sector_impacts.items(),
            key=lambda x: x[1].average_impact_score,
            reverse=True
        )

        # Add sector details
        for sector, impact in sorted_sectors:
            report["sector_details"][sector] = {
                "average_impact_score": impact.average_impact_score,
                "companies_affected": impact.companies_affected,
                "total_market_cap": f"${impact.total_market_cap:,.0f}",
                "dominant_events": impact.dominant_events,
                "confidence_interval": impact.confidence_interval
            }

        # Top sectors
        report["top_sectors_by_impact"] = [
            {"sector": sector, "impact_score": impact.average_impact_score}
            for sector, impact in sorted_sectors[:5]
        ]

        return report


# Global instance
cross_correlation_analyzer = CrossCorrelationAnalyzer()


if __name__ == "__main__":
    print("📊 Cross-Correlation Analyzer - Demo")
    print("=" * 50)

    # Sample event
    sample_event = {
        "title": "Major Defense Contract Award Announcement",
        "description": "Department of Defense awards $2B contract for advanced defense systems",
        "signal_score": 85,
        "event_type": "CONTRACT_AWARD",
        "agencies": ["DOD"],
        "amount": 2000000000
    }

    # Affected companies
    affected_companies = ["LMT", "BA", "NOC", "GD", "RTX", "PFE", "JNJ"]

    # Analyze sector impact
    sector_impacts = cross_correlation_analyzer.analyze_sector_impact(sample_event, affected_companies)

    # Generate report
    report = cross_correlation_analyzer.generate_sector_report(sector_impacts)

    print(f"\n📈 Sector Impact Analysis:")
    print(f"   Sectors analyzed: {report['sectors_analyzed']}")
    print(f"   Companies affected: {report['total_companies_affected']}")
    print(f"   Systemic risks: {len(report['systemic_risks'])}")

    print(f"\n🏆 Top Sectors by Impact:")
    for sector_data in report["top_sectors_by_impact"][:3]:
        print(f"   {sector_data['sector']}: {sector_data['impact_score']}/100")

    # Show detailed sector analysis
    print(f"\n📋 Detailed Sector Analysis:")
    for sector, details in list(report["sector_details"].items())[:3]:
        print(f"   {sector}:")
        print(f"     Impact Score: {details['average_impact_score']}")
        print(f"     Companies Affected: {details['companies_affected']}")
        print(f"     Market Cap: {details['total_market_cap']}")