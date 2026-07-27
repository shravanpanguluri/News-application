"""
FRED API Service - Federal Reserve Economic Data
FREE API key from https://fred.stlouisfed.org/docs/api/api_key.html
Provides: Interest rates, GDP, inflation, unemployment, and more
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os


class FREDService:
    """Fetch economic indicators from Federal Reserve (FRED)"""
    
    def __init__(self):
        # Get free API key: https://fred.stlouisfed.org/docs/api/api_key.html
        self.api_key = os.getenv('FRED_API_KEY', '')
        self.base_url = "https://api.stlouisfed.org/fred"
        
        # Common economic indicator series IDs
        self.series_ids = {
            'interest_rate': 'DFF',              # Federal Funds Rate
            'gdp': 'GDP',                        # Gross Domestic Product
            'cpi': 'CPIAUCSL',                   # Consumer Price Index (Inflation)
            'unemployment': 'UNRATE',            # Unemployment Rate
            'treasury_10y': 'DGS10',             # 10-Year Treasury Rate
            'treasury_2y': 'DGS2',               # 2-Year Treasury Rate
            'treasury_3m': 'DGS3MO',             # 3-Month Treasury Bill
            'sp500': 'SP500',                    # S&P 500 Index
            'recession': 'USREC',                # US Recession Indicator
            'consumer_sentiment': 'UMCSENT',     # Consumer Sentiment
            'initial_claims': 'INITIALCLAIMS',   # Initial Jobless Claims
            'ppi': 'PPIFGS',                     # Producer Price Index
            'retail_sales': 'RSAFS',             # Retail Sales
            'industrial_production': 'INDPRO',   # Industrial Production
            'housing_starts': 'HOUST',           # Housing Starts
            'crude_oil_price': 'DCOILWTICO',     # Crude Oil Prices
            'gold_price': 'GOLDPMGBD228NLBM',    # Gold Fixing Price
            'm2_money_stock': 'M2SL',            # M2 Money Stock
            'yield_curve': 'T10Y2Y',             # 10Y-2Y Treasury Spread
        }
    
    def get_series(self, series_id: str) -> Dict:
        """
        Get economic data for a specific series
        
        Args:
            series_id: FRED series ID (e.g., 'DFF' for interest rate)
        
        Returns:
            Dictionary with economic data
        """
        if not self.api_key:
            return {
                'series_id': series_id,
                'error': 'FRED API key not configured. Add FRED_API_KEY to .env',
                'get_key_at': 'https://fred.stlouisfed.org/docs/api/api_key.html'
            }
        
        url = f"{self.base_url}/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'limit': 10,
            'sort_order': 'desc'
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            observations = data.get('observations', [])
            
            if not observations:
                return {
                    'series_id': series_id,
                    'error': 'No data found',
                    'observations': []
                }
            
            # Get latest value
            latest = observations[0]
            
            # Calculate change from previous
            previous_value = float(observations[1]['value']) if len(observations) > 1 and observations[1]['value'] else None
            current_value = float(latest['value']) if latest['value'] else None
            change = current_value - previous_value if previous_value and current_value else None
            change_pct = (change / previous_value * 100) if previous_value and change else None
            
            return {
                'series_id': series_id,
                'title': data.get('title', series_id),
                'units': data.get('units', 'N/A'),
                'frequency': data.get('frequency', 'N/A'),
                'latest_value': current_value,
                'latest_date': latest.get('date', 'N/A'),
                'previous_value': previous_value,
                'change': round(change, 4) if change else None,
                'change_percent': round(change_pct, 2) if change_pct else None,
                'trend': 'UP' if change and change > 0 else 'DOWN' if change and change < 0 else 'FLAT',
                'observations': [
                    {
                        'date': obs.get('date'),
                        'value': float(obs['value']) if obs.get('value') else None
                    }
                    for obs in observations[:10]
                ],
                'timestamp': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'series_id': series_id,
                'error': str(e),
                'observations': []
            }
    
    def get_interest_rate(self) -> Dict:
        """Get current Federal Funds Interest Rate"""
        return self.get_series(self.series_ids['interest_rate'])
    
    def get_gdp(self) -> Dict:
        """Get latest GDP data"""
        return self.get_series(self.series_ids['gdp'])
    
    def get_cpi(self) -> Dict:
        """Get Consumer Price Index (Inflation)"""
        return self.get_series(self.series_ids['cpi'])
    
    def get_unemployment_rate(self) -> Dict:
        """Get current unemployment rate"""
        return self.get_series(self.series_ids['unemployment'])
    
    def get_treasury_yield(self, maturity: str = '10y') -> Dict:
        """
        Get Treasury yield for specific maturity
        
        Args:
            maturity: '3m', '2y', '10y'
        """
        series_map = {
            '3m': self.series_ids['treasury_3m'],
            '2y': self.series_ids['treasury_2y'],
            '10y': self.series_ids['treasury_10y']
        }
        series_id = series_map.get(maturity.lower(), self.series_ids['treasury_10y'])
        return self.get_series(series_id)
    
    def get_yield_curve_spread(self) -> Dict:
        """Get 10Y-2Y Treasury spread (recession indicator)"""
        return self.get_series(self.series_ids['yield_curve'])
    
    def get_recession_indicator(self) -> Dict:
        """Get US recession indicator"""
        return self.get_series(self.series_ids['recession'])
    
    def get_all_major_indicators(self) -> Dict:
        """
        Get all major economic indicators at once
        
        Returns:
            Dictionary with all key indicators
        """
        indicators = {
            'interest_rate': self.get_interest_rate(),
            'gdp': self.get_gdp(),
            'inflation': self.get_cpi(),
            'unemployment': self.get_unemployment_rate(),
            'treasury_10y': self.get_treasury_yield('10y'),
            'treasury_2y': self.get_treasury_yield('2y'),
            'yield_curve': self.get_yield_curve_spread(),
            'sp500': self.get_series(self.series_ids['sp500']),
            'crude_oil': self.get_series(self.series_ids['crude_oil_price']),
            'gold': self.get_series(self.series_ids['gold_price'])
        }
        
        # Create summary
        summary = {}
        for key, data in indicators.items():
            if 'error' not in data:
                summary[key] = {
                    'value': data.get('latest_value'),
                    'date': data.get('latest_date'),
                    'trend': data.get('trend')
                }
        
        return {
            'indicators': indicators,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_market_indicators(self) -> Dict:
        """
        Get market-related economic indicators
        
        Returns:
            Dictionary with market indicators
        """
        return {
            'sp500': self.get_series(self.series_ids['sp500']),
            'treasury_10y': self.get_treasury_yield('10y'),
            'treasury_2y': self.get_treasury_yield('2y'),
            'yield_curve': self.get_yield_curve_spread(),
            'crude_oil': self.get_series(self.series_ids['crude_oil_price']),
            'gold': self.get_series(self.series_ids['gold_price']),
            'vix': self.get_series('VIXCLS')  # Volatility Index
        }
    
    def get_inflation_data(self) -> Dict:
        """
        Get comprehensive inflation data
        
        Returns:
            Dictionary with inflation indicators
        """
        return {
            'cpi': self.get_cpi(),
            'ppi': self.get_series(self.series_ids['ppi']),
            'core_inflation': self.get_series('CPILFESL'),  # Core CPI
            'inflation_expectations': self.get_series('T5YIFR')  # 5Y Inflation Expectations
        }
    
    def get_labor_market_data(self) -> Dict:
        """
        Get labor market indicators
        
        Returns:
            Dictionary with labor data
        """
        return {
            'unemployment_rate': self.get_unemployment_rate(),
            'initial_claims': self.get_series(self.series_ids['initial_claims']),
            'labor_force_participation': self.get_series('CIVPART'),
            'employment_population_ratio': self.get_series('EMRATIO')
        }
    
    def get_consumer_data(self) -> Dict:
        """
        Get consumer economic indicators
        
        Returns:
            Dictionary with consumer data
        """
        return {
            'consumer_sentiment': self.get_series(self.series_ids['consumer_sentiment']),
            'retail_sales': self.get_series(self.series_ids['retail_sales']),
            'personal_spending': self.get_series('PCE'),
            'consumer_credit': self.get_series('TOTALSL')
        }


# Singleton instance
fred_service = FREDService()
