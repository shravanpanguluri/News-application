"""
Advanced Risk Models - Value-at-Risk and Stress Testing
Implements advanced risk management techniques for government event-driven portfolios.

This implements the Advanced Risk Models enhancement requested.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    var_95: float           # Value at Risk at 95% confidence
    var_99: float           # Value at Risk at 99% confidence
    expected_shortfall: float  # Conditional Value at Risk
    max_drawdown: float     # Maximum historical drawdown
    sharpe_ratio: float     # Risk-adjusted return ratio
    sortino_ratio: float    # Downside risk-adjusted ratio
    volatility: float       # Portfolio volatility
    beta: float            # Market sensitivity
    correlation_risk: float # Cross-asset correlation risk
    liquidity_risk: float   # Liquidity risk score
    regime_risk: float      # Market regime change risk
    timestamp: datetime


@dataclass
class StressTestScenario:
    """Stress test scenario definition"""
    name: str
    description: str
    shock_magnitude: float  # Percentage shock (-0.5 = 50% decline)
    duration: int          # Duration in days
    affected_assets: List[str]
    market_factors: Dict[str, float]  # Additional market factor shocks
    probability: float     # Likelihood of scenario (0-1)


@dataclass
class RegimeParameters:
    """Economic regime parameters"""
    regime_name: str
    expected_return: float
    volatility: float
    correlation_matrix: np.ndarray
    tail_risk: float      # Probability of extreme events
    recovery_time: int    # Days to recover from shocks


class AdvancedRiskModels:
    """
    Advanced risk models for government event-driven trading strategies.

    Features:
    - Value-at-Risk (VaR) calculations
    - Stress testing scenarios
    - Regime-switching risk models
    - Tail risk analysis
    - Liquidity risk assessment
    """

    def __init__(self):
        # Historical simulation parameters
        self.var_confidence_levels = [0.95, 0.99]
        self.lookback_period = 252  # 1 year of daily data

        # Stress test scenarios
        self.stress_scenarios = self._initialize_stress_scenarios()

        # Economic regimes
        self.regimes = self._initialize_regimes()

        print("🛡️  Advanced Risk Models initialized")

    def _initialize_stress_scenarios(self) -> List[StressTestScenario]:
        """Initialize predefined stress test scenarios"""
        return [
            StressTestScenario(
                name="2008_FINANCIAL_CRISIS",
                description="Global financial crisis with 50% market decline",
                shock_magnitude=-0.50,
                duration=90,
                affected_assets=["ALL"],
                market_factors={
                    "credit_spread": 3.0,  # 3x widening
                    "volatility": 2.5,     # 2.5x increase
                    "liquidity": 0.3       # 70% reduction
                },
                probability=0.05  # 5% chance per year
            ),
            StressTestScenario(
                name="COVID_PANIC",
                description="Pandemic-induced market panic with 35% decline",
                shock_magnitude=-0.35,
                duration=30,
                affected_assets=["ALL"],
                market_factors={
                    "volatility": 3.0,
                    "liquidity": 0.5,
                    "safe_haven_demand": 2.0
                },
                probability=0.03
            ),
            StressTestScenario(
                name="GEOPOLITICAL_SHOCK",
                description="Major geopolitical event causing defense sector surge",
                shock_magnitude={"defense": 0.30, "tech": -0.15, "consumer": -0.10},
                duration=14,
                affected_assets=["defense", "tech", "consumer"],
                market_factors={
                    "volatility": 1.8,
                    "safe_haven_demand": 1.5
                },
                probability=0.10
            ),
            StressTestScenario(
                name="RATE_HIKE_CYCLE",
                description="Aggressive interest rate hiking cycle",
                shock_magnitude=-0.20,
                duration=180,
                affected_assets=["financials", "reits"],
                market_factors={
                    "interest_rates": 2.0,  # 200bps increase
                    "credit_spread": 1.5,
                    "volatility": 1.3
                },
                probability=0.15
            )
        ]

    def _initialize_regimes(self) -> Dict[str, RegimeParameters]:
        """Initialize economic regime parameters"""
        return {
            "NORMAL": RegimeParameters(
                regime_name="NORMAL",
                expected_return=0.08,
                volatility=0.15,
                correlation_matrix=np.array([[1.0, 0.3, 0.2],
                                           [0.3, 1.0, 0.1],
                                           [0.2, 0.1, 1.0]]),
                tail_risk=0.05,
                recovery_time=30
            ),
            "BULL": RegimeParameters(
                regime_name="BULL",
                expected_return=0.15,
                volatility=0.20,
                correlation_matrix=np.array([[1.0, 0.6, 0.4],
                                           [0.6, 1.0, 0.3],
                                           [0.4, 0.3, 1.0]]),
                tail_risk=0.03,
                recovery_time=45
            ),
            "BEAR": RegimeParameters(
                regime_name="BEAR",
                expected_return=-0.10,
                volatility=0.30,
                correlation_matrix=np.array([[1.0, 0.8, 0.7],
                                           [0.8, 1.0, 0.6],
                                           [0.7, 0.6, 1.0]]),
                tail_risk=0.15,
                recovery_time=90
            ),
            "HIGH_VOLATILITY": RegimeParameters(
                regime_name="HIGH_VOLATILITY",
                expected_return=0.02,
                volatility=0.40,
                correlation_matrix=np.array([[1.0, 0.9, 0.8],
                                           [0.9, 1.0, 0.7],
                                           [0.8, 0.7, 1.0]]),
                tail_risk=0.20,
                recovery_time=60
            )
        }

    def calculate_var(self, portfolio_returns: List[float], confidence_level: float = 0.95) -> float:
        """
        Calculate Value-at-Risk using historical simulation method.

        Args:
            portfolio_returns: List of historical portfolio returns
            confidence_level: Confidence level for VaR (e.g., 0.95 for 95%)

        Returns:
            Value at Risk (negative return that will not be exceeded with given confidence)
        """
        if len(portfolio_returns) < 30:
            print("   ⚠️  Insufficient data for VaR calculation, using parametric method")
            return self._calculate_parametric_var(portfolio_returns, confidence_level)

        # Sort returns in ascending order (worst losses first)
        sorted_returns = np.sort(portfolio_returns)

        # Calculate percentile index
        percentile_index = int((1 - confidence_level) * len(sorted_returns))

        # VaR is the return at the percentile (negative for losses)
        var = sorted_returns[percentile_index]

        print(f"   📉 VaR at {confidence_level*100:.0f}%: {var:.2%}")
        return var

    def _calculate_parametric_var(self, returns: List[float], confidence_level: float) -> float:
        """Calculate parametric VaR when historical data is limited"""
        if not returns:
            return 0.0

        mean_return = np.mean(returns)
        std_dev = np.std(returns)

        # Inverse of standard normal distribution
        z_score = stats.norm.ppf(1 - confidence_level)

        # Parametric VaR
        var = mean_return - (z_score * std_dev)

        return var

    def calculate_expected_shortfall(self, portfolio_returns: List[float], confidence_level: float = 0.95) -> float:
        """
        Calculate Expected Shortfall (Conditional VaR).

        Args:
            portfolio_returns: List of historical portfolio returns
            confidence_level: Confidence level for ES

        Returns:
            Expected Shortfall
        """
        if len(portfolio_returns) < 30:
            print("   ⚠️  Insufficient data for Expected Shortfall calculation")
            return self.calculate_var(portfolio_returns, confidence_level)

        # Sort returns
        sorted_returns = np.sort(portfolio_returns)

        # Calculate VaR percentile index
        var_index = int((1 - confidence_level) * len(sorted_returns))

        # Expected Shortfall is average of returns worse than VaR
        es = np.mean(sorted_returns[:var_index])

        print(f"   📊 Expected Shortfall at {confidence_level*100:.0f}%: {es:.2%}")
        return es

    def calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """
        Calculate maximum drawdown from peak to trough.

        Args:
            portfolio_values: List of portfolio values over time

        Returns:
            Maximum drawdown as percentage
        """
        if len(portfolio_values) < 2:
            return 0.0

        peak = portfolio_values[0]
        max_dd = 0.0

        for value in portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        print(f"   📉 Maximum Drawdown: {max_dd:.2%}")
        return max_dd

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return).

        Args:
            returns: List of portfolio returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0

        # Annualize if daily returns
        if len(returns) > 250:  # Assume daily data
            annual_return = (1 + np.mean(returns)) ** 252 - 1
            annual_vol = np.std(returns) * np.sqrt(252)
        else:
            annual_return = np.mean(returns)
            annual_vol = np.std(returns)

        sharpe = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0

        print(f"   📈 Sharpe Ratio: {sharpe:.2f}")
        return sharpe

    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sortino ratio (downside risk-adjusted return).

        Args:
            returns: List of portfolio returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Sortino ratio
        """
        if len(returns) < 2:
            return 0.0

        # Calculate downside deviation
        negative_returns = [r for r in returns if r < risk_free_rate/252]  # Daily risk-free rate
        if not negative_returns:
            downside_dev = 0.0001  # Small positive value to avoid division by zero
        else:
            downside_dev = np.std(negative_returns) * np.sqrt(252)  # Annualized

        # Annualize return
        annual_return = (1 + np.mean(returns)) ** 252 - 1

        sortino = (annual_return - risk_free_rate) / downside_dev if downside_dev > 0 else 0

        print(f"   📊 Sortino Ratio: {sortino:.2f}")
        return sortino

    def stress_test_scenario(self, scenario: StressTestScenario,
                           portfolio: Dict[str, float],
                           current_market_conditions: Optional[Dict] = None) -> Dict:
        """
        Test portfolio against a specific stress scenario.

        Args:
            scenario: StressTestScenario to test
            portfolio: Dict mapping asset names to weights/values
            current_market_conditions: Current market conditions

        Returns:
            Stress test results
        """
        print(f"   🧪 Testing scenario: {scenario.name}")

        # Apply shock to affected assets
        stressed_portfolio = portfolio.copy()
        total_impact = 0.0

        for asset, weight in portfolio.items():
            if "ALL" in scenario.affected_assets or asset in scenario.affected_assets:
                if isinstance(scenario.shock_magnitude, dict):
                    # Asset-specific shock
                    shock = scenario.shock_magnitude.get(asset, scenario.shock_magnitude.get("ALL", 0))
                else:
                    shock = scenario.shock_magnitude

                impacted_value = weight * (1 + shock)
                stressed_portfolio[asset] = impacted_value
                impact = abs(weight * shock)
                total_impact += impact

        # Apply market factor shocks
        factor_impacts = {}
        for factor, shock in scenario.market_factors.items():
            factor_impacts[factor] = shock

        # Calculate portfolio-level impact
        original_value = sum(portfolio.values())
        stressed_value = sum(stressed_portfolio.values())
        portfolio_impact = (stressed_value - original_value) / original_value if original_value > 0 else 0

        # Expected loss considering probability
        expected_loss = portfolio_impact * scenario.probability

        result = {
            "scenario_name": scenario.name,
            "description": scenario.description,
            "portfolio_impact": portfolio_impact,
            "expected_loss": expected_loss,
            "total_dollar_impact": total_impact * original_value,
            "stressed_portfolio": stressed_portfolio,
            "market_factor_impacts": factor_impacts,
            "duration_days": scenario.duration,
            "probability": scenario.probability,
            "severity": self._classify_severity(abs(portfolio_impact))
        }

        print(f"      Portfolio Impact: {portfolio_impact:.2%}")
        print(f"      Expected Loss: {expected_loss:.2%}")
        print(f"      Severity: {result['severity']}")

        return result

    def regime_switching_risk(self, current_regime: str, transition_matrix: Optional[np.ndarray] = None) -> Dict:
        """
        Assess risk based on economic regime switching.

        Args:
            current_regime: Current economic regime
            transition_matrix: Matrix of regime transition probabilities

        Returns:
            Regime risk assessment
        """
        if transition_matrix is None:
            # Default transition matrix (simplified)
            transition_matrix = np.array([
                [0.9, 0.05, 0.03, 0.02],  # NORMAL transitions
                [0.1, 0.8, 0.08, 0.02],   # BULL transitions
                [0.2, 0.1, 0.6, 0.1],     # BEAR transitions
                [0.15, 0.05, 0.1, 0.7]    # HIGH_VOLATILITY transitions
            ])

        regime_names = ["NORMAL", "BULL", "BEAR", "HIGH_VOLATILITY"]
        current_index = regime_names.index(current_regime) if current_regime in regime_names else 0

        # Get transition probabilities
        transition_probs = transition_matrix[current_index]

        # Calculate expected risk across regimes
        expected_risk = 0.0
        risk_breakdown = {}

        for i, regime_name in enumerate(regime_names):
            regime_params = self.regimes[regime_name]
            probability = transition_probs[i]

            # Risk in this regime (simplified)
            regime_risk = regime_params.volatility * regime_params.tail_risk
            weighted_risk = regime_risk * probability

            expected_risk += weighted_risk
            risk_breakdown[regime_name] = {
                "probability": probability,
                "volatility": regime_params.volatility,
                "tail_risk": regime_params.tail_risk,
                "regime_risk": regime_risk,
                "weighted_risk": weighted_risk
            }

        # Most likely adverse regime
        adverse_regimes = ["BEAR", "HIGH_VOLATILITY"]
        adverse_probability = sum(risk_breakdown[r]["probability"] for r in adverse_regimes)

        return {
            "current_regime": current_regime,
            "expected_regime_risk": expected_risk,
            "adverse_regime_probability": adverse_probability,
            "risk_breakdown": risk_breakdown,
            "most_likely_regime": regime_names[np.argmax(transition_probs)],
            "regime_confidence": max(transition_probs)
        }

    def calculate_liquidity_risk(self, portfolio: Dict[str, float],
                               market_data: Dict[str, Dict]) -> float:
        """
        Calculate portfolio liquidity risk.

        Args:
            portfolio: Dict mapping assets to weights/values
            market_data: Dict with market data for each asset

        Returns:
            Liquidity risk score (0-100)
        """
        total_liquidity_score = 0.0
        total_weight = sum(portfolio.values())

        for asset, weight in portfolio.items():
            asset_data = market_data.get(asset, {})

            # Factors affecting liquidity
            bid_ask_spread = asset_data.get("bid_ask_spread", 0.01)  # 1% spread
            daily_volume = asset_data.get("daily_volume", 1000000)  # 1M shares
            market_cap = asset_data.get("market_cap", 10000000000)  # $10B

            # Normalize factors
            spread_factor = max(0, 1 - (bid_ask_spread / 0.05))  # 5% spread threshold
            volume_factor = min(1, daily_volume / 100000)  # 100K volume threshold
            cap_factor = min(1, market_cap / 1000000000)  # $1B cap threshold

            # Combined liquidity score (0-1)
            asset_liquidity = (spread_factor * 0.4 + volume_factor * 0.4 + cap_factor * 0.2)

            # Weight by portfolio allocation
            weighted_liquidity = asset_liquidity * (weight / total_weight)
            total_liquidity_score += weighted_liquidity

        # Convert to 0-100 scale
        liquidity_risk_score = (1 - total_liquidity_score) * 100

        print(f"   💧 Liquidity Risk Score: {liquidity_risk_score:.1f}/100")
        return liquidity_risk_score

    def calculate_correlation_risk(self, portfolio_returns: pd.DataFrame) -> float:
        """
        Calculate correlation risk across portfolio assets.

        Args:
            portfolio_returns: DataFrame with asset returns

        Returns:
            Correlation risk score (0-100)
        """
        if portfolio_returns.empty or len(portfolio_returns.columns) < 2:
            return 50.0  # Neutral risk

        # Calculate correlation matrix
        corr_matrix = portfolio_returns.corr()

        # Average pairwise correlation
        upper_triangle = corr_matrix.where(~np.tril(np.ones(corr_matrix.shape)).astype(bool))
        avg_correlation = upper_triangle.stack().mean()

        # Correlation risk score (higher correlation = higher risk)
        correlation_risk = avg_correlation * 100

        print(f"   🔗 Correlation Risk: {correlation_risk:.1f}/100")
        return correlation_risk

    def comprehensive_risk_assessment(self,
                                    portfolio: Dict[str, float],
                                    portfolio_returns: List[float],
                                    portfolio_values: List[float],
                                    market_data: Dict[str, Dict],
                                    current_regime: str = "NORMAL") -> RiskMetrics:
        """
        Perform comprehensive risk assessment combining all models.

        Args:
            portfolio: Dict mapping assets to weights/values
            portfolio_returns: List of portfolio returns
            portfolio_values: List of portfolio values
            market_data: Dict with market data for each asset
            current_regime: Current economic regime

        Returns:
            Comprehensive RiskMetrics
        """
        print("🛡️  Running comprehensive risk assessment...")

        # Calculate individual risk metrics
        var_95 = self.calculate_var(portfolio_returns, 0.95)
        var_99 = self.calculate_var(portfolio_returns, 0.99)
        expected_shortfall = self.calculate_expected_shortfall(portfolio_returns, 0.95)
        max_drawdown = self.calculate_max_drawdown(portfolio_values)
        sharpe_ratio = self.calculate_sharpe_ratio(portfolio_returns)
        sortino_ratio = self.calculate_sortino_ratio(portfolio_returns)
        volatility = np.std(portfolio_returns) * np.sqrt(252) if portfolio_returns else 0
        correlation_risk = self.calculate_correlation_risk(pd.DataFrame())
        liquidity_risk = self.calculate_liquidity_risk(portfolio, market_data)

        # Regime switching risk
        regime_analysis = self.regime_switching_risk(current_regime)
        regime_risk = regime_analysis["expected_regime_risk"] * 100

        # Beta (market sensitivity) - simplified
        beta = 1.0  # Would be calculated from market data in real implementation

        risk_metrics = RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            volatility=volatility,
            beta=beta,
            correlation_risk=correlation_risk,
            liquidity_risk=liquidity_risk,
            regime_risk=regime_risk,
            timestamp=datetime.utcnow()
        )

        return risk_metrics

    def run_stress_tests(self, portfolio: Dict[str, float]) -> List[Dict]:
        """
        Run all stress tests on portfolio.

        Args:
            portfolio: Dict mapping assets to weights/values

        Returns:
            List of stress test results
        """
        print("🧪 Running stress tests...")

        results = []
        for scenario in self.stress_scenarios:
            result = self.stress_test_scenario(scenario, portfolio)
            results.append(result)

        return results

    def _classify_severity(self, impact: float) -> str:
        """Classify impact severity"""
        if impact >= 0.20:
            return "SEVERE"
        elif impact >= 0.10:
            return "HIGH"
        elif impact >= 0.05:
            return "MODERATE"
        elif impact >= 0.02:
            return "LOW"
        else:
            return "MINIMAL"


