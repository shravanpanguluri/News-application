"""
Stock Data Service - Real-time and historical stock prices
Uses yfinance (Yahoo Finance) - FREE, no API key required
"""
import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime


class StockDataService:
    """Fetch stock data using Yahoo Finance"""
    
    def get_stock_price(self, ticker: str) -> Dict:
        """
        Get current stock price and basic metrics
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL', 'TSLA')
        
        Returns:
            Dictionary with price, change, volume
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d')
            
            if data.empty:
                return {
                    'ticker': ticker,
                    'error': 'Stock not found or market closed'
                }
            
            current_price = data['Close'].iloc[-1]
            open_price = data['Open'].iloc[-1]
            change = current_price - open_price
            change_pct = (change / open_price) * 100 if open_price else 0
            
            return {
                'ticker': ticker,
                'price': round(current_price, 2),
                'change': round(change, 2),
                'change_percent': round(change_pct, 2),
                'volume': int(data['Volume'].iloc[-1]),
                'open': round(open_price, 2),
                'high': round(data['High'].iloc[-1], 2),
                'low': round(data['Low'].iloc[-1], 2),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'ticker': ticker,
                'error': str(e)
            }
    
    def get_stock_info(self, ticker: str) -> Dict:
        """
        Get company information and fundamentals
        
        Args:
            ticker: Stock symbol
        
        Returns:
            Dictionary with company info
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'ticker': ticker,
                'company_name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow'),
                'employees': info.get('fullTimeEmployees'),
                'website': info.get('website'),
                'description': info.get('longBusinessSummary', '')[:500]
            }
        except Exception as e:
            return {
                'ticker': ticker,
                'error': str(e)
            }
    
    def get_deep_dive(self, ticker: str) -> Dict:
        """Comprehensive stock data for deep dive: price, fundamentals, analyst consensus"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or info.get('quoteType') == 'NONE':
                return {'ticker': ticker, 'error': 'Ticker not found'}

            # ── Price ──
            price = float(info.get('currentPrice') or info.get('regularMarketPrice') or 0)
            prev  = float(info.get('previousClose') or info.get('regularMarketPreviousClose') or price)
            chg   = round(price - prev, 2)
            pct   = round((chg / prev * 100) if prev else 0, 2)

            # ── Format helpers ──
            def fmt_money(v, prefix='$'):
                if v is None: return 'N/A'
                v = float(v)
                if abs(v) >= 1e12: return f'{prefix}{v/1e12:.2f}T'
                if abs(v) >= 1e9:  return f'{prefix}{v/1e9:.2f}B'
                if abs(v) >= 1e6:  return f'{prefix}{v/1e6:.1f}M'
                return f'{prefix}{v:,.0f}'

            def fmt_pct(v):
                if v is None: return 'N/A'
                return f'{float(v)*100:.1f}%'

            def fmt_vol(v):
                if not v: return 'N/A'
                v = int(v)
                if v >= 1e9: return f'{v/1e9:.1f}B'
                if v >= 1e6: return f'{v/1e6:.1f}M'
                if v >= 1e3: return f'{v/1e3:.0f}K'
                return str(v)

            # ── Analyst consensus ──
            n  = int(info.get('numberOfAnalystOpinions') or 0)
            rm = float(info.get('recommendationMean') or 3)
            if n > 0:
                buy_frac  = max(0.0, min(1.0, (3.5 - rm) / 2.5))
                sell_frac = max(0.0, min(1.0, (rm - 2.5) / 2.5))
                buy  = max(0, round(n * buy_frac))
                sell = max(0, round(n * sell_frac))
                hold = max(0, n - buy - sell)
            else:
                buy = hold = sell = 0

            return {
                'ticker':      ticker.upper(),
                'name':        info.get('longName') or info.get('shortName') or ticker.upper(),
                'exchange':    info.get('exchange') or 'N/A',
                'sector':      info.get('sector') or 'N/A',
                'price':       round(price, 2),
                'change':      chg,
                'change_pct':  pct,
                'prev_close':  round(prev, 2),
                'open':        round(float(info.get('open') or info.get('regularMarketOpen') or price), 2),
                'high':        round(float(info.get('dayHigh') or info.get('regularMarketDayHigh') or price), 2),
                'low':         round(float(info.get('dayLow')  or info.get('regularMarketDayLow')  or price), 2),
                'volume':      fmt_vol(info.get('volume') or info.get('regularMarketVolume')),
                'market_cap':  fmt_money(info.get('marketCap')),
                'pe':          round(float(info.get('trailingPE')), 1) if info.get('trailingPE') else None,
                'eps':         round(float(info.get('trailingEps')), 2) if info.get('trailingEps') else None,
                'range_52_low':  info.get('fiftyTwoWeekLow'),
                'range_52_high': info.get('fiftyTwoWeekHigh'),
                'fundamentals': [
                    {'k': 'Revenue (TTM)',     'v': fmt_money(info.get('totalRevenue'))},
                    {'k': 'Gross Margin',      'v': fmt_pct(info.get('grossMargins'))},
                    {'k': 'Operating Margin',  'v': fmt_pct(info.get('operatingMargins'))},
                    {'k': 'Net Income',        'v': fmt_money(info.get('netIncomeToCommon'))},
                    {'k': 'Free Cash Flow',    'v': fmt_money(info.get('freeCashflow'))},
                    {'k': 'Debt / Equity',     'v': f"{float(info.get('debtToEquity')):.2f}" if info.get('debtToEquity') else 'N/A'},
                    {'k': 'ROE',               'v': fmt_pct(info.get('returnOnEquity'))},
                    {'k': 'P / B',             'v': f"{float(info.get('priceToBook')):.1f}" if info.get('priceToBook') else 'N/A'},
                ],
                'analysts': {
                    'buy':         buy,
                    'hold':        hold,
                    'sell':        sell,
                    'target':      round(float(info.get('targetMeanPrice')), 2) if info.get('targetMeanPrice') else None,
                    'target_low':  round(float(info.get('targetLowPrice')),  2) if info.get('targetLowPrice')  else None,
                    'target_high': round(float(info.get('targetHighPrice')), 2) if info.get('targetHighPrice') else None,
                },
                'description': (info.get('longBusinessSummary') or '')[:280],
            }
        except Exception as e:
            return {'ticker': ticker, 'error': str(e)}

    def get_historical_data(self, ticker: str, period: str = '1mo') -> Dict:
        """
        Get historical stock prices
        
        Args:
            ticker: Stock symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
        Returns:
            Dictionary with historical price data
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            
            historical = []
            for date, row in data.iterrows():
                historical.append({
                    'date': str(date.date()),
                    'open': round(row['Open'], 2),
                    'high': round(row['High'], 2),
                    'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2),
                    'volume': int(row['Volume'])
                })
            
            return {
                'ticker': ticker,
                'period': period,
                'data_points': len(historical),
                'data': historical
            }
        except Exception as e:
            return {
                'ticker': ticker,
                'error': str(e)
            }
    
    def get_multiple_stocks(self, tickers: List[str]) -> List[Dict]:
        """
        Get prices for multiple stocks at once
        
        Args:
            tickers: List of stock symbols
        
        Returns:
            List of price dictionaries
        """
        results = []
        for ticker in tickers:
            results.append(self.get_stock_price(ticker))
        return results
    
    def get_market_movers(self, category: str = 'technology') -> List[Dict]:
        """
        Get top stocks in a sector
        
        Args:
            category: Sector/category name
        
        Returns:
            List of stocks in that sector
        """
        # Pre-defined stock lists by sector
        sector_stocks = {
            'technology': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
            'defense': ['LMT', 'RTX', 'NOC', 'GD', 'BA', 'LHX'],
            'pharma': ['JNJ', 'PFE', 'MRK', 'ABBV', 'BMY', 'LLY'],
            'finance': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C'],
            'energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
            'crypto': ['COIN', 'MSTR', 'RIOT', 'MARA', 'CLSK']
        }
        
        tickers = sector_stocks.get(category.lower(), sector_stocks['technology'])
        return self.get_multiple_stocks(tickers)

    SCREENER_UNIVERSE = {
        'mega_cap':   ['AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','BRK-B','V','UNH','JPM','XOM','LLY','AVGO','MA'],
        'tech':       ['AMD','INTC','QCOM','TXN','CRM','ORCL','ADBE','NOW','AMAT','MU','NFLX','SNOW','PLTR','UBER','LYFT'],
        'finance':    ['BAC','GS','MS','WFC','C','BLK','AXP','SCHW','SPGI','COF','USB','PNC','TFC','AIG','MET'],
        'healthcare': ['JNJ','PFE','ABBV','MRK','ABT','TMO','DHR','AMGN','GILD','VRTX','REGN','BMY','MRNA','ZTS','HCA'],
        'energy':     ['XOM','CVX','COP','SLB','EOG','OXY','MPC','PSX','VLO','KMI','WMB','HAL','DVN','BKR','FANG'],
        'consumer':   ['WMT','COST','HD','MCD','NKE','SBUX','TGT','LOW','TJX','BKNG','MAR','HLT','YUM','DG','DLTR'],
        'etf':        ['SPY','QQQ','VTI','IWM','DIA','GLD','TLT','HYG','ARKK','SOXX','XLF','XLK','XLE','XLV','SCHD'],
    }

    def get_screener(self):
        """Batch-fetch live prices for the full screener universe."""
        all_tickers = []
        for tickers in self.SCREENER_UNIVERSE.values():
            for t in tickers:
                if t not in all_tickers:
                    all_tickers.append(t)
        try:
            raw = yf.download(
                all_tickers, period='2d', progress=False,
                threads=True, auto_adjust=True
            )
            close = raw.get('Close', raw)
            results = {}
            for cat, tickers in self.SCREENER_UNIVERSE.items():
                results[cat] = []
                for t in tickers:
                    try:
                        series = close[t].dropna() if t in close.columns else None
                        if series is not None and len(series) >= 2:
                            px  = round(float(series.iloc[-1]), 2)
                            prv = round(float(series.iloc[-2]), 2)
                            chg = round(px - prv, 2)
                            pct = round((chg / prv * 100) if prv else 0, 2)
                        elif series is not None and len(series) == 1:
                            px  = round(float(series.iloc[-1]), 2)
                            chg, pct = 0.0, 0.0
                        else:
                            px = chg = pct = None
                        results[cat].append({
                            'ticker': t,
                            'price':      px,
                            'change':     chg,
                            'change_pct': pct,
                        })
                    except Exception:
                        results[cat].append({'ticker': t, 'price': None, 'change': 0, 'change_pct': 0})
            return results
        except Exception as e:
            return {'error': str(e)}


# Singleton instance
stock_data_service = StockDataService()

