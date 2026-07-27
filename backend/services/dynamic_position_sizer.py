"""
Dynamic Position Sizing Algorithm - Optimal Position Calculation
Calculates optimal position sizes based on signal confidence, market volatility, and portfolio risk limits.

This implements the Dynamic Position Sizing Algorithm enhancement requested.
"""
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PositionMetrics:
    """Position sizing metrics"""
    optimal_size: float
    confidence_multiplier: float
    volatility_adjustment: float
    correlation_penalty: float
    risk_adjustment: float
    final_position_size: float
    rationale: List[str]


@dataclass
class MarketConditions:
    """Current market conditions affecting position sizing"""
    volatility: float  # Implied volatility or realized volatility
    market_regime: str  # BULL, BEAR, NEUTRAL, HIGH_VOLATILITY, LOW_VOLATILITY
    liquidity: float   # Market liquidity score 0-100
    correlation_regime: str  # HIGH_CORRELATION, LOW_CORRELATION
    economic_conditions: str  # EXPANSION, RECESSION, UNCERTAIN


class DynamicPositionSizer:
    """
    Dynamic position sizing algorithm for government event-driven trading.

    Features:
    - Confidence-based position adjustment
    - Volatility scaling
    - Correlation discounting
    - Portfolio risk management
    - Market regime adaptation
    """

    def __init__(self):
        # Base position sizing parameters
        self.base_position_size = 0.02  # 2% of portfolio per trade
        self.max_position_size = 0.10   # 10% maximum position size
        self.min_position_size = 0.005  # 0.5% minimum position size

        # Confidence multipliers
        self.confidence_multipliers = {
            "VERY_HIGH": 1.5,  # 90-100% confidence
            "HIGH": 1.2,       # 75-89% confidence
            "MEDIUM": 1.0,     # 50-74% confidence
            "LOW": 0.7,        # 25-49% confidence
            "VERY_LOW": 0.4    # 0-24% confidence
        }

        # Volatility adjustment factors
        self.volatility_adjustments = {
            "LOW": 1.2,        # Low volatility - increase position
            "MODERATE": 1.0,   # Moderate volatility - normal position
            "HIGH": 0.7,       # High volatility - reduce position
            "VERY_HIGH": 0.4   # Very high volatility - minimal position
        }

        # Correlation penalties
        self.correlation_penalties = {
            "LOW": 1.0,        # Low correlation - no penalty
            "MODERATE": 0.8,   # Moderate correlation - small penalty
            "HIGH": 0.6,       # High correlation - significant penalty
            "VERY_HIGH": 0.3   # Very high correlation - heavy penalty
        }

        print("📏 Dynamic Position Sizer initialized")

    def base_position_size(self) -> float:
        """
        Get base position size for trades.

        Returns:
            Base position size as fraction of portfolio (e.g., 0.02 = 2%)
        """
        return self.base_position_size

    def confidence_adjustment(self, signal_confidence: float) -> float:
        """
        Calculate confidence-based position adjustment.

        Args:
            signal_confidence: Signal confidence score (0-100)

        Returns:
            Confidence multiplier
        """
        if signal_confidence >= 90:
            confidence_level = "VERY_HIGH"
        elif signal_confidence >= 75:
            confidence_level = "HIGH"
        elif signal_confidence >= 50:
            confidence_level = "MEDIUM"
        elif signal_confidence >= 25:
            confidence_level = "LOW"
        else:
            confidence_level = "VERY_LOW"

        multiplier = self.confidence_multipliers[confidence_level]
        print(f"   🔮 Confidence adjustment: {confidence_level} ({signal_confidence}%) → {multiplier}x")

        return multiplier

    def volatility_scaling(self, market_volatility: float) -> float:
        """
        Scale position size based on market volatility.

        Args:
            market_volatility: Market volatility measure (e.g., VIX, realized volatility)

        Returns:
            Volatility adjustment factor
        """
        if market_volatility <= 15:
            volatility_regime = "LOW"
        elif market_volatility <= 25:
            volatility_regime = "MODERATE"
        elif market_volatility <= 40:
            volatility_regime = "HIGH"
        else:
            volatility_regime = "VERY_HIGH"

        adjustment = self.volatility_adjustments[volatility_regime]
        print(f"   📉 Volatility adjustment: {volatility_regime} ({market_volatility}) → {adjustment}x")

        return adjustment

    def correlation_discount(self, signal_history: List[Dict]) -> float:
        """
        Apply discount for correlated signals to avoid concentration risk.

        Args:
            signal_history: History of recent signals

        Returns:
            Correlation penalty factor
        """
        if not signal_history:
            print("   🔗 Correlation discount: No history → 1.0x")
            return 1.0

        # Calculate correlation based on recent signals
        recent_signals = signal_history[-10:]  # Last 10 signals
        if len(recent_signals) < 2:
            print("   🔗 Correlation discount: Insufficient history → 1.0x")
            return 1.0

        # Simple correlation measure - percentage of similar signals
        similar_count = 0
        total_count = len(recent_signals) - 1

        for i in range(1, len(recent_signals)):
            current = recent_signals[i]
            previous = recent_signals[i-1]

            # Check if signals are similar (same direction, similar confidence)
            if (current.get("direction") == previous.get("direction") and
                abs(current.get("confidence", 50) - previous.get("confidence", 50)) < 10):
                similar_count += 1

        correlation_ratio = similar_count / total_count if total_count > 0 else 0

        if correlation_ratio >= 0.8:
            correlation_level = "VERY_HIGH"
        elif correlation_ratio >= 0.6:
            correlation_level = "HIGH"
        elif correlation_ratio >= 0.3:
            correlation_level = "MODERATE"
        else:
            correlation_level = "LOW"

        penalty = self.correlation_penalties[correlation_level]
        print(f"   🔗 Correlation discount: {correlation_level} ({correlation_ratio:.2f}) → {penalty}x")

        return penalty

    def risk_adjustment(self, portfolio_risk_limits: Dict, current_exposure: float) -> float:
        """
        Adjust position size based on portfolio risk limits.

        Args:
            portfolio_risk_limits: Portfolio risk constraints
            current_exposure: Current portfolio exposure

        Returns:
            Risk adjustment factor
        """
        max_sector_exposure = portfolio_risk_limits.get("max_sector_exposure", 0.20)  # 20%
        max_single_stock_exposure = portfolio_risk_limits.get("max_single_stock", 0.05)  # 5%
        current_sector_exposure = portfolio_risk_limits.get("current_sector_exposure", 0.10)
        current_single_stock_exposure = current_exposure

        # Sector exposure penalty
        sector_utilization = current_sector_exposure / max_sector_exposure
        if sector_utilization >= 0.9:
            sector_penalty = 0.3
        elif sector_utilization >= 0.7:
            sector_penalty = 0.6
        elif sector_utilization >= 0.5:
            sector_penalty = 0.8
        else:
            sector_penalty = 1.0

        # Single stock exposure penalty
        stock_utilization = current_single_stock_exposure / max_single_stock_exposure
        if stock_utilization >= 0.9:
            stock_penalty = 0.2
        elif stock_utilization >= 0.7:
            stock_penalty = 0.5
        elif stock_utilization >= 0.5:
            stock_penalty = 0.8
        else:
            stock_penalty = 1.0

        risk_penalty = min(sector_penalty, stock_penalty)
        print(f"   ⚠️  Risk adjustment: Sector util {sector_utilization:.2f}, Stock util {stock_utilization:.2f} → {risk_penalty}x")

        return risk_penalty

    def market_regime_adjustment(self, market_conditions: MarketConditions) -> float:
        """
        Adjust position size based on current market regime.

        Args:
            market_conditions: Current market conditions

        Returns:
            Market regime adjustment factor
        """
        adjustments = []

        # Volatility regime adjustment
        if market_conditions.volatility > 30:
            adjustments.append(("High volatility", 0.6))
        elif market_conditions.volatility < 15:
            adjustments.append(("Low volatility", 1.2))

        # Market regime adjustment
        if market_conditions.market_regime == "BEAR":
            adjustments.append(("Bear market", 0.7))
        elif market_conditions.market_regime == "BULL":
            adjustments.append(("Bull market", 1.1))

        # Liquidity adjustment
        if market_conditions.liquidity < 30:
            adjustments.append(("Low liquidity", 0.8))

        # Economic conditions adjustment
        if market_conditions.economic_conditions == "RECESSION":
            adjustments.append(("Recession", 0.6))
        elif market_conditions.economic_conditions == "EXPANSION":
            adjustments.append(("Expansion", 1.1))

        # Calculate combined adjustment
        combined_adjustment = 1.0
        for reason, factor in adjustments:
            combined_adjustment *= factor

        if adjustments:
            reasons = ", ".join([f"{reason}({factor}x)" for reason, factor in adjustments])
            print(f"   🌐 Market regime adjustment: {reasons} → {combined_adjustment:.2f}x")
        else:
            print(f"   🌐 Market regime adjustment: Normal conditions → 1.0x")

        return combined_adjustment

    def calculate_optimal_position(self,
                                signal_confidence: float,
                                market_volatility: float,
                                portfolio_risk_limits: Dict,
                                current_exposure: float = 0.0,
                                signal_history: Optional[List[Dict]] = None,
                                market_conditions: Optional[MarketConditions] = None) -> PositionMetrics:
        """
        Calculate optimal position size based on multiple factors.

        Args:
            signal_confidence: Signal confidence score (0-100)
            market_volatility: Market volatility measure
            portfolio_risk_limits: Portfolio risk constraints
            current_exposure: Current position exposure
            signal_history: History of recent signals
            market_conditions: Current market conditions

        Returns:
            PositionMetrics with calculated position size and rationale
        """
        print(f"📏 Calculating optimal position size...")
        print(f"   Signal confidence: {signal_confidence}")
        print(f"   Market volatility: {market_volatility}")
        print(f"   Current exposure: {current_exposure:.2%}")

        rationale = []

        # Step 1: Base position size
        base_size = self.base_position_size()
        rationale.append(f"Base position: {base_size:.2%}")

        # Step 2: Confidence adjustment
        confidence_multiplier = self.confidence_adjustment(signal_confidence)
        rationale.append(f"Confidence multiplier: {confidence_multiplier:.2f}x")

        # Step 3: Volatility adjustment
        volatility_adjustment = self.volatility_scaling(market_volatility)
        rationale.append(f"Volatility adjustment: {volatility_adjustment:.2f}x")

        # Step 4: Correlation discount
        correlation_penalty = self.correlation_discount(signal_history or [])
        rationale.append(f"Correlation penalty: {correlation_penalty:.2f}x")

        # Step 5: Risk adjustment
        risk_adjustment = self.risk_adjustment(portfolio_risk_limits, current_exposure)
        rationale.append(f"Risk adjustment: {risk_adjustment:.2f}x")

        # Step 6: Market regime adjustment
        if market_conditions:
            regime_adjustment = self.market_regime_adjustment(market_conditions)
            rationale.append(f"Regime adjustment: {regime_adjustment:.2f}x")
        else:
            regime_adjustment = 1.0
            rationale.append("Regime adjustment: 1.0x (default)")

        # Calculate preliminary position size
        preliminary_size = (base_size * confidence_multiplier * volatility_adjustment *
                          correlation_penalty * risk_adjustment * regime_adjustment)

        # Apply final bounds
        optimal_size = max(self.min_position_size, min(self.max_position_size, preliminary_size))

        rationale.append(f"Final size: {optimal_size:.2%} (bounded {self.min_position_size:.2%}-{self.max_position_size:.2%})")

        print(f"   🎯 Optimal position size: {optimal_size:.2%}")

        return PositionMetrics(
            optimal_size=base_size,
            confidence_multiplier=confidence_multiplier,
            volatility_adjustment=volatility_adjustment,
            correlation_penalty=correlation_penalty,
            risk_adjustment=risk_adjustment,
            final_position_size=optimal_size,
            rationale=rationale
        )

    def position_size_to_shares(self, position_size: float, portfolio_value: float, stock_price: float) -> int:
        """
        Convert position size to number of shares.

        Args:
            position_size: Position size as fraction of portfolio
            portfolio_value: Total portfolio value
            stock_price: Current stock price

        Returns:
            Number of shares to trade
        """
        dollar_amount = position_size * portfolio_value
        shares = int(dollar_amount / stock_price)
        return shares

    def get_position_recommendation(self, metrics: PositionMetrics, ticker: str) -> Dict:
        """
        Generate human-readable position recommendation.

        Args:
            metrics: PositionMetrics from calculate_optimal_position
            ticker: Stock ticker symbol

        Returns:
            Position recommendation dict
        """
        recommendation = {
            "ticker": ticker,
            "recommended_position_size": metrics.final_position_size,
            "shares_to_trade": 0,  # Will be calculated when portfolio value known
            "confidence_level": self._get_confidence_label(metrics.confidence_multiplier),
            "risk_level": self._get_risk_level(metrics.final_position_size),
            "rationale": metrics.rationale,
            "calculation_timestamp": datetime.utcnow().isoformat()
        }

        return recommendation

    def _get_confidence_label(self, confidence_multiplier: float) -> str:
        """Convert confidence multiplier to descriptive label"""
        if confidence_multiplier >= 1.3:
            return "HIGH"
        elif confidence_multiplier >= 1.0:
            return "MODERATE"
        elif confidence_multiplier >= 0.7:
            return "LOW"
        else:
            return "VERY_LOW"

    def _get_risk_level(self, position_size: float) -> str:
        """Convert position size to risk level"""
        if position_size >= 0.08:
            return "HIGH"
        elif position_size >= 0.04:
            return "MODERATE"
        elif position_size >= 0.02:
            return "LOW"
        else:
            return "VERY_LOW"