# Global instance
advanced_risk_models = AdvancedRiskModels()


if __name__ == "__main__":
    print("🛡️  Advanced Risk Models - Demo")
    print("=" * 50)

    # Sample portfolio
    sample_portfolio = {
        "LMT": 0.30,    # 30% Lockheed Martin
        "BA": 0.20,     # 20% Boeing
        "NOC": 0.15,    # 15% Northrop Grumman
        "PFE": 0.20,    # 20% Pfizer
        "AAPL": 0.15    # 15% Apple
    }

    # Sample returns data (mock)
    np.random.seed(42)
    sample_returns = np.random.normal(0.001, 0.02, 252).tolist()  # 252 daily returns

    # Sample portfolio values
    initial_value = 1000000
    sample_values = [initial_value]
    for ret in sample_returns:
        sample_values.append(sample_values[-1] * (1 + ret))

    # Sample market data
    sample_market_data = {
        "LMT": {"bid_ask_spread": 0.005, "daily_volume": 2000000, "market_cap": 120000000000},
        "BA": {"bid_ask_spread": 0.008, "daily_volume": 1500000, "market_cap": 180000000000},
        "NOC": {"bid_ask_spread": 0.01, "daily_volume": 800000, "market_cap": 85000000000},
        "PFE": {"bid_ask_spread": 0.003, "daily_volume": 15000000, "market_cap": 190000000000},
        "AAPL": {"bid_ask_spread": 0.001, "daily_volume": 80000000, "market_cap": 2800000000000}
    }

    # Run comprehensive risk assessment
    risk_metrics = advanced_risk_models.comprehensive_risk_assessment(
        portfolio=sample_portfolio,
        portfolio_returns=sample_returns,
        portfolio_values=sample_values,
        market_data=sample_market_data,
        current_regime="NORMAL"
    )

    print(f"\n📊 Risk Assessment Results:")
    print(f"   VaR (95%): {risk_metrics.var_95:.2%}")
    print(f"   VaR (99%): {risk_metrics.var_99:.2%}")
    print(f"   Expected Shortfall: {risk_metrics.expected_shortfall:.2%}")
    print(f"   Max Drawdown: {risk_metrics.max_drawdown:.2%}")
    print(f"   Sharpe Ratio: {risk_metrics.sharpe_ratio:.2f}")
    print(f"   Sortino Ratio: {risk_metrics.sortino_ratio:.2f}")
    print(f"   Volatility: {risk_metrics.volatility:.2%}")
    print(f"   Correlation Risk: {risk_metrics.correlation_risk:.1f}/100")
    print(f"   Liquidity Risk: {risk_metrics.liquidity_risk:.1f}/100")
    print(f"   Regime Risk: {risk_metrics.regime_risk:.1f}/100")

    # Run stress tests
    stress_results = advanced_risk_models.run_stress_tests(sample_portfolio)

    print(f"\n🧪 Stress Test Results:")
    for result in stress_results[:2]:  # Show first 2 results
        print(f"   {result['scenario_name']}: {result['portfolio_impact']:.2%} impact")
        print(f"      Severity: {result['severity']}")
        print(f"      Expected Loss: {result['expected_loss']:.2%}")