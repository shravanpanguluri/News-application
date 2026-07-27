"""
Training Data Collection System for Deep Financial Analysis
Collects user interactions, actual stock performance, and analysis outcomes
to continuously improve the deep analysis service predictions
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor


class AnalysisTrainingCollector:
    """
    Collects training data from deep analysis interactions to improve:
    - Overall rating accuracy
    - Valuation predictions
    - Risk assessments
    - Growth estimates
    - Bull/Bear debate outcomes
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent / "analysis_training_data"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.training_data_file = self.data_dir / "analysis_training.jsonl"
        self.feedback_file = self.data_dir / "user_feedback.jsonl"
        self.outcomes_file = self.data_dir / "stock_outcomes.jsonl"

        # Ensure files exist
        for f in [self.training_data_file, self.feedback_file, self.outcomes_file]:
            if not f.exists():
                f.touch()

    def record_analysis_request(self, ticker: str, analysis_result: Dict[str, Any]):
        """
        Record when a deep analysis is requested and its results

        Args:
            ticker: Stock ticker symbol
            analysis_result: Full analysis result from deep_analysis_service
        """
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "ticker": ticker,
                "overall_score": analysis_result.get("overall_rating", {}).get("overall_score"),
                "rating": analysis_result.get("overall_rating", {}).get("rating"),
                "component_scores": analysis_result.get("overall_rating", {}).get("component_scores"),
                "health_score": analysis_result.get("financial_breakdown", {}).get("health_score"),
                "risk_score": analysis_result.get("risk_analysis", {}).get("overall_risk_score"),
                "moat_rating": analysis_result.get("moat_analysis", {}).get("overall_moat_rating"),
                "growth_potential": analysis_result.get("growth_potential", {}).get("overall_growth_potential"),
                "bull_bear_verdict": analysis_result.get("bull_bear_debate", {}).get("verdict"),
                "bull_strength": analysis_result.get("bull_bear_debate", {}).get("bull_case", {}).get("strength_score"),
                "bear_strength": analysis_result.get("bull_bear_debate", {}).get("bear_case", {}).get("strength_score"),
                "dcf_upside": analysis_result.get("valuation_analysis", {}).get("valuation_metrics", {}).get("dcf_valuation", {}).get("upside_downside"),
                "event": "analysis_request"
            }

            self._append_jsonl(self.training_data_file, record)
            print(f"✓ Recorded analysis request for {ticker}")
        except Exception as e:
            print(f"⚠️ Failed to record analysis request: {e}")

    def record_user_feedback(self, ticker: str, feedback_type: str, feedback_data: Dict[str, Any]):
        """
        Record explicit user feedback on analysis quality

        Args:
            ticker: Stock ticker symbol
            feedback_type: 'thumbs_up', 'thumbs_down', 'rating', 'comment'
            feedback_data: Additional feedback data
        """
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "ticker": ticker,
                "feedback_type": feedback_type,
                "feedback_data": feedback_data,
                "event": "user_feedback"
            }

            self._append_jsonl(self.feedback_file, record)
            print(f"✓ Recorded user feedback for {ticker}: {feedback_type}")
        except Exception as e:
            print(f"⚠️ Failed to record user feedback: {e}")

    def collect_stock_outcome(self, ticker: str, days_after: int = 30):
        """
        Collect actual stock performance data after analysis was made

        Args:
            ticker: Stock ticker symbol
            days_after: Number of days after analysis to measure performance
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=f'{days_after}d')

            if hist.empty:
                return None

            # Calculate actual performance
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            price_change = (end_price - start_price) / start_price * 100
            high = hist['High'].max()
            low = hist['Low'].min()
            volatility = hist['Close'].pct_change().std() * np.sqrt(252) * 100
            volume = hist['Volume'].mean()

            record = {
                "timestamp": datetime.now().isoformat(),
                "ticker": ticker,
                "days_measured": days_after,
                "start_price": round(start_price, 2),
                "end_price": round(end_price, 2),
                "price_change_pct": round(price_change, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "volatility_annual": round(volatility, 2),
                "avg_volume": round(volume, 0),
                "actual_direction": "UP" if price_change > 0 else "DOWN",
                "event": "stock_outcome"
            }

            self._append_jsonl(self.outcomes_file, record)
            print(f"✓ Collected stock outcome for {ticker}: {price_change:.2f}% in {days_after}d")
            return record
        except Exception as e:
            print(f"⚠️ Failed to collect stock outcome for {ticker}: {e}")
            return None

    def collect_batch_outcomes(self, tickers: List[str], days_after: int = 30):
        """
        Collect outcomes for multiple tickers

        Args:
            tickers: List of ticker symbols
            days_after: Days after analysis to measure
        """
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.collect_stock_outcome, ticker, days_after) for ticker in tickers]
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)
        return results

    def get_training_dataset(self, min_samples: int = 50) -> Optional[pd.DataFrame]:
        """
        Load and prepare training dataset from collected data

        Args:
            min_samples: Minimum number of samples required

        Returns:
            DataFrame with features and labels, or None if insufficient data
        """
        try:
            # Load analysis requests
            analyses = self._load_jsonl(self.training_data_file)
            outcomes = self._load_jsonl(self.outcomes_file)
            feedback = self._load_jsonl(self.feedback_file)

            if len(analyses) < min_samples:
                print(f"⚠️ Insufficient training data: {len(analyses)}/{min_samples} samples")
                return None

            # Merge analyses with outcomes
            df_analyses = pd.DataFrame(analyses)
            df_outcomes = pd.DataFrame(outcomes)

            # Merge on ticker (simplified - in production would use analysis_id)
            if not df_outcomes.empty:
                df_merged = df_analyses.merge(
                    df_outcomes[['ticker', 'price_change_pct', 'actual_direction', 'volatility_annual']],
                    on='ticker',
                    how='inner',
                    suffixes=('', '_actual')
                )
            else:
                df_merged = df_analyses

            print(f"✓ Training dataset prepared: {len(df_merged)} samples, {len(df_merged.columns)} features")
            return df_merged
        except Exception as e:
            print(f"⚠️ Failed to prepare training dataset: {e}")
            return None

    def get_analysis_accuracy_stats(self) -> Dict[str, Any]:
        """
        Get statistics on analysis accuracy vs actual outcomes

        Returns:
            Dictionary with accuracy metrics
        """
        try:
            analyses = self._load_jsonl(self.training_data_file)
            outcomes = self._load_jsonl(self.outcomes_file)

            if not analyses or not outcomes:
                return {"status": "insufficient_data"}

            df_analyses = pd.DataFrame(analyses)
            df_outcomes = pd.DataFrame(outcomes)

            # Merge and calculate accuracy
            df_merged = df_analyses.merge(df_outcomes, on='ticker', how='inner')

            if df_merged.empty:
                return {"status": "no_matched_data"}

            # Direction prediction accuracy
            predicted_up = df_merged[df_merged['bull_bear_verdict'] == 'Bullish']
            actual_up = df_merged[df_merged['actual_direction'] == 'UP']

            correct_predictions = len(df_merged[
                (df_merged['bull_bear_verdict'] == 'Bullish') & (df_merged['actual_direction'] == 'UP') |
                (df_merged['bull_bear_verdict'] == 'Bearish') & (df_merged['actual_direction'] == 'DOWN')
            ])

            total_predictions = len(df_merged)
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0

            # Score vs actual performance correlation
            if 'overall_score' in df_merged.columns and 'price_change_pct' in df_merged.columns:
                correlation = df_merged['overall_score'].corr(df_merged['price_change_pct'])
            else:
                correlation = None

            return {
                "status": "success",
                "total_analyses": len(analyses),
                "matched_outcomes": len(df_merged),
                "direction_accuracy": round(accuracy, 3),
                "score_performance_correlation": round(correlation, 3) if correlation is not None else None,
                "avg_predicted_score": round(df_merged['overall_score'].mean(), 1) if 'overall_score' in df_merged.columns else None,
                "avg_actual_return": round(df_merged['price_change_pct'].mean(), 2) if 'price_change_pct' in df_merged.columns else None
            }
        except Exception as e:
            print(f"⚠️ Failed to calculate accuracy stats: {e}")
            return {"status": "error", "error": str(e)}

    def get_top_performing_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get analyses that were most accurate vs actual outcomes

        Args:
            limit: Number of top analyses to return

        Returns:
            List of top performing analysis records
        """
        try:
            dataset = self.get_training_dataset()
            if dataset is None or dataset.empty:
                return []

            # Calculate prediction error (absolute difference from actual)
            if 'overall_score' in dataset.columns and 'price_change_pct' in dataset.columns:
                dataset['prediction_error'] = abs(dataset['overall_score'] - dataset['price_change_pct'])
                top_analyses = dataset.nsmallest(limit, 'prediction_error')
                return top_analyses.to_dict('records')

            return []
        except Exception as e:
            print(f"⚠️ Failed to get top performing analyses: {e}")
            return []

    def export_training_data(self, output_path: Optional[str] = None) -> str:
        """
        Export all training data to CSV for external model training

        Args:
            output_path: Path to save CSV file

        Returns:
            Path to exported CSV file
        """
        try:
            if output_path is None:
                output_path = str(self.data_dir / "training_data_export.csv")

            dataset = self.get_training_dataset()
            if dataset is not None:
                dataset.to_csv(output_path, index=False)
                print(f"✓ Exported training data to {output_path}")
                return output_path
            else:
                print("⚠️ No training data to export")
                return ""
        except Exception as e:
            print(f"⚠️ Failed to export training data: {e}")
            return ""

    def get_data_collection_summary(self) -> Dict[str, Any]:
        """
        Get summary of all collected training data

        Returns:
            Dictionary with data collection statistics
        """
        try:
            analyses = self._load_jsonl(self.training_data_file)
            outcomes = self._load_jsonl(self.outcomes_file)
            feedback = self._load_jsonl(self.feedback_file)

            # Get unique tickers
            all_tickers = set()
            for record in analyses + outcomes + feedback:
                if 'ticker' in record:
                    all_tickers.add(record['ticker'])

            return {
                "total_analysis_requests": len(analyses),
                "total_stock_outcomes": len(outcomes),
                "total_user_feedback": len(feedback),
                "unique_tickers_tracked": len(all_tickers),
                "tickers": sorted(list(all_tickers)),
                "data_collection_started": self._get_first_record_date(),
                "last_updated": self._get_last_record_date()
            }
        except Exception as e:
            print(f"⚠️ Failed to get data collection summary: {e}")
            return {"error": str(e)}

    # ─── Private Helper Methods ───────────────────────────────────────────────

    def _append_jsonl(self, file_path: Path, record: Dict[str, Any]):
        """Append a record to a JSONL file"""
        with open(file_path, 'a') as f:
            f.write(json.dumps(record, default=str) + '\n')

    def _load_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load all records from a JSONL file"""
        records = []
        if file_path.exists():
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return records

    def _get_first_record_date(self) -> Optional[str]:
        """Get date of first recorded event"""
        for file_path in [self.training_data_file, self.feedback_file, self.outcomes_file]:
            records = self._load_jsonl(file_path)
            if records:
                return records[0].get('timestamp', 'Unknown')
        return None

    def _get_last_record_date(self) -> Optional[str]:
        """Get date of last recorded event"""
        last_date = None
        for file_path in [self.training_data_file, self.feedback_file, self.outcomes_file]:
            records = self._load_jsonl(file_path)
            if records:
                record_date = records[-1].get('timestamp')
                if record_date and (last_date is None or record_date > last_date):
                    last_date = record_date
        return last_date


# Singleton instance
analysis_training_collector = AnalysisTrainingCollector()
