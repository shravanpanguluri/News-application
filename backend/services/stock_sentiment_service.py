"""
Stock Sentiment Service - Hugging Face Model Integration
Predicts next-day stock direction (Up/Down) using technical indicators
Model: jacobre20/stock-sentiment-daily-v1

Features:
- Trading Signal Generator (STRONG BUY/BUY/HOLD/SELL/STRONG SELL)
- Portfolio Optimization (ranked stock picks, model portfolios)
- Backtesting Engine (win rate, Sharpe ratio, drawdown analysis)
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
import yfinance as yf

try:
    from huggingface_hub import hf_hub_download
    import skops.io as sio
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
    print("⚠️  ML dependencies not installed. Run: pip install skops huggingface-hub scikit-learn pandas")


class StockSentimentService:
    """
    Stock Sentiment Prediction Service
    Uses ML model to predict next-day stock direction
    """
    
    def __init__(self):
        self.model = None
        self.feature_cols = None
        self._model_loaded = False
        self._load_failed = False
        
    def _load_model(self):
        """Load the sentiment model from Hugging Face"""
        if self._model_loaded or self._load_failed:
            return

        if not MODEL_AVAILABLE:
            self._load_failed = True
            print("❌ ML dependencies not available (skops/huggingface-hub not installed)")
            return

        try:
            print("📥 Loading stock sentiment model from Hugging Face...")
            print(f"   MODEL_AVAILABLE={MODEL_AVAILABLE}")
            # Download and load model
            model_path = hf_hub_download(
                repo_id="jacobre20/stock-sentiment-daily-v1",
                filename="model.skops"
            )
            print(f"📥 Model downloaded to: {model_path}")
            artifacts = sio.load(model_path)
            self.model = artifacts["model"]
            self.feature_cols = artifacts["feature_cols"]
            self._model_loaded = True
            print(f"✅ Stock sentiment model loaded successfully!")
            print(f"   Features: {self.feature_cols}")
        except Exception as e:
            print(f"❌ Failed to load sentiment model: {e}")
            import traceback
            traceback.print_exc()
            self._load_failed = True
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators required by the model
        Model expects: ret_1d, ret_5d, vol_5d, vol_20d, rsi14, macd, macd_signal, macd_hist, bb_pct, sma_ratio, spy_ret_1d
        """
        df = df.copy()
        
        # Returns (exactly as model expects)
        df['ret_1d'] = df['Close'].pct_change(1)
        df['ret_5d'] = df['Close'].pct_change(5)
        
        # Volatility (exactly as model expects)
        df['vol_5d'] = df['ret_1d'].rolling(5).std()
        df['vol_20d'] = df['ret_1d'].rolling(20).std()
        
        # RSI (14-day) - exactly as model expects
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi14'] = 100 - (100 / (1 + rs))
        
        # MACD - exactly as model expects
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands %B - exactly as model expects
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['std_20'] = df['Close'].rolling(20).std()
        df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
        df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
        df['bb_pct'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # SMA Ratio - exactly as model expects (20/50)
        df['sma_50'] = df['Close'].rolling(50).mean()
        df['sma_ratio'] = df['sma_20'] / df['sma_50']
        
        # SPY return (market benchmark) - exactly as model expects
        try:
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="6mo")
            spy_ret = spy_hist['Close'].pct_change(1)
            # Align SPY returns with our dataframe index
            df['spy_ret_1d'] = spy_ret.reindex(df.index, method='nearest').fillna(0).values
        except Exception as e:
            print(f"Warning: Could not fetch SPY data: {e}")
            df['spy_ret_1d'] = 0
        
        return df
    
    def _prepare_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Prepare feature matrix for model prediction
        """
        df = self._calculate_technical_indicators(df)
        
        # Drop NaN rows from rolling calculations
        df = df.dropna()
        
        if len(df) == 0:
            return None
            
        # Select only required features
        available_cols = [col for col in self.feature_cols if col in df.columns]
        missing_cols = set(self.feature_cols) - set(df.columns)
        
        if missing_cols:
            print(f"⚠️  Missing features: {missing_cols}")
        
        X = df[available_cols].tail(1)  # Use latest row
        return X
    
    def predict(self, ticker: str, period: str = "3mo") -> Optional[Dict[str, Any]]:
        """
        Predict next-day direction for a stock
        
        Args:
            ticker: Stock ticker symbol
            period: Historical data period (default: 3 months)
            
        Returns:
            Dictionary with prediction, probability, and metadata
        """
        print(f"📈 Starting prediction for {ticker} (period={period})")
        
        # Load model if needed
        if not self._model_loaded:
            self._load_model()
            
        if self._load_failed or self.model is None:
            print(f"🔄 ML model not available, using fallback for {ticker}")
            # Fallback to simple price-based sentiment
            return self._fallback_predict(ticker, period)
        
        try:
            # Fetch historical data with retry logic
            print(f"📥 Fetching {period} history for {ticker}...")
            stock = yf.Ticker(ticker)
            
            # Retry up to 3 times (yfinance can be flaky)
            df = None
            for attempt in range(3):
                try:
                    df = stock.history(period=period, timeout=30)
                    if df is not None and len(df) > 0:
                        print(f"📊 Received {len(df)} days of data for {ticker} (attempt {attempt + 1})")
                        break
                    else:
                        print(f"⚠️ Empty data for {ticker}, retry {attempt + 1}/3...")
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff
                except Exception as fetch_error:
                    print(f"⚠️ Fetch error for {ticker} (attempt {attempt + 1}/3): {fetch_error}")
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
            
            if df is None or df.empty:
                print(f"⚠️ No data found for {ticker} after 3 attempts, using fallback")
                return self._fallback_predict(ticker, period)
            
            # Prepare features
            X = self._prepare_features(df)
            if X is None or X.empty:
                print(f"⚠️ Could not prepare features for {ticker}, using fallback")
                return self._fallback_predict(ticker, period)
            
            # Make prediction
            proba = self.model.predict_proba(X.values)[0, 1]  # Probability of "Up"
            prediction = int(proba >= 0.5)
            
            # Get current price
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
            
            print(f"✅ ML prediction for {ticker}: {'Up' if prediction else 'Down'} ({proba:.2%})")

            # Generate trading signal
            signal = self._get_trading_signal(proba)
            signal_strength = self._get_signal_strength(proba)

            return {
                "ticker": ticker,
                "prediction": "Up" if prediction == 1 else "Down",
                "probability": round(float(proba), 4),
                "confidence": "High" if proba > 0.6 or proba < 0.4 else "Medium" if proba > 0.55 or proba < 0.45 else "Low",
                "trading_signal": signal,
                "signal_strength": round(signal_strength, 2),
                "current_price": round(float(current_price), 2),
                "previous_close": round(float(prev_close), 2),
                "daily_change": round(float(current_price - prev_close), 2),
                "daily_change_pct": round(float((current_price - prev_close) / prev_close * 100), 2),
                "prediction_date": datetime.now().strftime("%Y-%m-%d"),
                "target_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "model_version": "jacobre20/stock-sentiment-daily-v1",
                "disclaimer": "This is not financial advice. Model accuracy ~52%."
            }
            
        except Exception as e:
            print(f"❌ Prediction error for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_predict(ticker, period)
    
    def _fallback_predict(self, ticker: str, period: str = "3mo") -> Optional[Dict[str, Any]]:
        """
        Fallback prediction using simple price momentum
        Used when ML model is not available
        """
        try:
            # Use the shared market snapshot first. This keeps fallback
            # predictions fast and consistent with the live market ticker,
            # instead of starting a separate yfinance request per ticker.
            from services.market_data import market_data_service
            market = market_data_service.get_market_data()
            quote = next(
                (item for group in market.values() if isinstance(group, list)
                 for item in group if item.get('symbol') == ticker),
                None,
            )

            if quote and quote.get('price'):
                current_price = float(quote['price'])
                daily_change_pct = float(quote.get('change') or 0.0) / 100.0
                prev_close = current_price / (1 + daily_change_pct) if daily_change_pct > -0.99 else current_price
            else:
                # Last-resort lookup for symbols not in the shared snapshot.
                stock = yf.Ticker(ticker)
                df = stock.history(period=period, timeout=8)
                if df.empty:
                    return {"error": f"No data found for {ticker}"}
                current_price = float(df['Close'].iloc[-1])
                prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
                daily_change_pct = (current_price - prev_close) / prev_close

            # If stock is up today, predict up tomorrow (momentum)
            # Add some noise to probability to make it varied
            import random
            base_prob = 0.52 + (daily_change_pct * 0.1)  # Slight momentum bias
            proba = min(max(base_prob + random.uniform(-0.03, 0.03), 0.45), 0.58)

            prediction = "Up" if proba >= 0.5 else "Down"

            print(f"🔄 Fallback prediction for {ticker}: {prediction} ({proba:.2%})")

            return {
                "ticker": ticker,
                "prediction": prediction,
                "probability": round(proba, 4),
                "confidence": "Low",
                "current_price": round(current_price, 2),
                "previous_close": round(prev_close, 2),
                "daily_change": round(current_price - prev_close, 2),
                "daily_change_pct": round(daily_change_pct * 100, 2),
                "prediction_date": datetime.now().strftime("%Y-%m-%d"),
                "target_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "model_version": "fallback-momentum",
                "disclaimer": "This is not financial advice. Fallback prediction (ML model unavailable)."
            }
        except Exception as e:
            print(f"❌ Fallback prediction error for {ticker}: {e}")
            return {"error": str(e), "ticker": ticker}

    def _get_trading_signal(self, probability: float) -> str:
        """
        Generate trading signal based on probability thresholds
        
        Args:
            probability: Probability of positive next-day return (0-1)
            
        Returns:
            Trading signal: STRONG BUY, BUY, HOLD, SELL, or STRONG SELL
        """
        if probability > 0.65:
            return "STRONG BUY"
        elif probability > 0.55:
            return "BUY"
        elif probability < 0.35:
            return "STRONG SELL"
        elif probability < 0.45:
            return "SELL"
        else:
            return "HOLD"

    def _get_signal_strength(self, probability: float) -> float:
        """
        Calculate signal strength (0-100) based on confidence
        
        Args:
            probability: Probability of positive next-day return
            
        Returns:
            Signal strength percentage (higher = more confident)
        """
        if probability >= 0.5:
            # Bullish confidence
            return min((probability - 0.5) * 200, 100)
        else:
            # Bearish confidence
            return min((0.5 - probability) * 200, 100)
    
    def predict_batch(self, tickers: list) -> Dict[str, Any]:
        """
        Predict for multiple stocks (optimized with parallel fetching)

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with all predictions
        """
        import concurrent.futures
        
        print(f"📊 predict_batch called with {len(tickers)} tickers: {tickers}")
        print(f"📊 Model loaded: {self._model_loaded}, Failed: {self._load_failed}")

        results = []
        errors = []

        # Use ThreadPoolExecutor for parallel fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all predictions
            future_to_ticker = {executor.submit(self.predict, ticker, "3mo"): ticker
                               for ticker in tickers}

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_ticker):
                result = future.result()
                if result:
                    if "error" in result:
                        errors.append(f"{result.get('ticker', 'unknown')}: {result['error']}")
                        print(f"❌ Prediction error: {result}")
                    else:
                        results.append(result)

        print(f"✅ Batch complete: {len(results)} success, {len(errors)} errors")
        if errors:
            print(f"⚠️ Errors: {errors[:3]}")  # Show first 3 errors

        # Sort by probability (highest confidence first)
        results.sort(key=lambda x: abs(x['probability'] - 0.5), reverse=True)
        
        return {
            "predictions": results,
            "total": len(results),
            "bullish_count": len([r for r in results if r['prediction'] == "Up"]),
            "bearish_count": len([r for r in results if r['prediction'] == "Down"]),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_sector_sentiment(self, sector_stocks: Dict[str, list]) -> Dict[str, Any]:
        """
        Get sentiment by sector

        Args:
            sector_stocks: Dict mapping sector names to list of tickers

        Returns:
            Sector-level sentiment aggregation
        """
        sector_results = {}

        for sector, tickers in sector_stocks.items():
            predictions = []
            for ticker in tickers[:5]:  # Limit to 5 stocks per sector
                result = self.predict(ticker)
                if result and "error" not in result:
                    predictions.append(result)

            if predictions:
                avg_prob = np.mean([p['probability'] for p in predictions])
                sector_results[sector] = {
                    "sentiment": "Bullish" if avg_prob > 0.55 else "Bearish" if avg_prob < 0.45 else "Neutral",
                    "avg_probability": round(float(avg_prob), 4),
                    "stocks_analyzed": len(predictions),
                    "bullish_stocks": len([p for p in predictions if p['prediction'] == "Up"]),
                    "bearish_stocks": len([p for p in predictions if p['prediction'] == "Down"]),
                    "top_picks": sorted(predictions, key=lambda x: x['probability'], reverse=True)[:3]
                }

        return {
            "sectors": sector_results,
            "timestamp": datetime.now().isoformat()
        }

    def get_top_picks(self, tickers: List[str], limit: int = 10) -> Dict[str, Any]:
        """
        Get top stock picks ranked by probability and signal strength
        
        Args:
            tickers: List of ticker symbols to analyze
            limit: Number of top picks to return
            
        Returns:
            Ranked list of best investment opportunities
        """
        # Get predictions for all tickers
        batch_result = self.predict_batch(tickers)
        predictions = batch_result.get('predictions', [])
        
        # Separate bullish and bearish
        bullish = [p for p in predictions if p['prediction'] == 'Up']
        bearish = [p for p in predictions if p['prediction'] == 'Down']
        
        # Rank by probability (highest for bullish, lowest for bearish)
        bullish.sort(key=lambda x: x['probability'], reverse=True)
        bearish.sort(key=lambda x: x['probability'])
        
        # Get top picks
        top_bullish = bullish[:limit]
        top_bearish = bearish[:limit]
        
        # Add rank and signal strength
        for i, pick in enumerate(top_bullish):
            pick['rank'] = i + 1
            pick['signal'] = self._get_trading_signal(pick['probability'])
            pick['signal_strength'] = self._get_signal_strength(pick['probability'])
            
        for i, pick in enumerate(top_bearish):
            pick['rank'] = i + 1
            pick['signal'] = self._get_trading_signal(pick['probability'])
            pick['signal_strength'] = self._get_signal_strength(pick['probability'])
        
        return {
            "top_bullish_picks": top_bullish,
            "top_bearish_picks": top_bearish,
            "total_analyzed": len(predictions),
            "bullish_count": len(bullish),
            "bearish_count": len(bearish),
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "This is not financial advice. Model accuracy ~52%."
        }

    def get_model_portfolio(self, tickers: List[str], risk_profile: str = "balanced") -> Dict[str, Any]:
        """
        Generate model portfolio based on sentiment predictions
        
        Args:
            tickers: Universe of stocks to consider
            risk_profile: "conservative", "balanced", or "aggressive"
            
        Returns:
            Model portfolio with allocation percentages
        """
        # Get top picks
        picks_result = self.get_top_picks(tickers, limit=20)
        
        # Filter based on risk profile
        if risk_profile == "conservative":
            # Only high confidence signals
            min_strength = 60
            max_stocks = 5
        elif risk_profile == "aggressive":
            # Include medium confidence
            min_strength = 30
            max_stocks = 15
        else:  # balanced
            min_strength = 45
            max_stocks = 10
        
        # Filter bullish picks
        qualified_bullish = [
            p for p in picks_result['top_bullish_picks']
            if p.get('signal_strength', 0) >= min_strength
        ][:max_stocks]
        
        # Calculate allocations based on signal strength
        if not qualified_bullish:
            return {
                "portfolio": [],
                "total_allocation": 0,
                "cash_allocation": 100,
                "risk_profile": risk_profile,
                "message": "No qualified stocks found. Consider increasing cash position.",
                "timestamp": datetime.now().isoformat()
            }
        
        # Weight by signal strength
        total_strength = sum(p['signal_strength'] for p in qualified_bullish)
        portfolio = []
        
        for stock in qualified_bullish:
            allocation = (stock['signal_strength'] / total_strength) * 100
            portfolio.append({
                "ticker": stock['ticker'],
                "allocation": round(allocation, 2),
                "signal": stock['signal'],
                "probability": stock['probability'],
                "signal_strength": stock['signal_strength'],
                "current_price": stock['current_price'],
                "reasoning": f"{stock['signal']} with {stock['probability']:.1%} probability of upside"
            })
        
        # Sort by allocation
        portfolio.sort(key=lambda x: x['allocation'], reverse=True)
        
        # Cash allocation (remainder)
        total_allocated = sum(p['allocation'] for p in portfolio)
        cash_allocation = max(0, 100 - total_allocated)
        
        return {
            "portfolio": portfolio,
            "total_allocation": round(total_allocated, 2),
            "cash_allocation": round(cash_allocation, 2),
            "risk_profile": risk_profile,
            "expected_stocks": len(portfolio),
            "rebalance_frequency": "Daily (based on model predictions)",
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "This is not financial advice. Model accuracy ~52%. Past performance does not guarantee future results."
        }

    def backtest_strategy(self, tickers: List[str], days: int = 30, initial_capital: float = 10000) -> Dict[str, Any]:
        """
        Backtest trading strategy based on model predictions
        
        Args:
            tickers: List of stocks to test
            days: Number of days to backtest
            initial_capital: Starting capital
            
        Returns:
            Backtest results with performance metrics
        """
        print(f"📊 Starting backtest for {len(tickers)} stocks over {days} days...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 30)  # Extra data for calculations
        
        all_returns = []
        daily_portfolio_values = []
        trades = []
        
        # Fetch historical data for all tickers
        stock_data = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(start=start_date, end=end_date)
                if not df.empty:
                    stock_data[ticker] = df
            except Exception as e:
                print(f"⚠️ Could not fetch data for {ticker}: {e}")
        
        if not stock_data:
            return {"error": "No historical data available for backtesting"}
        
        # Simulate daily trading
        portfolio_value = initial_capital
        cash = initial_capital
        positions = {}
        
        for day_idx in range(days):
            current_date = end_date - timedelta(days=days - day_idx)
            
            # Skip if no data for this date
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Get predictions for this day (using data up to previous day)
            predictions = []
            for ticker, df in stock_data.items():
                if date_str in df.index or len(df) > day_idx:
                    # Use historical slice to simulate prediction
                    hist_df = df.iloc[:max(0, day_idx + 30)]
                    if len(hist_df) > 20:  # Need minimum data
                        try:
                            # Calculate technical indicators
                            hist_df = self._calculate_technical_indicators(hist_df.copy())
                            
                            if self.model is not None and self.feature_cols:
                                available_cols = [col for col in self.feature_cols if col in hist_df.columns]
                                X = hist_df[available_cols].tail(1)
                                if not X.empty:
                                    proba = self.model.predict_proba(X.values)[0, 1]
                                    predictions.append({
                                        'ticker': ticker,
                                        'probability': proba,
                                        'price': float(hist_df['Close'].iloc[-1])
                                    })
                        except Exception as e:
                            pass
            
            # Rebalance portfolio based on predictions
            # Close all positions
            for ticker, pos in positions.items():
                if ticker in stock_data:
                    close_price = float(stock_data[ticker].iloc[min(day_idx + 1, len(stock_data[ticker]) - 1)]['Close'])
                    pnl = (close_price - pos['entry_price']) * pos['shares']
                    cash += pos['shares'] * close_price
                    trades.append({
                        'date': date_str,
                        'ticker': ticker,
                        'type': 'SELL',
                        'shares': pos['shares'],
                        'price': close_price,
                        'pnl': pnl
                    })
            
            positions = {}
            
            # Open new positions based on top picks
            qualified = [p for p in predictions if p['probability'] > 0.55]
            qualified.sort(key=lambda x: x['probability'], reverse=True)
            
            if qualified and cash > 0:
                # Equal weight allocation
                allocation_per_stock = cash / min(len(qualified), 5)
                
                for pick in qualified[:5]:
                    if allocation_per_stock > 100:  # Minimum trade size
                        shares = int(allocation_per_stock / pick['price'])
                        if shares > 0:
                            cost = shares * pick['price']
                            cash -= cost
                            positions[pick['ticker']] = {
                                'shares': shares,
                                'entry_price': pick['price']
                            }
                            trades.append({
                                'date': date_str,
                                'ticker': pick['ticker'],
                                'type': 'BUY',
                                'shares': shares,
                                'price': pick['price'],
                                'cost': cost
                            })
            
            # Calculate portfolio value
            portfolio_value = cash
            for ticker, pos in positions.items():
                if ticker in stock_data and min(day_idx + 1, len(stock_data[ticker]) - 1) >= 0:
                    current_price = float(stock_data[ticker].iloc[min(day_idx + 1, len(stock_data[ticker]) - 1)]['Close'])
                    portfolio_value += pos['shares'] * current_price
            
            daily_portfolio_values.append({
                'date': date_str,
                'value': portfolio_value,
                'cash': cash,
                'positions_value': portfolio_value - cash
            })
        
        # Calculate performance metrics
        portfolio_values = [d['value'] for d in daily_portfolio_values]
        daily_returns = [(portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1] 
                        for i in range(1, len(portfolio_values))]
        
        # Total return
        total_return = (portfolio_values[-1] - initial_capital) / initial_capital * 100
        
        # Win rate (percentage of profitable days)
        profitable_days = len([r for r in daily_returns if r > 0])
        win_rate = profitable_days / len(daily_returns) * 100 if daily_returns else 0
        
        # Sharpe Ratio (annualized, assuming 252 trading days)
        if daily_returns:
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Maximum Drawdown
        peak = portfolio_values[0]
        max_drawdown = 0
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Compare to buy-and-hold (SPY as benchmark)
        try:
            spy = yf.Ticker("SPY")
            spy_df = spy.history(start=start_date, end=end_date)
            spy_return = (spy_df['Close'].iloc[-1] - spy_df['Close'].iloc[0]) / spy_df['Close'].iloc[0] * 100
        except:
            spy_return = 0
        
        return {
            "strategy": "ML Sentiment-Based Trading",
            "model": "jacobre20/stock-sentiment-daily-v1",
            "period": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d'),
                "days": days
            },
            "performance": {
                "initial_capital": initial_capital,
                "final_value": round(portfolio_values[-1], 2),
                "total_return_pct": round(total_return, 2),
                "total_profit_loss": round(portfolio_values[-1] - initial_capital, 2),
                "win_rate_pct": round(win_rate, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "benchmark_return_pct": round(spy_return, 2),
                "alpha": round(total_return - spy_return, 2)
            },
            "trading_activity": {
                "total_trades": len(trades),
                "buy_trades": len([t for t in trades if t['type'] == 'BUY']),
                "sell_trades": len([t for t in trades if t['type'] == 'SELL']),
                "sample_trades": trades[:10]  # First 10 trades
            },
            "portfolio_history": daily_portfolio_values,
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "This is not financial advice. Backtested performance does not guarantee future results. Model accuracy ~52%."
        }


# Singleton instance
stock_sentiment_service = StockSentimentService()


# Test function
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Stock Sentiment Service")
    print("=" * 60)
    
    # Test single prediction
    print("\n📊 Testing single stock prediction (AAPL)...")
    result = stock_sentiment_service.predict("AAPL")
    if result:
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Ticker: {result['ticker']}")
            print(f"Prediction: {result['prediction']}")
            print(f"Probability: {result['probability']:.2%}")
            print(f"Confidence: {result['confidence']}")
            print(f"Current Price: ${result['current_price']:.2f}")
            print(f"Daily Change: {result['daily_change_pct']:.2f}%")
    
    # Test batch prediction
    print("\n📊 Testing batch prediction...")
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM"]
    batch_result = stock_sentiment_service.predict_batch(tickers)
    
    if batch_result:
        print(f"\nTotal predictions: {batch_result['total']}")
        print(f"Bullish: {batch_result['bullish_count']} | Bearish: {batch_result['bearish_count']}")
        print("\nTop 3 predictions:")
        for pred in batch_result['predictions'][:3]:
            print(f"  {pred['ticker']}: {pred['prediction']} ({pred['probability']:.2%})")
