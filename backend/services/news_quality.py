"""
News Quality Service - De-duplication, Source Tiering, and Ranking
Improves news feed quality by:
1. Removing duplicate stories
2. Tiering sources by quality
3. Ranking by relevance score
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
from collections import Counter


class NewsQualityService:
    """Improve news feed quality through de-duplication and ranking"""
    
    # Source tiers - higher is better
    SOURCE_TIERS = {
        # Tier 3: Premium wire services (highest quality)
        'reuters': 3,
        'associated press': 3,
        'ap news': 3,
        'bloomberg': 3,
        'wall street journal': 3,
        'financial times': 3,
        
        # Tier 2: Major news organizations
        'bbc': 2,
        'guardian': 2,
        'nbc news': 2,
        'abc news': 2,
        'cbs news': 2,
        'cnn': 2,
        'cnbc': 2,
        'npr': 2,
        'pbs': 2,
        'economist': 2,
        'forbes': 2,
        
        # Tier 1: Standard news sources
        'yahoo': 1,
        'google news': 1,
        'msn': 1,
        'business insider': 1,
        'axios': 1,
        'politico': 1,
        'the hill': 1,
        
        # Tier 0: Blogs/aggregators (lowest priority)
        'techcrunch': 0,
        'buzzfeed': 0,
        'daily mail': 0,
    }
    
    # Keywords that indicate low-quality/clickbait
    CLICKBAIT_KEYWORDS = [
        'you won\'t believe', 'shocking', 'mind-blowing', 'doctors hate',
        'one weird trick', 'click here', 'viral', 'omg', 'lol'
    ]
    
    def __init__(self):
        self.source_tiers = self.SOURCE_TIERS
    
    def process_feed(self, articles: List[Dict], limit: int = 20) -> List[Dict]:
        """
        Process article feed with de-duplication and ranking
        
        Args:
            articles: List of article dicts
            limit: Max articles to return
        
        Returns:
            Curated list of high-quality, unique articles
        """
        # Step 1: Calculate quality scores
        for article in articles:
            article['quality_score'] = self._calculate_quality_score(article)
        
        # Step 2: Group duplicates
        grouped = self._group_duplicates(articles)
        
        # Step 3: Select best version of each story
        unique_articles = []
        for group in grouped:
            # Sort by quality score, pick best
            group.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            best = group[0]
            best['duplicate_count'] = len(group)  # Show how many sources covered this
            unique_articles.append(best)
        
        # Step 4: Sort by quality + recency
        unique_articles.sort(
            key=lambda x: (
                x.get('quality_score', 0),
                self._parse_date(x.get('published_at', datetime.now()))
            ),
            reverse=True
        )
        
        # Step 5: Return top N
        return unique_articles[:limit]
    
    def _calculate_quality_score(self, article: Dict) -> float:
        """
        Calculate overall quality score (0-100)
        
        Factors:
        - Source tier (0-30 points)
        - Recency (0-25 points)
        - Impact level (0-20 points)
        - Content quality (0-15 points)
        - Uniqueness (0-10 points)
        """
        score = 0.0
        
        # Source tier (0-30 points)
        source_score = self._get_source_tier_score(article.get('source', ''))
        score += source_score * 10  # Max 30 points
        
        # Recency (0-25 points)
        recency_score = self._get_recency_score(article.get('published_at'))
        score += recency_score
        
        # Impact level (0-20 points)
        impact_scores = {'High': 20, 'Medium': 12, 'Low': 5}
        impact = article.get('impact_level', 'Low')
        score += impact_scores.get(impact, 5)
        
        # Content quality (0-15 points)
        content_score = self._get_content_quality_score(article)
        score += content_score
        
        # Uniqueness bonus (0-10 points) - will be calculated later
        score += 5  # Default midpoint
        
        return min(score, 100)
    
    def _get_source_tier_score(self, source: str) -> float:
        """Get source tier score (0-3)"""
        source_lower = source.lower()
        
        # Check for known sources
        for name, tier in self.source_tiers.items():
            if name in source_lower:
                return float(tier)
        
        # Government sources get automatic tier 2
        gov_keywords = ['gov', 'white house', 'sec', 'fda', 'federal', 'ministry']
        if any(kw in source_lower for kw in gov_keywords):
            return 2.5
        
        # Default tier 1 for unknown sources
        return 1.0
    
    def _get_recency_score(self, published_at) -> float:
        """Calculate recency score (0-25 points)"""
        try:
            pub_date = self._parse_date(published_at)
            hours_old = (datetime.now() - pub_date).total_seconds() / 3600
            
            if hours_old < 1:
                return 25  # Breaking!
            elif hours_old < 6:
                return 22  # Very recent
            elif hours_old < 24:
                return 18  # Today
            elif hours_old < 48:
                return 12  # Yesterday
            elif hours_old < 168:  # 7 days
                return 6   # This week
            else:
                return 2   # Old
        except:
            return 10  # Default midpoint
    
    def _get_content_quality_score(self, article: Dict) -> float:
        """Evaluate content quality (0-15 points)"""
        score = 10.0  # Start with midpoint
        
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        text = title + ' ' + description
        
        # Penalize clickbait
        clickbait_count = sum(1 for kw in self.CLICKBAIT_KEYWORDS if kw in text)
        score -= clickbait_count * 3
        
        # Bonus for having description
        if description and len(description) > 50:
            score += 2
        
        # Bonus for having author
        if article.get('author'):
            score += 1
        
        # Bonus for having image
        if article.get('image') or article.get('url_to_image'):
            score += 1
        
        # Penalize very short titles
        if len(title.split()) < 5:
            score -= 2
        
        return max(0, min(score, 15))
    
    def _group_duplicates(self, articles: List[Dict]) -> List[List[Dict]]:
        """
        Group duplicate articles together
        
        Uses fuzzy matching on:
        - Title similarity
        - Same entities mentioned
        - Same time window
        """
        groups = []
        used = set()
        
        for i, article in enumerate(articles):
            if i in used:
                continue
            
            # Start new group
            group = [article]
            used.add(i)
            
            # Find similar articles
            for j, other in enumerate(articles):
                if j in used or j == i:
                    continue
                
                if self._are_duplicates(article, other):
                    group.append(other)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    def _are_duplicates(self, article1: Dict, article2: Dict) -> bool:
        """Check if two articles are duplicates of the same story"""
        
        # Check time window (within 24 hours)
        try:
            date1 = self._parse_date(article1.get('published_at'))
            date2 = self._parse_date(article2.get('published_at'))
            hours_diff = abs((date1 - date2).total_seconds() / 3600)
            
            if hours_diff > 24:
                return False  # Too far apart
        except:
            pass
        
        # Check title similarity
        title1 = article1.get('title', '').lower()
        title2 = article2.get('title', '').lower()
        
        # Extract key terms
        terms1 = self._extract_key_terms(title1)
        terms2 = self._extract_key_terms(title2)
        
        if not terms1 or not terms2:
            return False
        
        # Check overlap
        overlap = len(set(terms1) & set(terms2))
        min_terms = min(len(terms1), len(terms2))
        
        if min_terms > 0 and overlap / min_terms >= 0.6:
            return True  # 60%+ term overlap = duplicate
        
        return False
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract important terms from text"""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'this', 'that', 'it', 'as', 'if', 'when', 'than', 'because', 'while'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Filter stop words
        key_terms = [w for w in words if w not in stop_words]
        
        return key_terms[:20]
    
    def _parse_date(self, date_val) -> datetime:
        """Parse date string to datetime"""
        if not date_val:
            return datetime.now()
        
        if isinstance(date_val, datetime):
            return date_val
        
        try:
            # ISO format
            return datetime.fromisoformat(date_val.replace('Z', '+00:00'))
        except:
            return datetime.now()
    
    def get_personalized_feed(self, articles: List[Dict], 
                             user_history: List[str], 
                             limit: int = 20) -> List[Dict]:
        """
        Get personalized feed based on user reading history
        
        Args:
            articles: Available articles
            user_history: List of topics/categories user has read
            limit: Max articles to return
        
        Returns:
            Personalized article list
        """
        # Score articles by user interest
        for article in articles:
            interest_score = self._calculate_user_interest(article, user_history)
            article['personalization_score'] = interest_score
        
        # Sort by combined quality + personalization
        articles.sort(
            key=lambda x: (
                x.get('quality_score', 0) * 0.6 +  # 60% quality
                x.get('personalization_score', 0) * 0.4  # 40% personalization
            ),
            reverse=True
        )
        
        return articles[:limit]
    
    def _calculate_user_interest(self, article: Dict, user_history: List[str]) -> float:
        """Calculate how much user would be interested in this article"""
        if not user_history:
            return 50.0  # Default
        
        score = 0.0
        
        # Check category match
        category = article.get('category', '').lower()
        if category in [h.lower() for h in user_history]:
            score += 40
        
        # Check topic keywords
        title = article.get('title', '').lower()
        for history_item in user_history:
            if history_item.lower() in title:
                score += 20
        
        # Check sector match (for policy articles)
        sectors = article.get('affected_sectors', [])
        for sector in sectors:
            if sector.get('sector', '').lower() in [h.lower() for h in user_history]:
                score += 30
        
        return min(score, 100)


# Singleton instance
news_quality_service = NewsQualityService()
