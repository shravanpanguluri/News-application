"""
Reddit Sentiment Service - Stock sentiment from Reddit
FREE API via PRAW (Python Reddit API Wrapper)
Requires: Reddit API keys (takes 2 minutes to get)
Get keys at: https://www.reddit.com/prefs/apps
"""
import praw
from textblob import TextBlob
from typing import Dict, List, Optional
from datetime import datetime
import os


class RedditSentimentService:
    """Analyze stock sentiment from Reddit discussions"""
    
    def __init__(self):
        # Get these keys from https://www.reddit.com/prefs/apps
        # Takes 2 minutes to create an app and get credentials
        self.client_id = os.getenv('REDDIT_CLIENT_ID', '')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET', '')
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'Predovex/1.0 by /u/yourusername')
        
        # Initialize Reddit client
        try:
            if self.client_id and self.client_secret:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent
                )
                self.enabled = True
            else:
                self.enabled = False
                self.reddit = None
        except Exception as e:
            print(f"Reddit API initialization failed: {e}")
            self.enabled = False
            self.reddit = None
    
    def get_stock_sentiment(self, ticker: str, limit: int = 100) -> Dict:
        """
        Get sentiment analysis for a stock ticker from Reddit
        
        Args:
            ticker: Stock symbol (e.g., 'TSLA', 'AAPL')
            limit: Number of posts to analyze
        
        Returns:
            Dictionary with sentiment score and analysis
        """
        if not self.enabled:
            return {
                'ticker': ticker,
                'error': 'Reddit API not configured. Add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to .env',
                'sentiment_score': 0,
                'sentiment_label': 'UNAVAILABLE'
            }
        
        try:
            # Search across multiple subreddits
            subreddits = self.reddit.subreddit('stocks+investing+wallstreetbets+SecurityAnalysis')
            posts = subreddits.search(ticker, limit=limit, time_filter='week')
            
            sentiment_scores = []
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0
            post_details = []
            
            for post in posts:
                # Combine title and text for analysis
                text = f"{post.title} {post.selftext}"
                
                # Sentiment analysis using TextBlob
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity  # -1 to +1
                sentiment_scores.append(polarity)
                
                # Categorize sentiment
                if polarity > 0.1:
                    bullish_count += 1
                elif polarity < -0.1:
                    bearish_count += 1
                else:
                    neutral_count += 1
                
                # Store post details
                post_details.append({
                    'title': post.title,
                    'score': post.score,
                    'upvote_ratio': post.upvote_ratio,
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
                    'subreddit': post.subreddit.display_name,
                    'url': f"https://reddit.com{post.permalink}",
                    'sentiment': polarity
                })
            
            # Calculate average sentiment
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # Determine sentiment label
            if avg_sentiment > 0.15:
                sentiment_label = 'BULLISH'
            elif avg_sentiment < -0.15:
                sentiment_label = 'BEARISH'
            else:
                sentiment_label = 'NEUTRAL'
            
            # Sort posts by score (most popular first)
            post_details.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'ticker': ticker,
                'sentiment_score': round(avg_sentiment, 3),
                'sentiment_label': sentiment_label,
                'post_count': len(sentiment_scores),
                'bullish_posts': bullish_count,
                'bearish_posts': bearish_count,
                'neutral_posts': neutral_count,
                'bullish_percent': round((bullish_count / len(sentiment_scores) * 100), 1) if sentiment_scores else 0,
                'bearish_percent': round((bearish_count / len(sentiment_scores) * 100), 1) if sentiment_scores else 0,
                'top_posts': post_details[:10],  # Top 10 most popular
                'period': 'Last 7 days',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'error': str(e),
                'sentiment_score': 0,
                'sentiment_label': 'ERROR'
            }
    
    def get_trending_stocks(self, limit: int = 20) -> Dict:
        """
        Get trending stocks on Reddit by mention count
        
        Args:
            limit: Number of trending stocks to return
        
        Returns:
            Dictionary with trending stocks
        """
        if not self.enabled:
            return {
                'error': 'Reddit API not configured',
                'trending': []
            }
        
        try:
            # Get posts from wallstreetbets (most active stock discussion)
            subreddit = self.reddit.subreddit('wallstreetbets')
            posts = subreddit.hot(limit=500)
            
            # Count stock ticker mentions
            ticker_counts = {}
            common_tickers = [
                'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'AMZN', 
                'GOOGL', 'META', 'MSFT', 'GME', 'AMC', 'PLTR', 'SOFI',
                'NIO', 'BABA', 'COIN', 'MSTR', 'RIOT', 'MARA'
            ]
            
            for post in posts:
                title_upper = post.title.upper()
                for ticker in common_tickers:
                    if f'${ticker}' in title_upper or f' {ticker} ' in f" {title_upper} ":
                        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
            
            # Sort by mention count
            trending = sorted(
                [{'ticker': k, 'mentions': v} for k, v in ticker_counts.items()],
                key=lambda x: x['mentions'],
                reverse=True
            )[:limit]
            
            return {
                'trending': trending,
                'period': 'Current Hot Posts',
                'total_posts_analyzed': 500,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'trending': []
            }
    
    def get_sector_sentiment(self, sector: str) -> Dict:
        """
        Get sentiment for a specific sector
        
        Args:
            sector: Sector name (technology, defense, pharma, energy, finance)
        
        Returns:
            Dictionary with sector sentiment
        """
        # Sector keywords and associated stocks
        sector_data = {
            'technology': {
                'keywords': ['tech', 'AI', 'software', 'semiconductor', 'cloud'],
                'stocks': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META']
            },
            'defense': {
                'keywords': ['defense', 'military', 'contract', 'pentagon', 'aerospace'],
                'stocks': ['LMT', 'RTX', 'NOC', 'GD', 'BA']
            },
            'pharma': {
                'keywords': ['pharma', 'biotech', 'FDA', 'drug', 'clinical trial'],
                'stocks': ['JNJ', 'PFE', 'MRK', 'ABBV', 'BMY']
            },
            'energy': {
                'keywords': ['oil', 'gas', 'energy', 'renewable', 'crude'],
                'stocks': ['XOM', 'CVX', 'COP', 'SLB', 'EOG']
            },
            'finance': {
                'keywords': ['bank', 'finance', 'fed', 'interest rate', 'trading'],
                'stocks': ['JPM', 'BAC', 'WFC', 'GS', 'MS']
            }
        }
        
        if sector.lower() not in sector_data:
            return {
                'error': f'Unknown sector: {sector}',
                'valid_sectors': list(sector_data.keys())
            }
        
        sector_info = sector_data[sector.lower()]
        
        # Get sentiment for each stock in the sector
        stock_sentiments = []
        for ticker in sector_info['stocks']:
            sentiment = self.get_stock_sentiment(ticker, limit=50)
            stock_sentiments.append({
                'ticker': ticker,
                'sentiment_score': sentiment.get('sentiment_score', 0),
                'sentiment_label': sentiment.get('sentiment_label', 'UNKNOWN')
            })
        
        # Calculate average sector sentiment
        avg_sentiment = sum(s['sentiment_score'] for s in stock_sentiments) / len(stock_sentiments)
        
        if avg_sentiment > 0.15:
            sector_label = 'BULLISH'
        elif avg_sentiment < -0.15:
            sector_label = 'BEARISH'
        else:
            sector_label = 'NEUTRAL'
        
        return {
            'sector': sector,
            'sentiment_score': round(avg_sentiment, 3),
            'sentiment_label': sector_label,
            'stocks_analyzed': len(stock_sentiments),
            'stock_sentiments': stock_sentiments,
            'keywords': sector_info['keywords'],
            'timestamp': datetime.now().isoformat()
        }
    
    def search_discussions(self, query: str, limit: int = 50) -> Dict:
        """
        Search Reddit for specific topics
        
        Args:
            query: Search query
            limit: Number of posts
        
        Returns:
            Dictionary with search results
        """
        if not self.enabled:
            return {
                'error': 'Reddit API not configured',
                'posts': []
            }
        
        try:
            subreddits = self.reddit.subreddit('stocks+investing+wallstreetbets+SecurityAnalysis+economics')
            posts = subreddits.search(query, limit=limit, time_filter='month')
            
            results = []
            for post in posts:
                results.append({
                    'title': post.title,
                    'score': post.score,
                    'num_comments': post.num_comments,
                    'subreddit': post.subreddit.display_name,
                    'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
                    'url': f"https://reddit.com{post.permalink}",
                    'selftext': post.selftext[:300] if post.selftext else ''
                })
            
            return {
                'query': query,
                'post_count': len(results),
                'posts': results[:20],  # Return top 20
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'posts': []
            }


# Singleton instance
reddit_sentiment_service = RedditSentimentService()
