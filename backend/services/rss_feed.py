"""
RSS Feed Service - Fetch news from free RSS feeds + GDELT
Now includes:
- 15 reliable RSS feeds (optimized for speed)
- Concurrent fetching for faster load times
- GDELT unlimited news API (FREE, no key needed)
"""
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import re
from dateutil import parser as date_parser
from concurrent.futures import ThreadPoolExecutor, as_completed


class RSSFeedService:
    """Fetch news from various free RSS feeds"""
    
    # Reliable RSS feeds — 40+ sources across categories
    RSS_FEEDS = {
        # General/International
        'bbc': 'http://feeds.bbci.co.uk/news/rss.xml',
        'bbc_world': 'http://feeds.bbci.co.uk/news/world/rss.xml',
        'reuters': 'https://feeds.reuters.com/reuters/topNews',
        'aljazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
        'npr_news': 'https://feeds.npr.org/1001/rss.xml',
        'ap_top': 'https://feeds.apnews.com/rss/apf-topnews',
        'dw_news': 'https://rss.dw.com/rdf/rss-en-all',
        'france24': 'https://www.france24.com/en/rss',
        'guardian_world': 'https://www.theguardian.com/world/rss',
        'abc_news': 'https://feeds.abcnews.com/abcnews/topstories',
        'nbc_news': 'https://feeds.nbcnews.com/nbcnews/public/news',

        # Technology
        'techcrunch': 'https://techcrunch.com/feed/',
        'the_verge': 'https://www.theverge.com/rss/index.xml',
        'wired': 'https://www.wired.com/feed/rss',
        'ars_technica': 'https://feeds.arstechnica.com/arstechnica/index',
        'mit_tech': 'https://www.technologyreview.com/feed/',

        # Business/Economy
        'economist': 'https://www.economist.com/sections/business-finance/rss.xml',
        'cnbc': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        'marketwatch': 'https://www.marketwatch.com/rss/topstories',
        'guardian_business': 'https://www.theguardian.com/business/rss',
        'ft_world': 'https://www.ft.com/world?format=rss',
        'wsj_world': 'https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml',
        'seeking_alpha': 'https://seekingalpha.com/market_currents.xml',

        # Markets / Crypto
        'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'cointelegraph': 'https://cointelegraph.com/rss',
        'investing_com': 'https://www.investing.com/rss/news.rss',

        # US Government & Policy
        'white_house': 'https://www.whitehouse.gov/feed/',
        'sec_news': 'https://www.sec.gov/news/pressreleases.rss',
        'treasury_news': 'https://home.treasury.gov/news/press-releases.xml',
        'politico': 'https://rss.politico.com/politics-news.xml',
        'thehill': 'https://thehill.com/rss/syndicator/19109',
        'axios': 'https://api.axios.com/feed/',

        # Health & Science
        'who_news': 'https://www.who.int/rss-feeds/news-english.xml',
        'nih_news': 'https://www.nih.gov/news-releases/feed.xml',
        'nature_news': 'https://www.nature.com/news.rss',
        'science_daily': 'https://www.sciencedaily.com/rss/top.xml',

        # India
        'business_standard': 'https://www.business-standard.com/rss/home_page_top_stories.rss',
        'livemint_news': 'https://www.livemint.com/rss/news',
        'ndtv_profit': 'https://feeds.feedburner.com/ndtvprofit-latest',
        'economic_times': 'https://economictimes.indiatimes.com/rssfeedstopstories.cms',
    }
    
    CATEGORY_MAPPING = {
        'bbc': ['general'],
        'reuters': ['general', 'business'],
        'techcrunch': ['technology', 'business'],
        'the_verge': ['technology'],
        'wired': ['technology', 'science'],
        'google_news_in': ['policy', 'general'],
        'rbi_news': ['economy', 'finance'],
        'pib_news': ['policy', 'general'],
        'moneycontrol_in': ['economy', 'business'],
        'economictimes_in': ['economy', 'business'],
        'white_house': ['policy', 'general'],
        'defense_gov': ['policy', 'defense'],
        'state_dept': ['policy', 'international'],
        'justice_gov': ['policy', 'law'],
        'labor_gov': ['economy', 'labor'],
        'energy_gov': ['policy', 'energy'],
        'homeland_security': ['policy', 'security'],
        'nasa_news': ['science', 'space'],
        'cdc_news': ['health', 'policy'],
        'epa_news': ['environment', 'policy'],
        'fda_press': ['health', 'regulation'],
        'fema_news': ['policy', 'emergency'],
        'us_senate': ['policy', 'legislation'],
        'us_house': ['policy', 'legislation'],
        
        'india_pib': ['policy', 'government'],
        'mea_india': ['policy', 'international'],
        'isro_news': ['science', 'space'],
        'mohfw_india': ['health', 'policy'],
        'niti_aayog': ['policy', 'economy'],
        'sebi_news': ['markets', 'regulation'],
        'rbi_press': ['economy', 'finance'],
        'commerce_min': ['economy', 'business'],
        'make_in_india': ['business', 'economy'],
        
        'google_india_govt': ['policy', 'government'],
        'google_us_govt': ['policy', 'government'],
        'times_of_india_govt': ['policy', 'government'],
        'us_news_govt': ['policy', 'government'],
        'google_news_us': ['policy', 'general'],
        'sec_news': ['economy', 'finance', 'regulation'],
        'treasury_news': ['economy', 'finance'],
        'wsj_us': ['business', 'economy', 'general'],
        'coindesk': ['markets', 'crypto'],
        'cointelegraph': ['markets', 'crypto'],
        'forexlive': ['markets', 'forex'],
        'investing_news': ['markets', 'economy'],
        'seeking_alpha': ['markets', 'stocks', 'analysis'],
        'zacks_stocks': ['markets', 'stocks'],
        'morningstar': ['markets', 'mutual_funds'],
        'marketwatch': ['markets', 'stocks'],
        'economictimes_invest': ['markets', 'investing'],
        'kitco_gold': ['markets', 'metals'],
        'economist': ['business', 'economy'],
        'cnbc': ['business', 'economy'],
        'aljazeera': ['general', 'international'],
        'guardian_world': ['general', 'international'],
        'guardian_business': ['business', 'economy'],
        'npr_news': ['general', 'policy'],
        'ap_top': ['general', 'international'],
        'dw_news': ['general', 'international'],
        'france24': ['general', 'international'],
        'abc_news': ['general', 'policy'],
        'nbc_news': ['general', 'policy'],
        'business_standard': ['economy', 'business'],
        'livemint_news': ['business', 'economy'],
        'livemint_economy': ['economy', 'policy'],
        'ndtv_profit': ['economy', 'business'],
        'financial_express': ['economy', 'business'],
        'hindu_business': ['economy', 'business'],
        'india_today_biz': ['economy', 'business'],
        'politico': ['policy', 'government'],
        'thehill': ['policy', 'government'],
        'axios': ['general', 'policy'],
        'nature_news': ['science'],
        'science_daily': ['science'],
        'climatecentral': ['environment', 'science'],
        'who_news': ['health'],
        'nih_news': ['health', 'science'],
    }

    COUNTRY_MAPPING = {
        'bbc': 'global',
        'reuters': 'global',
        'techcrunch': 'global',
        'the_verge': 'global',
        'wired': 'global',
        'google_news_in': 'in',
        'rbi_news': 'in',
        'pib_news': 'in',
        'moneycontrol_in': 'in',
        'economictimes_in': 'in',
        'economictimes_in': 'in',
        'white_house': 'us',
        'defense_gov': 'us',
        'state_dept': 'us',
        'justice_gov': 'us',
        'labor_gov': 'us',
        'energy_gov': 'us',
        'homeland_security': 'us',
        'nasa_news': 'us',
        'cdc_news': 'us',
        'epa_news': 'us',
        'fda_press': 'us',
        'fema_news': 'us',
        'us_senate': 'us',
        'us_house': 'us',
        
        'india_pib': 'in',
        'mea_india': 'in',
        'isro_news': 'in',
        'mohfw_india': 'in',
        'niti_aayog': 'in',
        'sebi_news': 'in',
        'rbi_press': 'in',
        'commerce_min': 'in',
        'make_in_india': 'in',
        
        'google_india_govt': 'in',
        'google_us_govt': 'us',
        'times_of_india_govt': 'in',
        'us_news_govt': 'us',
        'google_news_us': 'us',
        'sec_news': 'us',
        'treasury_news': 'us',
        'wsj_us': 'us',
        'coindesk': 'global',
        'cointelegraph': 'global',
        'forexlive': 'global',
        'investing_news': 'global',
        'seeking_alpha': 'global',
        'zacks_stocks': 'global',
        'morningstar': 'global',
        'marketwatch': 'global',
        'kitco_gold': 'global',
        'economist': 'global',
        'cnbc': 'global',
        'aljazeera': 'global',
        'guardian_world': 'global',
        'guardian_business': 'global',
        'npr_news': 'us',
        'ap_top': 'global',
        'dw_news': 'global',
        'france24': 'global',
        'abc_news': 'us',
        'nbc_news': 'us',
        'business_standard': 'in',
        'livemint_news': 'in',
        'livemint_economy': 'in',
        'ndtv_profit': 'in',
        'financial_express': 'in',
        'hindu_business': 'in',
        'india_today_biz': 'in',
        'politico': 'us',
        'thehill': 'us',
        'axios': 'us',
        'nature_news': 'global',
        'science_daily': 'global',
        'climatecentral': 'global',
        'who_news': 'global',
        'nih_news': 'us',
    }
    
    def __init__(self):
        self.feeds = self.RSS_FEEDS
        self.category_mapping = self.CATEGORY_MAPPING
        self.country_mapping = self.COUNTRY_MAPPING
    
    def _generate_summary(self, description: str) -> str:
        """AI-powered heuristic summary generator - now with more context"""
        if not description:
            return "Summary unavailable."

        # Clean up HTML tags and bullet points
        clean_text = re.sub('<[^<]+?>', '', description)
        clean_text = re.sub(r'\s*[•·]\s*', ' ', clean_text)  # Remove bullet points
        clean_text = re.sub(r'\n\s*', ' ', clean_text)  # Remove newlines
        clean_text = re.sub(r'\s+', ' ', clean_text)  # Normalize multiple spaces

        # Split into sentences (keep more sentences for better context)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_text) if len(s.strip()) > 20]

        if not sentences:
            # If no sentences found, return first 400 chars
            return clean_text[:400] + "..." if len(clean_text) > 400 else clean_text

        # Return 3-4 sentences for better context (instead of just 2)
        num_sentences = min(4, len(sentences))
        summary = ". ".join(sentences[:num_sentences])
        
        # Ensure summary ends properly
        if not summary.endswith('.'):
            summary += '.'
        
        return summary

    def _analyze_article(self, title: str, description: str) -> Dict:
        """Analyze title and description for sentiment and impact"""
        text = (title + " " + description).lower()
        
        # Simple rule-based sentiment
        positive_words = ['growth', 'rise', 'success', 'innovation', 'breakthrough', 'positive', 'gain', 'surplus', 'recovery', 'improves', 'bullish', 'soars', 'rally']
        negative_words = ['decline', 'fall', 'crisis', 'failure', 'drop', 'negative', 'loss', 'deficit', 'recession', 'clash', 'protest', 'warns', 'bearish', 'slumps', 'crash']
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            sentiment = "Positive"
        elif neg_count > pos_count:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        # Simple rule-based impact
        high_impact_words = ['global', 'national', 'government', 'policy', 'economy', 'budget', 'emergency', 'security', 'major', 'fed', 'interest rates', 'inflation']
        medium_impact_words = ['industry', 'sector', 'company', 'local', 'regional', 'market', 'bitcoin', 'crypto', 'forex', 'stocks']
        
        high_count = sum(1 for word in high_impact_words if word in text)
        med_count = sum(1 for word in medium_impact_words if word in text)
        
        if high_count > 1:
            impact_level = "High"
        elif high_count == 1 or med_count > 1:
            impact_level = "Medium"
        else:
            impact_level = "Low"
            
        return {
            'sentiment': sentiment,
            'impact_level': impact_level
        }

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/rss+xml,application/xml;q=0.9,text/xml;q=0.8',
    }

    def fetch_feed(self, feed_name: str, url: str) -> List[Dict]:
        """Fetch a single RSS feed"""
        articles = []
        try:
            # Enhanced request for government servers
            response = requests.get(url, headers=self.HEADERS, timeout=8, verify=True)  # Reduced from 15s to 8s
            if response.status_code == 200:
                feed = feedparser.parse(response.content)

                for entry in feed.entries[:10]:  # Limit to 10 articles per feed (was 15)
                    title = entry.get('title', 'No Title')
                    desc = entry.get('description', entry.get('summary', ''))
                    
                    # Clean description: remove HTML, bullet points, and extra whitespace
                    clean_desc = re.sub('<[^<]+?>', '', desc)
                    clean_desc = re.sub(r'\s*[•·]\s*', ' ', clean_desc)  # Remove bullet points
                    clean_desc = re.sub(r'\n\s*', ' ', clean_desc)  # Remove newlines
                    clean_desc = ' '.join(clean_desc.split())  # Normalize whitespace
                    
                    analysis = self._analyze_article(title, clean_desc)

                    article = {
                        'title': title,
                        'description': clean_desc[:500],
                        'ai_summary': self._generate_summary(clean_desc),
                        'url': entry.get('link', ''),
                        'source': feed_name.replace('_', ' ').title(),
                        'published_at': self._parse_date(entry.get('published', '')),
                        'image': self._extract_image(entry),
                        'category': self.category_mapping.get(feed_name, ['general'])[0],
                        'country': self.country_mapping.get(feed_name, 'global'),
                        'content': entry.get('content', [{}])[0].get('value', '') if entry.get('content') else entry.get('summary', ''),
                        'sentiment': analysis['sentiment'],
                        'impact_level': analysis['impact_level']
                    }
                    articles.append(article)
        except Exception as e:
            print(f"Error fetching {feed_name}: {e}")
        
        return articles
    
    def _extract_image(self, entry) -> str:
        """Extract image URL from RSS entry"""
        # Try media_content
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0].get('url', '')
        
        # Try media_thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url', '')
        
        # Try to extract from content/description
        content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
        img_match = re.search(r'<img[^>]+src="([^">]+)"', content)
        if img_match:
            return img_match.group(1)
        
        return ''
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse RSS date string robustly and return offset-naive datetime"""
        if not date_str:
            return datetime.now()
        try:
            # Parse and remove timezone info to avoid comparison errors with offset-naive datetimes
            dt = date_parser.parse(date_str)
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return dt
        except Exception as e:
            return datetime.now()
    
    def fetch_all_feeds(self, categories: List[str] = None, country: str = 'all', max_age_days: int = 7, include_gdelt: bool = False, include_alternative: bool = False) -> List[Dict]:
        """
        Fetch all RSS feeds with concurrent fetching for speed
        
        Args:
            categories: Filter by categories
            country: Filter by country
            max_age_days: Only articles from last N days
            include_gdelt: Also fetch from GDELT API (disabled - unreliable)
            include_alternative: Also fetch from alternative sources (disabled - slow)
        """
        all_articles = []
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date - timedelta(days=max_age_days)

        # Fetch from RSS feeds concurrently (15 sources, ~8 seconds total)
        def fetch_single_feed(args):
            feed_name, url = args
            try:
                articles = self.fetch_feed(feed_name, url)
                return [a for a in articles if a.get('published_at', cutoff_date) >= cutoff_date]
            except Exception as e:
                print(f"Error fetching {feed_name}: {e}")
                return []
        
        # Use thread pool for concurrent fetching (5 concurrent feeds)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_single_feed, (feed_name, url)): feed_name 
                      for feed_name, url in self.feeds.items()}
            
            for future in as_completed(futures):
                feed_name = futures[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Feed {feed_name} failed: {e}")
        
        print(f"RSS: Loaded {len(all_articles)} articles from {len(self.feeds)} sources")
        
        # Sort by published date
        all_articles.sort(key=lambda x: x.get('published_at', datetime.now()), reverse=True)

        return all_articles
    
    def fetch_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Fetch articles for a specific category"""
        all_articles = self.fetch_all_feeds()
        filtered = [
            article for article in all_articles
            if article.get('category', '').lower() == category.lower()
        ]
        return filtered[:limit]
    
    def fetch_breaking_news(self, limit: int = 20) -> List[Dict]:
        """Fetch breaking news (most recent articles)"""
        all_articles = self.fetch_all_feeds()
        return all_articles[:limit]
    
    def fetch_trending_topics(self, limit: int = 10) -> List[Dict]:
        """Fetch trending topics based on frequency"""
        all_articles = self.fetch_all_feeds()
        
        from collections import Counter
        keywords = []
        
        for article in all_articles[:100]:
            title = article.get('title', '').lower()
            words = title.split()
            keywords.extend([w for w in words if len(w) > 4])
        
        trending = Counter(keywords).most_common(limit)
        
        return [
            {'topic': topic, 'count': count, 'category': 'trending'}
            for topic, count in trending
        ]
    
    def fetch_trending_news(self, limit: int = 20) -> List[Dict]:
        """Fetch trending news based on topic frequency and recency"""
        all_articles = self.fetch_all_feeds()
        
        # Score articles by recency and keyword frequency
        from collections import Counter
        from datetime import datetime
        
        # Get trending keywords
        keywords = []
        for article in all_articles[:100]:
            title = article.get('title', '').lower()
            words = title.split()
            keywords.extend([w for w in words if len(w) > 4 and len(w) < 20])
        
        keyword_counts = Counter(keywords)
        top_keywords = set([kw for kw, count in keyword_counts.most_common(20)])
        
        # Score articles
        scored_articles = []
        now = datetime.now() # Use offset-naive now
        
        for article in all_articles:
            title = article.get('title', '').lower()
            words = set(title.split())
            
            # Count trending keywords in title
            trend_score = len(words.intersection(top_keywords))
            
            # Recency bonus
            try:
                pub_date = article.get('published_at', now)
                hours_old = max(1, (now - pub_date).total_seconds() / 3600)
                recency_score = 24 / hours_old
            except:
                recency_score = 1
            
            total_score = trend_score * 2 + recency_score
            scored_articles.append((total_score, article))
        
        # Sort by score and return top articles
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        
        return [article for score, article in scored_articles[:limit]]


# Singleton instance
rss_service = RSSFeedService()