# Global instance
dynamic_position_sizer = DynamicPositionSizer()


if __name__ == "__main__":
    print("📏 Dynamic Position Sizer - Demo")
    print("=" * 50)

    # Sample inputs
    sample_confidence = 85.0  # 85% confidence
    sample_volatility = 22.5  # Moderate volatility
    sample_portfolio_limits = {
        "max_sector_exposure": 0.20,
        "max_single_stock": 0.05,
        "current_sector_exposure": 0.12
    }
    sample_current_exposure = 0.03  # 3% current exposure

    # Sample signal history
    sample_signal_history = [
        {"direction": "BULLISH", "confidence": 80},
        {"direction": "BULLISH", "confidence": 85},
        {"direction": "BEARISH", "confidence": 70},
        {"direction": "BULLISH", "confidence": 90},
        {"direction": "BULLISH", "confidence": 88},
    ]

    # Sample market conditions
    sample_market_conditions = MarketConditions(
        volatility=22.5,
        market_regime="NEUTRAL",
        liquidity=75.0,
        correlation_regime="MODERATE",
        economic_conditions="EXPANSION"
    )

    # Calculate optimal position
    position_metrics = dynamic_position_sizer.calculate_optimal_position(
        signal_confidence=sample_confidence,
        market_volatility=sample_volatility,
        portfolio_risk_limits=sample_portfolio_limits,
        current_exposure=sample_current_exposure,
        signal_history=sample_signal_history,
        market_conditions=sample_market_conditions
    )

    # Generate recommendation
    recommendation = dynamic_position_sizer.get_position_recommendation(position_metrics, "LMT")

    print(f"\n📊 Position Recommendation:")
    print(f"   Ticker: {recommendation['ticker']}")
    print(f"   Recommended Size: {recommendation['recommended_position_size']:.2%}")
    print(f"   Confidence Level: {recommendation['confidence_level']}")
    print(f"   Risk Level: {recommendation['risk_level']}")
    print(f"   Rationale: {'; '.join(recommendation['rationale'][-3:])}")  # Show last 3 reasons

    # Calculate shares for sample portfolio
    portfolio_value = 1000000  # $1M portfolio
    stock_price = 450.00  # $450 per share
    shares = dynamic_position_sizer.position_size_to_shares(
        recommendation['recommended_position_size'],
        portfolio_value,
        stock_price
    )
    print(f"   Shares to trade: {shares:,} (${shares * stock_price:,.0f})")