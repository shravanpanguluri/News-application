"""
Compliance Engine - Regulatory Compliance Checking
Ensures trades comply with SEC, FINRA, and other financial regulations.

This implements the Regulatory Compliance Engine enhancement requested.
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ComplianceStatus(Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    CONDITIONAL = "CONDITIONAL"


@dataclass
class ComplianceRule:
    """Regulatory compliance rule"""
    rule_id: str
    regulation: str  # SEC, FINRA, etc.
    description: str
    check_function: callable
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


@dataclass
class ComplianceCheck:
    """Individual compliance check result"""
    rule_id: str
    rule_description: str
    status: bool  # True = compliant, False = violation
    violation_details: Optional[str]
    severity: str
    timestamp: datetime


@dataclass
class TradingComplianceReport:
    """Complete compliance report for a trade"""
    compliance_status: ComplianceStatus
    regulatory_risks: List[ComplianceCheck]
    disclosure_requirements: List[str]
    trade_restrictions: List[str]
    monitoring_requirements: List[str]
    approval_timestamp: datetime
    reviewed_by: Optional[str]
    confidence_score: float  # 0-100 confidence in compliance assessment


class ComplianceEngine:
    """
    Regulatory compliance engine for government event-driven trading.

    Features:
    - SEC insider trading violation detection
    - Market manipulation pattern recognition
    - Disclosure timing verification
    - Cross-regulatory compliance checking
    """

    def __init__(self):
        self.regulations = self.load_regulatory_database()
        self.compliance_rules = self.initialize_compliance_rules()
        self.insider_trading_watchlist = set()  # Companies with recent insider trades
        self.disclosure_deadlines = {}  # Event-specific disclosure deadlines

        print("⚖️  Compliance Engine initialized")

    def load_regulatory_database(self) -> Dict:
        """
        Load regulatory database with key compliance requirements.

        Returns:
            Dict of regulations and requirements
        """
        # In real implementation, this would load from database
        return {
            "SEC_RULE_10b5": {
                "title": "SEC Rule 10b5-1 - Insider Trading Plans",
                "description": "Prohibits trading on material non-public information",
                "requirements": [
                    "No trading during blackout periods",
                    "Pre-established trading plans required",
                    "Material information disclosure obligations"
                ]
            },
            "SEC_RULE_16a": {
                "title": "SEC Section 16(a) - Beneficial Ownership Reporting",
                "description": "Insider trading reporting requirements",
                "requirements": [
                    "Form 4 filing within 2 business days",
                    "Disclosure of all transactions",
                    "Beneficial ownership thresholds"
                ]
            },
            "FINRA_RULE_5130": {
                "title": "FINRA Rule 5130 - New Issue Allocations",
                "description": "Restrictions on new issue allocations to restricted persons",
                "requirements": [
                    "No allocation to employees of participating members",
                    "No allocation to family members of employees",
                    "No allocation to finders or developers"
                ]
            },
            "SEC_MD_ACCESS": {
                "title": "SEC Market Data Access Rules",
                "description": "Fair access to market data and trading systems",
                "requirements": [
                    "Non-discriminatory access to market data",
                    "No preferential treatment in order execution",
                    "Transparency in pricing and fees"
                ]
            }
        }

    def initialize_compliance_rules(self) -> List[ComplianceRule]:
        """
        Initialize compliance rules for automated checking.

        Returns:
            List of ComplianceRule objects
        """
        rules = [
            ComplianceRule(
                rule_id="INSIDER_TRADING_CHECK",
                regulation="SEC",
                description="Check for insider trading violations",
                check_function=self.check_insider_trading_violation,
                severity="CRITICAL"
            ),
            ComplianceRule(
                rule_id="MARKET_MANIPULATION_CHECK",
                regulation="SEC",
                description="Check for market manipulation patterns",
                check_function=self.check_market_manipulation,
                severity="CRITICAL"
            ),
            ComplianceRule(
                rule_id="DISCLOSURE_TIMING_CHECK",
                regulation="SEC",
                description="Verify proper disclosure timing",
                check_function=self.check_disclosure_timing,
                severity="HIGH"
            ),
            ComplianceRule(
                rule_id="BLACKOUT_PERIOD_CHECK",
                regulation="SEC",
                description="Check for trading during blackout periods",
                check_function=self.check_blackout_periods,
                severity="HIGH"
            ),
            ComplianceRule(
                rule_id="MATERIAL_INFO_CHECK",
                regulation="SEC",
                description="Check for material non-public information usage",
                check_function=self.check_material_information,
                severity="CRITICAL"
            )
        ]

        return rules

    def check_insider_trading_violation(self, proposed_trade: Dict, event_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check for potential insider trading violations.

        Args:
            proposed_trade: Proposed trade details
            event_data: Government event data

        Returns:
            Tuple of (compliant: bool, violation_details: str)
        """
        ticker = proposed_trade.get("ticker", "")
        trade_date = proposed_trade.get("date", datetime.utcnow())
        trader_identity = proposed_trade.get("trader", "UNKNOWN")

        # Check if trader has access to material non-public information
        # This is a simplified check - real implementation would be more complex
        event_age_hours = (datetime.utcnow() - trade_date).total_seconds() / 3600

        # If event is very recent and trader is connected to the company
        if event_age_hours < 24 and self.is_connected_party(trader_identity, ticker):
            return False, f"Potential insider trading: Trade {event_age_hours:.1f} hours after event by connected party"

        # Check if there are recent insider trades on this company
        if ticker in self.insider_trading_watchlist:
            return False, f"Company {ticker} under insider trading scrutiny"

        return True, None

    def check_market_manipulation(self, proposed_trade: Dict, event_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check for market manipulation patterns.

        Args:
            proposed_trade: Proposed trade details
            event_data: Government event data

        Returns:
            Tuple of (compliant: bool, violation_details: str)
        """
        trade_size = proposed_trade.get("size", 0)
        ticker = proposed_trade.get("ticker", "")
        trade_price = proposed_trade.get("price", 0)

        # Check for unusually large trades around events
        average_volume = self.get_average_trading_volume(ticker)
        if trade_size > (average_volume * 10):  # 10x average volume
            return False, f"Unusually large trade ({trade_size:,} shares) vs average volume ({average_volume:,})"

        # Check for price manipulation patterns
        event_impact = event_data.get("signal_score", 50)
        if event_impact > 80 and trade_size > (average_volume * 5):
            return False, f"Possible price manipulation: High-impact event + large trade"

        return True, None

    def check_disclosure_timing(self, proposed_trade: Dict, event_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Verify proper disclosure timing.

        Args:
            proposed_trade: Proposed trade details
            event_data: Government event data

        Returns:
            Tuple of (compliant: bool, violation_details: str)
        """
        ticker = proposed_trade.get("ticker", "")
        trade_date = proposed_trade.get("date", datetime.utcnow())

        # Check if disclosure deadline has passed
        deadline = self.disclosure_deadlines.get(ticker)
        if deadline and trade_date < deadline:
            return False, f"Trade executed before required disclosure deadline: {deadline}"

        # Check if event information is public
        event_publication_date = event_data.get("publication_date", datetime.min)
        if trade_date < event_publication_date:
            return False, f"Trade executed before event was publicly disclosed"

        return True, None

    def check_blackout_periods(self, proposed_trade: Dict, event_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check for trading during blackout periods.

        Args:
            proposed_trade: Proposed trade details
            event_data: Government event data

        Returns:
            Tuple of (compliant: bool, violation_details: str)
        """
        ticker = proposed_trade.get("ticker", "")
        trade_date = proposed_trade.get("date", datetime.utcnow())

        # Check company-specific blackout periods
        blackout_periods = self.get_company_blackout_periods(ticker)
        for start_date, end_date in blackout_periods:
            if start_date <= trade_date <= end_date:
                return False, f"Trade executed during blackout period: {start_date} to {end_date}"

        # Check earnings blackout periods
        earnings_blackout = self.get_earnings_blackout_period(ticker)
        if earnings_blackout:
            start_date, end_date = earnings_blackout
            if start_date <= trade_date <= end_date:
                return False, f"Trade executed during earnings blackout period"

        return True, None

    def check_material_information(self, proposed_trade: Dict, event_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check for material non-public information usage.

        Args:
            proposed_trade: Proposed trade details
            event_data: Government event data

        Returns:
            Tuple of (compliant: bool, violation_details: str)
        """
        event_type = event_data.get("event_type", "")
        signal_score = event_data.get("signal_score", 0)
        event_public = event_data.get("public", True)

        # High-impact events that should be public
        if signal_score > 75 and not event_public:
            return False, f"Trading on high-impact non-public event (score: {signal_score})"

        # Specific event types requiring extra scrutiny
        sensitive_events = ["MERGER_ACQUISITION", "REGULATORY_ACTION", "LEGAL_LITIGATION"]
        if event_type in sensitive_events and not event_public:
            return False, f"Trading on sensitive {event_type} event before public disclosure"

        return True, None

    def is_connected_party(self, trader_identity: str, ticker: str) -> bool:
        """
        Check if trader is connected to the company (insider).

        Args:
            trader_identity: Trader identifier
            ticker: Stock ticker

        Returns:
            True if connected party
        """
        # Simplified check - real implementation would check against company insiders
        connected_parties = {
            "LMT": ["lockheed", "martin", "ceo", "cfo", "director"],
            "BA": ["boeing", "executive", "manager"],
            "PFE": ["pfizer", "pharma", "chief"],
        }

        company_keywords = connected_parties.get(ticker, [])
        trader_lower = trader_identity.lower()

        return any(keyword in trader_lower for keyword in company_keywords)

    def get_average_trading_volume(self, ticker: str) -> int:
        """
        Get average trading volume for a stock.

        Args:
            ticker: Stock ticker

        Returns:
            Average daily trading volume
        """
        # Mock implementation - real would fetch from market data
        volumes = {
            "LMT": 1_500_000,
            "BA": 2_000_000,
            "PFE": 8_000_000,
            "AAPL": 50_000_000,
            "MSFT": 30_000_000,
        }
        return volumes.get(ticker, 1_000_000)

    def get_company_blackout_periods(self, ticker: str) -> List[Tuple[datetime, datetime]]:
        """
        Get company blackout periods.

        Args:
            ticker: Stock ticker

        Returns:
            List of (start_date, end_date) tuples
        """
        # Mock implementation - real would fetch from company policies
        if ticker == "LMT":
            return [(datetime(2026, 3, 15), datetime(2026, 3, 22))]
        elif ticker == "PFE":
            return [(datetime(2026, 4, 1), datetime(2026, 4, 7))]
        return []

    def get_earnings_blackout_period(self, ticker: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Get earnings blackout period for a company.

        Args:
            ticker: Stock ticker

        Returns:
            (start_date, end_date) tuple or None
        """
        # Mock implementation
        earnings_dates = {
            "LMT": (datetime(2026, 4, 20), datetime(2026, 4, 27)),
            "PFE": (datetime(2026, 4, 25), datetime(2026, 5, 2)),
        }
        return earnings_dates.get(ticker)

    def check_trading_compliance(self, proposed_trade: Dict, event_data: Dict) -> TradingComplianceReport:
        """
        Ensure trades comply with SEC/FINRA regulations.

        Args:
            proposed_trade: Proposed trade details
            event_data: Government event data

        Returns:
            TradingComplianceReport with compliance status and requirements
        """
        print(f"⚖️  Checking compliance for {proposed_trade.get('ticker', 'UNKNOWN')} trade...")

        compliance_checks = []
        regulatory_risks = []
        disclosure_requirements = []
        trade_restrictions = []
        monitoring_requirements = []

        # Run all compliance rules
        for rule in self.compliance_rules:
            try:
                compliant, violation_details = rule.check_function(proposed_trade, event_data)

                check = ComplianceCheck(
                    rule_id=rule.rule_id,
                    rule_description=rule.description,
                    status=comppliant,
                    violation_details=violation_details,
                    severity=rule.severity,
                    timestamp=datetime.utcnow()
                )

                compliance_checks.append(check)

                if not compliant:
                    regulatory_risks.append(check)
                    print(f"   ❌ {rule.rule_id}: {violation_details}")
                else:
                    print(f"   ✅ {rule.rule_id}: Compliant")

            except Exception as e:
                print(f"   ⚠️  Error checking {rule.rule_id}: {e}")
                compliance_checks.append(ComplianceCheck(
                    rule_id=rule.rule_id,
                    rule_description=rule.description,
                    status=False,
                    violation_details=f"System error: {e}",
                    severity="HIGH",
                    timestamp=datetime.utcnow()
                ))

        # Determine overall compliance status
        critical_violations = [c for c in regulatory_risks if c.severity == "CRITICAL"]
        high_violations = [c for c in regulatory_risks if c.severity == "HIGH"]

        if critical_violations:
            compliance_status = ComplianceStatus.REJECTED
        elif high_violations:
            compliance_status = ComplianceStatus.PENDING_REVIEW
        elif regulatory_risks:
            compliance_status = ComplianceStatus.CONDITIONAL
        else:
            compliance_status = ComplianceStatus.APPROVED

        # Generate disclosure requirements
        if event_data.get("signal_score", 0) > 70:
            disclosure_requirements.append("Material event disclosure required within 4 hours")

        if proposed_trade.get("size", 0) > 100000:
            disclosure_requirements.append("Large trade reporting to exchanges")

        if proposed_trade.get("insider", False):
            disclosure_requirements.append("Form 4 filing required within 2 business days")

        # Generate trade restrictions
        if critical_violations:
            trade_restrictions.append("Trading prohibited pending investigation")
        elif high_violations:
            trade_restrictions.append("Trading requires supervisory approval")
        elif regulatory_risks:
            trade_restrictions.append("Enhanced monitoring required")

        # Generate monitoring requirements
        monitoring_requirements.append("Transaction surveillance for 30 days")
        if proposed_trade.get("insider", False):
            monitoring_requirements.append("Insider trading pattern monitoring")
        if event_data.get("event_type") in ["MERGER_ACQUISITION", "REGULATORY_ACTION"]:
            monitoring_requirements.append("Special event monitoring")

        # Calculate confidence score
        total_checks = len(compliance_checks)
        compliant_checks = len([c for c in compliance_checks if c.status])
        confidence_score = (compliant_checks / total_checks * 100) if total_checks > 0 else 100

        report = TradingComplianceReport(
            compliance_status=compliance_status,
            regulatory_risks=regulatory_risks,
            disclosure_requirements=disclosure_requirements,
            trade_restrictions=trade_restrictions,
            monitoring_requirements=monitoring_requirements,
            approval_timestamp=datetime.utcnow(),
            reviewed_by="ComplianceEngine",
            confidence_score=round(confidence_score, 1)
        )

        print(f"   📋 Compliance Status: {compliance_status.value}")
        print(f"   ⚠️  Regulatory Risks: {len(regulatory_risks)}")
        print(f"   💯 Confidence Score: {confidence_score:.1f}%")

        return report

    def add_to_insider_watchlist(self, ticker: str):
        """
        Add company to insider trading watchlist.

        Args:
            ticker: Stock ticker
        """
        self.insider_trading_watchlist.add(ticker)
        print(f"   👁️  Added {ticker} to insider trading watchlist")

    def set_disclosure_deadline(self, ticker: str, deadline: datetime):
        """
        Set disclosure deadline for a company.

        Args:
            ticker: Stock ticker
            deadline: Disclosure deadline
        """
        self.disclosure_deadlines[ticker] = deadline
        print(f"   📅 Set disclosure deadline for {ticker}: {deadline}")


# Global instance
compliance_engine = ComplianceEngine()


if __name__ == "__main__":
    print("⚖️  Compliance Engine - Demo")
    print("=" * 50)

    # Sample proposed trade
    sample_trade = {
        "ticker": "LMT",
        "size": 50000,
        "price": 450.00,
        "date": datetime.utcnow(),
        "trader": "Lockheed Martin Executive",
        "insider": True
    }

    # Sample government event
    sample_event = {
        "title": "Major Defense Contract Award",
        "description": "Department of Defense awards $2B contract",
        "signal_score": 85,
        "event_type": "CONTRACT_AWARD",
        "publication_date": datetime.utcnow() - timedelta(hours=2),
        "public": True
    }

    # Check compliance
    compliance_report = compliance_engine.check_trading_compliance(sample_trade, sample_event)

    print(f"\n📋 Compliance Report:")
    print(f"   Status: {compliance_report.compliance_status.value}")
    print(f"   Confidence: {compliance_report.confidence_score}%")
    print(f"   Regulatory Risks: {len(compliance_report.regulatory_risks)}")
    print(f"   Disclosure Requirements: {len(compliance_report.disclosure_requirements)}")
    print(f"   Trade Restrictions: {len(compliance_report.trade_restrictions)}")
    print(f"   Monitoring Requirements: {len(compliance_report.monitoring_requirements)}")