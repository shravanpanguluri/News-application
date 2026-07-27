"""
Government API Service - Fetches data from India and US government sources
"""
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio


class PIBService:
    """Press Information Bureau of India - RSS Feed Parser"""
    
    def __init__(self):
        self.base_url = "https://pib.gov.in/rss.aspx"
        self.source = "pib"
        self.country = "in"
    
    def fetch_press_releases(self, limit: int = 50) -> List[Dict]:
        """Fetch latest press releases from PIB"""
        articles = []
        try:
            feed = feedparser.parse(self.base_url)
            for entry in feed.entries[:limit]:
                article = {
                    "title": entry.title,
                    "description": entry.get("description", "")[:500],
                    "content": entry.get("description", ""),
                    "source": self.source,
                    "country": self.country,
                    "category": self._categorize(entry.title),
                    "url": entry.get("link", ""),
                    "published_at": self._parse_date(entry.get("published", "")),
                    "impact_score": self._calculate_impact(entry.title),
                    "tags": self._extract_tags(entry.title),
                    "article_metadata": {
                        "author": entry.get("author", "PIB"),
                        "language": "en"
                    }
                }
                articles.append(article)
        except Exception as e:
            print(f"Error fetching PIB data: {e}")
        
        return articles
    
    def _categorize(self, title: str) -> str:
        """Categorize article based on title keywords"""
        title_lower = title.lower()
        categories = {
            "economy": ["economy", "gdp", "budget", "finance", "economic"],
            "health": ["health", "medical", "hospital", "disease", "vaccine"],
            "education": ["education", "school", "university", "student"],
            "agriculture": ["agriculture", "farm", "crop", "farmer"],
            "technology": ["technology", "digital", "it", "software", "ai"],
            "infrastructure": ["infrastructure", "road", "railway", "airport"],
            "environment": ["environment", "climate", "pollution", "green"],
            "defense": ["defense", "military", "army", "security"],
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        return "general"
    
    def _calculate_impact(self, title: str) -> int:
        """Calculate impact score 0-10"""
        high_impact_keywords = [
            "prime minister", "president", "cabinet", "parliament", 
            "budget", "policy", "scheme", "launch", "national"
        ]
        score = 0
        title_lower = title.lower()
        
        for keyword in high_impact_keywords:
            if keyword in title_lower:
                score += 2
        
        return min(score, 10)
    
    def _extract_tags(self, title: str) -> List[str]:
        """Extract relevant tags from title"""
        # Simple keyword extraction
        keywords = [
            "India", "Government", "Policy", "Scheme", "Development",
            "Economy", "Technology", "Health", "Education", "Agriculture"
        ]
        tags = []
        title_lower = title.lower()
        
        for keyword in keywords:
            if keyword.lower() in title_lower:
                tags.append(keyword)
        
        return tags[:5]  # Limit to 5 tags
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse RSS date format"""
        try:
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT")
        except:
            return datetime.utcnow()


class FederalRegisterService:
    """US Federal Register API Service"""
    
    def __init__(self):
        self.base_url = "https://www.federalregister.gov/api/v1"
        self.source = "federal_register"
        self.country = "us"
    
    def fetch_documents(self, document_type: str = "all", limit: int = 50) -> List[Dict]:
        """Fetch latest documents from Federal Register"""
        articles = []
        try:
            # Map document types
            type_mapping = {
                "all": "",
                "rule": "rules",
                "proposed_rule": "proposed_rules", 
                "notice": "notices",
                "presidential": "presidential_documents"
            }
            
            endpoint = type_mapping.get(document_type, "")
            url = f"{self.base_url}/{endpoint}" if endpoint else f"{self.base_url}/documents"
            
            params = {
                "per_page": limit,
                "order": "newest",
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            documents = data.get("documents", []) if isinstance(data, dict) else data
            
            for doc in documents[:limit]:
                article = {
                    "title": doc.get("title", "Untitled"),
                    "description": doc.get("abstract", "")[:500],
                    "content": doc.get("abstract", ""),
                    "source": self.source,
                    "country": self.country,
                    "category": self._categorize(doc.get("title", "")),
                    "url": doc.get("html_url", doc.get("url", "")),
                    "published_at": self._parse_date(doc.get("publication_date", "")),
                    "impact_score": self._calculate_impact(doc),
                    "tags": doc.get("topics", [])[:5],
                    "article_metadata": {
                        "document_type": doc.get("type", "unknown"),
                        "agency": doc.get("agency", "Unknown"),
                        "docket_number": doc.get("docket_number", "")
                    }
                }
                articles.append(article)
                
        except Exception as e:
            print(f"Error fetching Federal Register data: {e}")
        
        return articles
    
    def _categorize(self, title: str) -> str:
        """Categorize document based on title"""
        title_lower = title.lower()
        categories = {
            "regulation": ["regulation", "rule", "compliance", "enforcement"],
            "economy": ["economic", "trade", "tariff", "finance", "budget"],
            "health": ["health", "fda", "medical", "healthcare"],
            "environment": ["environment", "epa", "climate", "emission"],
            "labor": ["labor", "employment", "worker", "wage"],
            "technology": ["technology", "telecom", "fcc", "digital"],
            "agriculture": ["agriculture", "usda", "food", "farm"],
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        return "general"
    
    def _calculate_impact(self, doc: Dict) -> int:
        """Calculate impact score for document"""
        score = 0
        doc_type = doc.get("type", "")
        
        # Document type impact
        if doc_type == "rule":
            score += 3
        elif doc_type == "proposed_rule":
            score += 2
        elif doc_type == "presidential_document":
            score += 5
        
        # Agency impact
        high_impact_agencies = [
            "Department of the Treasury",
            "Federal Reserve",
            "Environmental Protection Agency",
            "Department of Health and Human Services",
            "Securities and Exchange Commission"
        ]
        
        if doc.get("agency") in high_impact_agencies:
            score += 3
        
        return min(score, 10)
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return datetime.utcnow()


class GovInfoService:
    """US GovInfo API Service"""
    
    def __init__(self):
        self.base_url = "https://www.govinfo.gov/api"
        self.source = "govinfo"
        self.country = "us"
    
    def fetch_bills(self, limit: int = 30) -> List[Dict]:
        """Fetch latest congressional bills"""
        articles = []
        try:
            # Using public endpoints
            url = f"{self.base_url}/bills"
            params = {"limit": limit}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Process bills data
                for bill in data.get("bills", [])[:limit]:
                    article = {
                        "title": bill.get("title", "Untitled Bill"),
                        "description": bill.get("summary", "")[:500],
                        "content": bill.get("summary", ""),
                        "source": self.source,
                        "country": self.country,
                        "category": "legislation",
                        "url": bill.get("url", ""),
                        "published_at": datetime.utcnow(),
                        "impact_score": 7,
                        "tags": [bill.get("congress", ""), bill.get("type", "")],
                        "article_metadata": {
                            "bill_number": bill.get("billNumber", ""),
                            "congress": bill.get("congress", "")
                        }
                    }
                    articles.append(article)
        except Exception as e:
            print(f"Error fetching GovInfo data: {e}")
        
        return articles


class DataGovInService:
    """India Open Government Data Platform"""
    
    def __init__(self):
        self.base_url = "https://api.data.gov.in"
        self.source = "data_gov_in"
        self.country = "in"
        self.api_key = ""  # Users need to register for API key
    
    def fetch_datasets(self, category: str = "all", limit: int = 30) -> List[Dict]:
        """Fetch dataset information from data.gov.in"""
        articles = []
        # Note: This requires API key registration
        # For demo, we'll return placeholder structure
        return articles
    
    def set_api_key(self, api_key: str):
        """Set API key for authenticated requests"""
        self.api_key = api_key


# Main Government Intelligence Service
class GovernmentIntelligenceService:
    """Unified service for all government data sources"""
    
    def __init__(self):
        self.pib = PIBService()
        self.federal_register = FederalRegisterService()
        self.govinfo = GovInfoService()
        self.data_gov_in = DataGovInService()
    
    def fetch_all(self, country: str = "all", limit_per_source: int = 25) -> List[Dict]:
        """Fetch from all available sources"""
        all_articles = []
        
        if country in ["all", "in"]:
            pib_articles = self.pib.fetch_press_releases(limit=limit_per_source)
            all_articles.extend(pib_articles)
        
        if country in ["all", "us"]:
            fr_articles = self.federal_register.fetch_documents(limit=limit_per_source)
            all_articles.extend(fr_articles)
            
            # govinfo_articles = self.govinfo.fetch_bills(limit=limit_per_source)
            # all_articles.extend(govinfo_articles)
        
        # Sort by published date
        all_articles.sort(
            key=lambda x: x.get("published_at", datetime.utcnow()),
            reverse=True
        )
        
        return all_articles
    
    def fetch_by_category(self, category: str, limit: int = 20) -> List[Dict]:
        """Fetch articles by category"""
        all_articles = self.fetch_all()
        filtered = [
            article for article in all_articles 
            if article.get("category", "").lower() == category.lower()
        ]
        return filtered[:limit]
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Search across all government sources"""
        all_articles = self.fetch_all()
        query_lower = query.lower()
        
        results = [
            article for article in all_articles
            if (query_lower in article.get("title", "").lower() or
                query_lower in article.get("description", "").lower() or
                query_lower in " ".join(article.get("tags", [])))
        ]
        
        return results[:limit]


# Singleton instance
gov_intelligence = GovernmentIntelligenceService()
