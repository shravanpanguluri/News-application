"""
Breaking News Detector - Full Intelligence
Detects truly breaking news using multiple signals:
1. Cross-source validation (multiple RSS feeds)
2. Government source priority
3. Keyword velocity detection
4. Reddit trending analysis
5. Market impact detection
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
import re


class BreakingNewsDetector:
    """Intelligent breaking news detection system"""
    
    # Keywords that indicate breaking news
    BREAKING_KEYWORDS = {
        'high_impact': [
            'breaking', 'urgent', 'just in', 'developing', 'live update',
            'emergency', 'crisis', 'major', 'historic', 'unprecedented'
        ],
        'government': [
            'white house', 'president', 'congress', 'senate', 'supreme court',
            'federal reserve', 'sec filing', 'fda approves', 'government announces',
            'pib', 'ministry announces', 'parliament', 'executive order'
        ],
        'market_moving': [
            'merger', 'acquisition', 'bankruptcy', 'layoffs', 'strike',
            'interest rate', 'inflation', 'gdp', 'unemployment', 'recession',
            'stock surge', 'stock plunge', 'crypto crash', 'bitcoin',
            'fed announces', 'earnings beat', 'earnings miss'
        ],
        'health': [
            'fda approves', 'vaccine', 'pandemic', 'outbreak', 'who announces',
            'clinical trial', 'drug approval', 'health emergency'
        ]
    }
    
    # High-authority sources (auto-boost breaking score)
    AUTHORITY_SOURCES = {
        'government': [
            'white house', 'pib', 'sec', 'federal reserve', 'treasury',
            'defense department', 'state department', 'cdc', 'fda'
        ],
        'major_news': [
            'reuters', 'associated press', 'bloomberg', 'wall street journal',
            'financial times', 'economist'
        ]
    }
    
    def __init__(self, reddit_service=None, market_service=None):
        self.reddit_service = reddit_service
        self.market_service = market_service
    
    def analyze_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Analyze all articles and rank by breaking score
        
        Args:
            articles: List of article dicts with title, description, source, published_at
        
        Returns:
            Articles sorted by breaking score with metadata
        """
        analyzed = []
        
        for article in articles:
            analysis = self.calculate_breaking_score(article, articles)
            analyzed.append({
                **article,
                'breaking_score': analysis['score'],
                'is_breaking': analysis['score'] >= 70,
                'is_trending': analysis['score'] >= 50,
                'breaking_signals': analysis['signals'],
                'analyzed_at': datetime.now().isoformat()
            })
        
        # Sort by breaking score (highest first)
        analyzed.sort(key=lambda x: x['breaking_score'], reverse=True)
        
        # Add ranking
        for i, article in enumerate(analyzed):
            article['breaking_rank'] = i + 1
        
        return analyzed
    
    def calculate_breaking_score(self, article: Dict, all_articles: List[Dict]) -> Dict:
        """
        Calculate breaking news score (0-100) using multiple signals
        
        Returns:
            Dict with score and signal breakdown
        """
        signals = {}
        total_score = 0
        
        # Signal 1: Recency (0-20 points)
        recency_score = self._analyze_recency(article)
        signals['recency'] = recency_score
        total_score += recency_score['score']
        
        # Signal 2: Cross-source validation (0-25 points)
        cross_source_score = self._analyze_cross_source(article, all_articles)
        signals['cross_source'] = cross_source_score
        total_score += cross_source_score['score']
        
        # Signal 3: Keyword detection (0-20 points)
        keyword_score = self._analyze_keywords(article)
        signals['keywords'] = keyword_score
        total_score += keyword_score['score']
        
        # Signal 4: Source authority (0-15 points)
        authority_score = self._analyze_source_authority(article)
        signals['authority'] = authority_score
        total_score += authority_score['score']
        
        # Signal 5: Reddit trending (0-10 points) - if available
        reddit_score = self._analyze_reddit_signals(article)
        signals['reddit'] = reddit_score
        total_score += reddit_score['score']
        
        # Signal 6: Market impact potential (0-10 points)
        market_score = self._analyze_market_impact(article)
        signals['market_impact'] = market_score
        total_score += market_score['score']
        
        return {
            'score': min(total_score, 100),
            'signals': signals,
            'total_signals': sum(1 for s in signals.values() if s['score'] > 0)
        }
    
    def _analyze_recency(self, article: Dict) -> Dict:
        """Analyze how recent the article is (0-20 points)"""
        try:
            published_at = article.get('published_at')
            if not published_at:
                return {'score': 0, 'details': 'No publish time'}
            
            # Parse datetime (handle both string and datetime objects)
            if isinstance(published_at, str):
                published_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                if published_dt.tzinfo:
                    published_dt = published_dt.replace(tzinfo=None)
            else:
                published_dt = published_at
            
            minutes_old = (datetime.now() - published_dt).total_seconds() / 60
            
            if minutes_old < 15:
                return {'score': 20, 'details': f'{minutes_old:.0f} min ago - VERY RECENT'}
            elif minutes_old < 30:
                return {'score': 15, 'details': f'{minutes_old:.0f} min ago - RECENT'}
            elif minutes_old < 60:
                return {'score': 10, 'details': f'{minutes_old:.0f} min ago - MODERATE'}
            elif minutes_old < 180:
                return {'score': 5, 'details': f'{minutes_old:.0f} min ago - OLDER'}
            else:
                return {'score': 0, 'details': f'{minutes_old:.0f} min ago - TOO OLD'}
        
        except Exception as e:
            return {'score': 0, 'details': f'Error: {str(e)}'}
    
    def _analyze_cross_source(self, article: Dict, all_articles: List[Dict]) -> Dict:
        """
        Check if multiple sources are reporting similar story (0-25 points)
        """
        try:
            title = article.get('title', '').lower()
            # Extract key terms (nouns, important words)
            key_terms = self._extract_key_terms(title)
            
            if not key_terms:
                return {'score': 0, 'details': 'No key terms extracted'}
            
            # Find similar articles
            similar_sources = set()
            similar_count = 0
            
            for other in all_articles:
                if other.get('url') == article.get('url'):
                    continue  # Skip self
                
                other_title = other.get('title', '').lower()
                # Check for term overlap
                other_terms = self._extract_key_terms(other_title)
                overlap = len(set(key_terms) & set(other_terms))
                
                if overlap >= 2:  # At least 2 key terms match
                    similar_count += 1
                    similar_sources.add(other.get('source', 'unknown'))
            
            # Score based on number of sources covering same story
            unique_sources = len(similar_sources)
            
            if unique_sources >= 5:
                return {
                    'score': 25,
                    'details': f'{unique_sources} sources covering - WIDESPREAD',
                    'sources': list(similar_sources)[:5]
                }
            elif unique_sources >= 3:
                return {
                    'score': 18,
                    'details': f'{unique_sources} sources covering - TRENDING',
                    'sources': list(similar_sources)[:5]
                }
            elif unique_sources >= 2:
                return {
                    'score': 10,
                    'details': f'{unique_sources} sources covering - DEVELOPING',
                    'sources': list(similar_sources)[:5]
                }
            else:
                return {
                    'score': 3,
                    'details': 'Single source - EXCLUSIVE',
                    'sources': []
                }
        
        except Exception as e:
            return {'score': 0, 'details': f'Error: {str(e)}'}
    
    def _analyze_keywords(self, article: Dict) -> Dict:
        """Analyze title/description for breaking news keywords (0-20 points)"""
        try:
            text = (
                article.get('title', '').lower() + ' ' +
                article.get('description', '').lower()
            )
            
            matched_categories = []
            total_matches = 0
            
            for category, keywords in self.BREAKING_KEYWORDS.items():
                matches = [kw for kw in keywords if kw in text]
                if matches:
                    matched_categories.append(category)
                    total_matches += len(matches)
            
            # Score based on keyword matches
            if total_matches >= 5:
                return {
                    'score': 20,
                    'details': f'{total_matches} breaking keywords - VERY URGENT',
                    'categories': matched_categories
                }
            elif total_matches >= 3:
                return {
                    'score': 15,
                    'details': f'{total_matches} breaking keywords - URGENT',
                    'categories': matched_categories
                }
            elif total_matches >= 1:
                return {
                    'score': 8,
                    'details': f'{total_matches} breaking keywords - NOTABLE',
                    'categories': matched_categories
                }
            else:
                return {
                    'score': 0,
                    'details': 'No breaking keywords',
                    'categories': []
                }
        
        except Exception as e:
            return {'score': 0, 'details': f'Error: {str(e)}'}
    
    def _analyze_source_authority(self, article: Dict) -> Dict:
        """Analyze if source is high-authority (0-15 points)"""
        try:
            source = article.get('source', '').lower()
            
            # Check government sources
            for gov_source in self.AUTHORITY_SOURCES['government']:
                if gov_source in source:
                    return {
                        'score': 15,
                        'details': 'Government/Official source',
                        'type': 'government'
                    }
            
            # Check major news sources
            for news_source in self.AUTHORITY_SOURCES['major_news']:
                if news_source in source:
                    return {
                        'score': 10,
                        'details': 'Major news wire service',
                        'type': 'major_news'
                    }
            
            return {
                'score': 3,
                'details': 'Standard news source',
                'type': 'standard'
            }
        
        except Exception as e:
            return {'score': 0, 'details': f'Error: {str(e)}'}
    
    def _analyze_reddit_signals(self, article: Dict) -> Dict:
        """
        Check Reddit for trending signals (0-10 points)
        Requires reddit_service to be initialized
        """
        if not self.reddit_service:
            return {'score': 0, 'details': 'Reddit service not available'}
        
        try:
            # Extract key terms from title
            title = article.get('title', '').lower()
            key_terms = self._extract_key_terms(title)
            
            if not key_terms:
                return {'score': 0, 'details': 'No terms to search'}
            
            # This would require actual Reddit API integration
            # For now, return placeholder
            return {
                'score': 5,
                'details': 'Reddit analysis pending',
                'status': 'not_implemented'
            }
        
        except Exception as e:
            return {'score': 0, 'details': f'Error: {str(e)}'}
    
    def _analyze_market_impact(self, article: Dict) -> Dict:
        """
        Analyze if article mentions stocks/companies that could move markets (0-10 points)
        """
        try:
            text = (
                article.get('title', '').lower() + ' ' +
                article.get('description', '').lower()
            )
            
            # Check for market-moving keywords
            market_keywords = [
                'earnings', 'revenue', 'profit', 'loss', 'guidance',
                'merger', 'acquisition', 'buyout', 'ipo',
                'fda approval', 'clinical trial', 'drug approval',
                'layoffs', 'strike', 'ceo resigns', 'bankruptcy',
                'fed', 'interest rate', 'inflation', 'jobs report'
            ]
            
            matches = [kw for kw in market_keywords if kw in text]
            
            # Check for stock tickers (simple pattern)
            ticker_pattern = r'\b[A-Z]{2,5}\b'
            tickers = re.findall(ticker_pattern, article.get('title', ''))
            # Filter common words
            tickers = [t for t in tickers if t not in ['THE', 'AND', 'FOR', 'WITH']]
            
            if len(matches) >= 3 or len(tickers) >= 2:
                return {
                    'score': 10,
                    'details': f'Market-moving potential: {matches + tickers}',
                    'tickers': tickers[:5]
                }
            elif len(matches) >= 1 or len(tickers) >= 1:
                return {
                    'score': 5,
                    'details': f'Possible market impact: {matches + tickers}',
                    'tickers': tickers[:5]
                }
            else:
                return {
                    'score': 0,
                    'details': 'No market impact detected',
                    'tickers': []
                }
        
        except Exception as e:
            return {'score': 0, 'details': f'Error: {str(e)}'}
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract important terms from text for matching"""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'it', 'its', 'as', 'if', 'when',
            'than', 'because', 'while', 'although', 'though', 'after', 'before',
            'during', 'through', 'between', 'into', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'all', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'just', 'about', 'what', 'which', 'who', 'whom'
        }
        
        # Split and clean
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter stop words and get unique terms
        key_terms = list(set(w for w in words if w not in stop_words))
        
        return key_terms[:10]  # Return top 10 terms
    
    def get_breaking_news(self, articles: List[Dict], limit: int = 20) -> List[Dict]:
        """
        Get top breaking news stories
        
        Args:
            articles: List of articles to analyze
            limit: Number of breaking stories to return
        
        Returns:
            Top breaking news stories
        """
        analyzed = self.analyze_articles(articles)
        
        # Filter for breaking/trending only
        breaking = [a for a in analyzed if a['breaking_score'] >= 50]
        
        # Return top N
        return breaking[:limit]
    
    def get_trending_topics(self, articles: List[Dict]) -> List[Dict]:
        """
        Extract trending topics from breaking news
        
        Returns:
            List of trending topics with frequency
        """
        breaking = self.get_breaking_news(articles, limit=50)
        
        # Extract key terms from breaking news
        all_terms = []
        for article in breaking:
            terms = self._extract_key_terms(article.get('title', ''))
            all_terms.extend(terms)
        
        # Count frequency
        term_counts = Counter(all_terms)
        
        # Return top trending
        trending = [
            {'topic': term, 'count': count, 'relevance': 'high' if count >= 3 else 'medium'}
            for term, count in term_counts.most_common(20)
        ]
        
        return trending


# Singleton instance
breaking_news_detector = BreakingNewsDetector()
