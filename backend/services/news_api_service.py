"""NewsAPI integration; credentials are supplied through NEWS_API_KEY."""

import os
from datetime import datetime
from typing import Dict, List, Optional

import requests


class NewsAPIService:
    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY", "")
        self.base_url = "https://newsapi.org/v2"

    def _request(self, endpoint: str, params: Dict) -> Dict:
        if not self.api_key:
            return {"status": "error", "error": "NEWS_API_KEY is not configured", "articles": []}
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                params={**params, "apiKey": self.api_key},
                headers={"X-Api-Key": self.api_key, "User-Agent": "Predovex/1.0"},
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            return {"status": "error", "error": str(exc), "articles": []}

    @staticmethod
    def _normalize(data: Dict, **metadata) -> Dict:
        articles: List[Dict] = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title", "No title"),
                "description": article.get("description", ""),
                "source": (article.get("source") or {}).get("name", "Unknown"),
                "author": article.get("author", "Unknown"),
                "url": article.get("url"),
                "url_to_image": article.get("urlToImage"),
                "published_at": article.get("publishedAt"),
                "content": (article.get("content") or "")[:500],
            })
        return {"status": "success", "total_results": data.get("totalResults", 0),
                "articles": articles, "timestamp": datetime.now().isoformat(), **metadata}

    def get_top_headlines(self, country: str = "us", category: str = "business", page_size: int = 20) -> Dict:
        data = self._request("top-headlines", {"country": country, "category": category, "pageSize": min(page_size, 100)})
        return self._normalize(data, country=country, category=category) if data.get("status") != "error" else data

    def search_everything(self, query: str, from_date: Optional[str] = None, page_size: int = 20, sort_by: str = "publishedAt") -> Dict:
        params = {"q": query, "pageSize": min(page_size, 100), "sortBy": sort_by, "language": "en"}
        if from_date:
            params["from"] = from_date
        data = self._request("everything", params)
        return self._normalize(data, query=query) if data.get("status") != "error" else data

    def get_sources(self, category: Optional[str] = None, country: str = "us") -> Dict:
        params = {"country": country}
        if category:
            params["category"] = category
        return self._request("sources", params)

    def get_government_news(self, country: str = "us", page_size: int = 20) -> Dict:
        return self.search_everything("government OR policy OR regulation", page_size=page_size)

    def get_defense_news(self, page_size: int = 20) -> Dict:
        return self.search_everything("defense OR military OR Pentagon", page_size=page_size)

    def get_pharma_news(self, page_size: int = 20) -> Dict:
        return self.search_everything("pharmaceutical OR FDA OR biotech", page_size=page_size)

    def get_tech_regulation_news(self, page_size: int = 20) -> Dict:
        return self.search_everything("technology regulation OR antitrust OR AI policy", page_size=page_size)


news_api_service = NewsAPIService()
