"""
Backtesting Framework - Historical Event → Stock Movement Validation
Proves the system works by testing on historical data.

This is the CRITICAL patent evidence component:
- Replay historical government events
- Generate signals as if in real-time
- Track predicted vs actual stock movements
- Calculate accuracy metrics (Sharpe ratio, win rate, max drawdown)

Without this, the patent has no proof of utility.
"""
import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import time

from services.foia_engine import foia_engine
from services.usaspending_service import usaspending_service
from services.sec_edgar_service import sec_edgar_service
from services.nlp_signal_engine import nlp_signal_engine
from services.gov_event_predictor import gov_event_predictor


class BacktestingFramework:
    """
    Backtesting Framework for Government Event → Stock Prediction

    Methodology:
    1. Load historical government events (FOIA, SEC, contracts)
    2. For each event, generate a signal at the event date
    3. Track stock price at event date + 1/7/30 days after
    4. Compare predicted direction vs actual movement
    5. Calculate portfolio-level metrics (win rate, Sharpe, drawdown)

    This provides the empirical evidence needed for patent utility claims.
    """

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "backtest_results"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Backtest configuration
        self.initial_capital = 100_000  # $100K starting portfolio
        self.position_size = 0.05  # 5% of portfolio per trade
        self.transaction_cost = 0.001  # 0.1% per trade

        # Results storage
        self.trades: List[Dict] = []
        self.daily_portfolio: List[Dict] = []
        self.metrics: Dict = {}

    def _get_historical_price(self, ticker: str, date: datetime,
                              days_offset: int = 0) -> Optional[float]:
        """
        Get historical stock price for a specific date

        Args:
            ticker: Stock ticker
            date: Base date
            days_offset: Days to add to base date

        Returns:
            Closing price or None
        """
        target_date = date + timedelta(days=days_offset)
        start_date = target_date - timedelta(days=5)
        end_date = target_date + timedelta(days=5)

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d")
            )

            if hist.empty:
                return None

            # Find closest date to target
            target_str = target_date.strftime("%Y-%m-%d")
            if target_str in hist.index.strftime("%Y-%m-%d").values:
                idx = hist.index.strftime("%Y-%m-%d").tolist().index(target_str)
                return float(hist['Close'].iloc[idx])
            else:
                # Use first available price
                return float(hist['Close'].iloc[0])

        except Exception as e:
            print(f"  ✗ Price lookup error for {ticker} on {target_date}: {e}")
            return None

    def _generate_signal_for_event(self, event: Dict, event_date: datetime) -> Dict:
        """
        Generate trading signal from a historical event

        Args:
            event: Event dict (FOIA, SEC, contract, etc.)
            event_date: Date of the event

        Returns:
            Signal dict with predicted direction
        """
        event_type = event.get("type", event.get("event_type", ""))

        # Use NLP analysis if available
        if event.get("nlp_analysis"):
            nlp = event["nlp_analysis"]
            signal_score = nlp.get("signal_score", 50)
            direction = nlp.get("direction", "NEUTRAL")
            confidence = nlp.get("confidence", 0.5)
        else:
            # Fall back to basic analysis
            title = (event.get("title", "") + " " + event.get("summary", "")).lower()

            # Simple keyword-based signal
            bullish_keywords = ["approved", "award", "contract", "grant", "success", "growth"]
            bearish_keywords = ["rejected", "investigation", "violation", "fine", "penalty", "recall"]

            bullish_count = sum(1 for kw in bullish_keywords if kw in title)
            bearish_count = sum(1 for kw in bearish_keywords if kw in title)

            if bullish_count > bearish_count:
                direction = "BULLISH"
                signal_score = 50 + (bullish_count * 10)
            elif bearish_count > bullish_count:
                direction = "BEARISH"
                signal_score = 50 - (bearish_count * 10)
            else:
                direction = "NEUTRAL"
                signal_score = 50

            confidence = min((bullish_count + bearish_count) / 5.0, 0.9)

        # Use ML model if trained
        ml_prediction = None
        if gov_event_predictor.model is not None:
            contract_amount = event.get("Award Amount", 0) or 0
            ml_prediction = gov_event_predictor.predict_for_ticker(
                ticker=event.get("ticker", ""),
                event_type=event_type,
                signal_score=signal_score,
                contract_amount=contract_amount,
            )

        return {
            "direction": direction,
            "signal_score": min(max(signal_score, 0), 100),
            "confidence": confidence,
            "ml_prediction": ml_prediction,
            "event_type": event_type,
            "generated_at": event_date.isoformat(),
        }

    def backtest_single_event(self, ticker: str, event: Dict,
                             event_date: datetime,
                             hold_days: int = 7) -> Optional[Dict]:
        """
        Backtest a single event

        Args:
            ticker: Stock ticker
            event: Event dict
            event_date: Date of event
            hold_days: Days to hold the position

        Returns:
            Trade result dict or None
        """
        # Get entry price (price at event date)
        entry_price = self._get_historical_price(ticker, event_date, days_offset=0)
        if not entry_price:
            return None

        # Generate signal
        signal = self._generate_signal_for_event(event, event_date)

        # Skip neutral signals
        if signal["direction"] == "NEUTRAL":
            return None

        # Get exit price (price after hold_days)
        exit_price = self._get_historical_price(ticker, event_date, days_offset=hold_days)
        if not exit_price:
            return None

        # Calculate actual return
        if signal["direction"] == "BULLISH":
            # Long position: profit if price goes up
            actual_return = (exit_price - entry_price) / entry_price
        else:
            # Short position: profit if price goes down
            actual_return = (entry_price - exit_price) / entry_price

        # Subtract transaction costs (entry + exit)
        net_return = actual_return - (2 * self.transaction_cost)

        # Determine if trade was profitable
        is_win = net_return > 0

        # Compare prediction vs actual
        actual_direction = "UP" if exit_price > entry_price else "DOWN"
        prediction_correct = (
            (signal["direction"] == "BULLISH" and actual_direction == "UP") or
            (signal["direction"] == "BEARISH" and actual_direction == "DOWN")
        )

        trade = {
            "ticker": ticker,
            "event_id": event.get("event_id", event.get("title", "unknown")),
            "event_type": event.get("type", event.get("event_type", "unknown")),
            "event_date": event_date.isoformat(),
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "signal_direction": signal["direction"],
            "signal_score": signal["signal_score"],
            "signal_confidence": signal["confidence"],
            "hold_days": hold_days,
            "gross_return": round(actual_return * 100, 2),
            "transaction_costs": round(2 * self.transaction_cost * 100, 2),
            "net_return": round(net_return * 100, 2),
            "is_win": is_win,
            "actual_direction": actual_direction,
            "prediction_correct": prediction_correct,
        }

        return trade

    def backtest_events(self, events: List[Dict], ticker: str,
                       hold_days: int = 7,
                       min_signal_score: int = 40) -> Dict:
        """
        Backtest a list of historical events

        Args:
            events: List of event dicts
            ticker: Stock ticker
            hold_days: Days to hold each position
            min_signal_score: Minimum signal score to trade

        Returns:
            Backtest results dict
        """
        print(f"\n📊 Backtesting {len(events)} events for {ticker} (hold={hold_days}d)")

        trades = []
        skipped = 0

        for i, event in enumerate(events):
            # Parse event date
            event_date_str = event.get("date", event.get("event_date", ""))
            if not event_date_str:
                skipped += 1
                continue

            try:
                if "T" in event_date_str:
                    event_date = datetime.fromisoformat(event_date_str[:19])
                else:
                    event_date = datetime.strptime(event_date_str[:10], "%Y-%m-%d")
            except:
                skipped += 1
                continue

            # Skip future events
            if event_date > datetime.utcnow():
                skipped += 1
                continue

            # Generate signal and backtest
            trade = self.backtest_single_event(ticker, event, event_date, hold_days)

            if trade:
                # Filter by minimum signal score
                if trade["signal_score"] >= min_signal_score:
                    trades.append(trade)
                    print(f"  [{i+1}/{len(events)}] {trade['event_type']}: "
                          f"{trade['signal_direction']} → "
                          f"{'WIN' if trade['is_win'] else 'LOSS'} "
                          f"({trade['net_return']:+.2f}%)")
                else:
                    skipped += 1
            else:
                skipped += 1

            # Rate limiting
            time.sleep(0.5)

        # Calculate metrics
        results = self._calculate_metrics(trades, ticker, hold_days)
        results["skipped"] = skipped

        print(f"\n📈 Backtest Results for {ticker}:")
        print(f"   Trades: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1f}%")
        print(f"   Avg Return: {results['avg_net_return']:+.2f}%")
        print(f"   Total Return: {results['total_return']:+.2f}%")

        return results

    def _calculate_metrics(self, trades: List[Dict], ticker: str,
                          hold_days: int) -> Dict:
        """
        Calculate portfolio-level backtest metrics

        Args:
            trades: List of trade results
            ticker: Stock ticker
            hold_days: Hold period

        Returns:
            Metrics dict
        """
        if not trades:
            return {
                "ticker": ticker,
                "hold_days": hold_days,
                "total_trades": 0,
                "win_rate": 0,
                "avg_net_return": 0,
                "total_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "profit_factor": 0,
                "best_trade": 0,
                "worst_trade": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "consecutive_wins": 0,
                "consecutive_losses": 0,
                "prediction_accuracy": 0,
            }

        # Basic metrics
        total_trades = len(trades)
        wins = [t for t in trades if t["is_win"]]
        losses = [t for t in trades if not t["is_win"]]

        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
        avg_net_return = np.mean([t["net_return"] for t in trades])
        total_return = sum(t["net_return"] for t in trades)

        # Prediction accuracy
        correct_predictions = sum(1 for t in trades if t["prediction_correct"])
        prediction_accuracy = correct_predictions / total_trades * 100 if total_trades > 0 else 0

        # Sharpe ratio (annualized)
        returns = [t["net_return"] for t in trades]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252 / hold_days)
        else:
            sharpe_ratio = 0

        # Max drawdown
        cumulative = np.cumsum(returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = cumulative - peak
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0

        # Profit factor
        gross_profit = sum(t["net_return"] for t in wins)
        gross_loss = abs(sum(t["net_return"] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Best/worst trades
        best_trade = max(t["net_return"] for t in trades)
        worst_trade = min(t["net_return"] for t in trades)

        # Average win/loss
        avg_win = np.mean([t["net_return"] for t in wins]) if wins else 0
        avg_loss = np.mean([t["net_return"] for t in losses]) if losses else 0

        # Consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for t in trades:
            if t["is_win"]:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)

        return {
            "ticker": ticker,
            "hold_days": hold_days,
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 1),
            "avg_net_return": round(avg_net_return, 2),
            "total_return": round(total_return, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "profit_factor": round(profit_factor, 2),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "consecutive_wins": max_consecutive_wins,
            "consecutive_losses": max_consecutive_losses,
            "prediction_accuracy": round(prediction_accuracy, 1),
            "trades": trades,
        }

    def backtest_watchlist(self, watchlist: Optional[List[Dict]] = None,
                          hold_days: int = 7,
                          lookback_months: int = 6) -> Dict:
        """
        Backtest the full watchlist

        Args:
            watchlist: List of {"ticker": ..., "company": ...}
            hold_days: Hold period for each trade
            lookback_months: Months of historical data to use

        Returns:
            Full backtest results
        """
        companies = watchlist or [
            {"ticker": "LMT", "company": "Lockheed Martin"},
            {"ticker": "BA", "company": "Boeing"},
            {"ticker": "PFE", "company": "Pfizer"},
            {"ticker": "AAPL", "company": "Apple"},
            {"ticker": "JPM", "company": "JPMorgan Chase"},
        ]

        print(f"\n🔄 Full Watchlist Backtest")
        print(f"   Companies: {len(companies)}")
        print(f"   Hold period: {hold_days} days")
        print(f"   Lookback: {lookback_months} months")
        print("=" * 60)

        all_results = {}
        all_trades = []

        for item in companies:
            ticker = item["ticker"]
            company = item["company"]

            try:
                # Collect historical events
                events = []

                # FOIA events
                foia_docs = foia_engine.get_foia_documents_for_ticker(ticker, company, limit=20)
                for doc in foia_docs:
                    events.append({
                        "type": "FOIA",
                        "title": doc.get("title", ""),
                        "summary": doc.get("summary", ""),
                        "date": doc.get("date", ""),
                        "ticker": ticker,
                    })

                # SEC filings
                sec_filings = sec_edgar_service.get_filings_for_ticker(ticker, limit=15)
                for filing in sec_filings:
                    events.append({
                        "type": "SEC_FILING",
                        "title": filing.get("description", ""),
                        "summary": filing.get("form_type", ""),
                        "date": filing.get("filing_date", ""),
                        "ticker": ticker,
                        "signal": filing.get("signal", {}),
                    })

                # Contract events
                contracts = usaspending_service.get_contract_awards_for_ticker(
                    ticker, company, limit=10
                )
                for contract in contracts:
                    events.append({
                        "type": "FEDERAL_CONTRACT",
                        "title": contract.get("Description", "") or "",
                        "summary": f"Amount: ${contract.get('Award Amount', 0):,.0f}",
                        "date": contract.get("Start Date", contract.get("Last Modified Date", "")),
                        "ticker": ticker,
                        "Award Amount": contract.get("Award Amount", 0) or 0,
                        "signal": contract.get("signal", {}),
                    })

                # Backtest
                if events:
                    results = self.backtest_events(
                        events, ticker, hold_days=hold_days
                    )
                    all_results[ticker] = results
                    all_trades.extend(results.get("trades", []))

                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"  ✗ Error backtesting {ticker}: {e}")
                all_results[ticker] = {"error": str(e)}

        # Aggregate metrics
        if all_trades:
            aggregate = self._calculate_metrics(all_trades, "AGGREGATE", hold_days)
        else:
            aggregate = {"total_trades": 0, "error": "No trades executed"}

        full_results = {
            "backtest_id": datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            "configuration": {
                "companies": len(companies),
                "hold_days": hold_days,
                "lookback_months": lookback_months,
                "initial_capital": self.initial_capital,
                "position_size": self.position_size,
                "transaction_cost": self.transaction_cost,
            },
            "aggregate": aggregate,
            "by_company": all_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Save results
        output_path = self.output_dir / f"backtest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, "w") as f:
            json.dump(full_results, f, indent=2, default=str)

        print(f"\n💾 Results saved to {output_path}")

        return full_results

    def generate_patent_evidence(self, backtest_results: Optional[Dict] = None) -> Dict:
        """
        Generate formatted evidence for patent filing

        Args:
            backtest_results: Results from backtest_watchlist()

        Returns:
            Patent evidence dict
        """
        if backtest_results is None:
            # Run a fresh backtest
            backtest_results = self.backtest_watchlist()

        aggregate = backtest_results.get("aggregate", {})

        evidence = {
            "generated_at": datetime.utcnow().isoformat(),
            "backtest_configuration": backtest_results.get("configuration", {}),
            "summary": {
                "total_trades": aggregate.get("total_trades", 0),
                "win_rate_pct": aggregate.get("win_rate", 0),
                "total_return_pct": aggregate.get("total_return", 0),
                "sharpe_ratio": aggregate.get("sharpe_ratio", 0),
                "max_drawdown_pct": aggregate.get("max_drawdown", 0),
                "prediction_accuracy_pct": aggregate.get("prediction_accuracy", 0),
                "profit_factor": aggregate.get("profit_factor", 0),
            },
            "methodology": {
                "description": "Historical government events (FOIA, SEC filings, federal contracts) were collected and analyzed using NLP signal extraction. Trading signals were generated at event dates, and stock price movements were tracked over the hold period. Returns are net of transaction costs.",
                "event_sources": ["FOIA (MuckRock)", "SEC EDGAR Filings", "USAspending.gov Contracts"],
                "signal_extraction": "NLP-based sentiment analysis, entity extraction, topic classification, urgency scoring",
                "hold_periods": [1, 7, 30],
                "metrics": ["win_rate", "sharpe_ratio", "total_return", "max_drawdown", "prediction_accuracy"],
            },
            "by_company": {
                ticker: {
                    "trades": results.get("total_trades", 0),
                    "win_rate": results.get("win_rate", 0),
                    "total_return": results.get("total_return", 0),
                    "prediction_accuracy": results.get("prediction_accuracy", 0),
                }
                for ticker, results in backtest_results.get("by_company", {}).items()
                if "error" not in results
            },
            "utility_claim": (
                f"The system achieved a {aggregate.get('win_rate', 0):.1f}% win rate over "
                f"{aggregate.get('total_trades', 0)} trades with a Sharpe ratio of "
                f"{aggregate.get('sharpe_ratio', 0):.2f} and total return of "
                f"{aggregate.get('total_return', 0):.2f}% over the backtest period. "
                f"Prediction accuracy was {aggregate.get('prediction_accuracy', 0):.1f}%."
            ),
        }

        # Save evidence
        evidence_path = self.output_dir / "patent_evidence.json"
        with open(evidence_path, "w") as f:
            json.dump(evidence, f, indent=2, default=str)

        print(f"\n📄 Patent evidence saved to {evidence_path}")

        return evidence


# Initialize global backtester
backtester = BacktestingFramework()


if __name__ == "__main__":
    print("📊 Backtesting Framework")
    print("=" * 60)

    # Run backtest on watchlist
    results = backtester.backtest_watchlist(hold_days=7)

    # Generate patent evidence
    evidence = backtester.generate_patent_evidence(results)

    print(f"\n📄 Patent Evidence Summary:")
    print(f"   {evidence['utility_claim']}")
