"""
Alternative Free News APIs - No API Key Required
- Spaceflight News API (unlimited, real-time)
- Wikipedia Current Events (unlimited, daily updates)
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict


class AlternativeNewsService:
    """Fetch news from alternative free APIs"""
    
    # Spaceflight News API (unlimited, no key)
    SPACEFLIGHT_URL = "https://api.spaceflightnewsapi.net/v4/articles"
    
    # Wikipedia Current Events (unlimited, no key)
    WIKI_URL = "https://en.wikipedia.org/api/rest_v1/feed/featured/{year}/{month}/{day}"
    
    def __init__(self):
        self.timeout = 15
    
    def get_spaceflight_news(self, limit: int = 50) -> List[Dict]:
        """
        Get spaceflight/aerospace news (unlimited, no API key)
        
        Args:
            limit: Max articles
        
        Returns:
            List of articles
        """
        try:
            params = {
                'limit': limit,
                'ordering': '-published_at'
            }
            
            response = requests.get(
                self.SPACEFLIGHT_URL,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                articles = []
                for item in results:
                    article = {
                        'title': item.get('title', 'No title'),
                        'description': item.get('summary', '') or item.get('title', ''),
                        'url': item.get('url', ''),
                        'source': 'Spaceflight News',
                        'published_at': self._parse_date(item.get('published_at', '')),
                        'category': 'technology',
                        'country': 'global',
                        'sentiment': 'Neutral',
                        'impact_level': 'Medium',
                        'image': item.get('image_url', ''),
                    }
                    articles.append(article)
                
                print(f"Spaceflight News: Found {len(articles)} articles")
                return articles
            else:
                print(f"Spaceflight API error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Spaceflight fetch error: {e}")
            return []
    
    def get_wikipedia_current_events(self, days: int = 7) -> List[Dict]:
        """
        Get current events from Wikipedia (unlimited, no API key)
        
        Args:
            days: Number of days to fetch
        
        Returns:
            List of articles
        """
        articles = []
        
        try:
            for day_offset in range(days):
                date = datetime.now() - timedelta(days=day_offset)
                url = self.WIKI_URL.format(
                    year=date.year,
                    month=date.month,
                    day=date.day
                )
                
                response = requests.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract featured articles
                    featured = data.get('featured', [])
                    
                    for item in featured[:10]:  # Max 10 per day
                        article = {
                            'title': item.get('title', 'No title'),
                            'description': item.get('extract', '')[:200],
                            'url': f"https://en.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}",
                            'source': 'Wikipedia Current Events',
                            'published_at': date,
                            'category': 'general',
                            'country': 'global',
                            'sentiment': 'Neutral',
                            'impact_level': 'Low',
                            'image': item.get('thumbnail', {}).get('source', ''),
                        }
                        articles.append(article)
            
            print(f"Wikipedia: Found {len(articles)} current events")
            return articles
            
        except Exception as e:
            print(f"Wikipedia fetch error: {e}")
            return []
    
    def get_all_alternative_news(self, spaceflight_limit: int = 30, wiki_days: int = 3) -> List[Dict]:
        """
        Get news from all alternative sources
        
        Args:
            spaceflight_limit: Max spaceflight articles
            wiki_days: Days of Wikipedia events
        
        Returns:
            Combined list of articles
        """
        all_articles = []
        
        # Get spaceflight news
        spaceflight = self.get_spaceflight_news(limit=spaceflight_limit)
        all_articles.extend(spaceflight)
        
        # Get Wikipedia current events
        wiki = self.get_wikipedia_current_events(days=wiki_days)
        all_articles.extend(wiki)
        
        return all_articles
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse ISO date string"""
        try:
            if date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        return datetime.now()


# Singleton instance
alternative_news_service = AlternativeNewsService()
