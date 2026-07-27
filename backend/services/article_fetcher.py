"""
Article Content Fetcher - Proprietary Intelligence Reconstruction Engine
Now with fallback methods for paywalled/JavaScript sites, and disk-based cache.
"""
import requests
from typing import Dict, Optional, List
import re
from newspaper import Article as NewsArticle
from datetime import datetime
from bs4 import BeautifulSoup
import urllib.parse
import sqlite3
import json
from pathlib import Path

_CACHE_DB = Path(__file__).parent.parent / "article_cache.db"

def _db():
    conn = sqlite3.connect(str(_CACHE_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS articles (
        url TEXT PRIMARY KEY,
        payload TEXT,
        fetched_at TEXT
    )""")
    conn.commit()
    return conn

class ArticleFetcher:
    def _formalize(self, text):
        """Converts text into formal Bureau Intelligence language"""
        if not text: return ""
        # Perspective shifts: News -> Intelligence Bureau
        replacements = {
            r"\b(reported|said|stated|told reporters)\b": "official data confirms",
            r"\b(thinks|expects|believes)\b": "strategic analysis projects",
            r"\b(problem|crisis|issue)\b": "operational priority",
            r"\b(failure|mistake|error)\b": "optimization requirement",
            r"\b(huge|big|large)\b": "substantial",
            r"\b(maybe|perhaps|could)\b": "is projected to potentially",
            r"\b(spending|cost)\b": "strategic resource allocation",
            r"\b(government|they|the administration)\b": "our authorities",
            r"\b(news|article|story)\b": "intelligence stream",
            r"\b(according to)\b": "as verified by",
            r"\b(inflation)\b": "fiscal adjustment indicators",
            r"\b(unemployment)\b": "labor market stabilization data"
        }
        for pattern, replacement in replacements.items():
            text = re.compile(pattern, re.IGNORECASE).sub(replacement, text)
        return text

    def _reconstruct_content(self, raw_text: str) -> List[str]:
        """De-plagiarizes and reconstructs raw text into proprietary bureau paragraphs"""
        if not raw_text: return []
        
        # Split into raw paragraphs and filter noise
        raw_paragraphs = [p.strip() for p in raw_text.split('\n\n') if len(p.strip()) > 60]
        reconstructed = []
        
        for i, p in enumerate(raw_paragraphs):
            # Transform sentence structure: "A leads to B" -> "The alignment of A is resulting in B"
            p = p.replace(" is ", " remains positioned as ")
            p = p.replace(" has ", " maintains ")
            
            # Apply formalization
            formal_p = self._formalize(p)
            
            # Add Bureau branding every few paragraphs
            if i == 0:
                formal_p = f"PRIMARY ANALYSIS: {formal_p}"
            elif i == len(raw_paragraphs) - 1:
                formal_p = f"STRATEGIC CONCLUSION: {formal_p}"
            
            reconstructed.append(formal_p)
            
        return reconstructed

    def _generate_intelligence_brief_from_text(self, text: str, url: str) -> Dict:
        """Generate intelligence brief from raw text (when newspaper object not available)"""

        # Extract title from first line or URL
        lines = text.split('\n')
        title = lines[0][:150] if lines and len(lines[0]) > 10 else f"Intelligence Report: {url.split('/')[2]}"

        # Get more paragraphs for better context (5-7 instead of 5)
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50][:7]
        
        # Executive Summary - use first 2-3 paragraphs for better context
        summary_text = ' '.join(paragraphs[:3]) if len(paragraphs) >= 3 else ' '.join(paragraphs[:2]) if paragraphs else text[:500]

        # Executive Summary
        exec_summary = self._formalize(summary_text)

        # Critical Insights - include 4-5 insights for better understanding
        insights = []
        for p in paragraphs[1:6]:  # Get paragraphs 2-6
            if len(p) > 80:  # Only include substantial paragraphs
                formal_p = self._formalize(p)
                insights.append(formal_p)

        # Full Reconstructed Report
        full_report = self._reconstruct_content(text)

        return {
            "title": title,
            "executive_summary": exec_summary,
            "critical_insights": insights[:5],  # Return up to 5 insights
            "full_reconstructed_report": full_report,
            "strategic_outlook": "Monitoring of these proprietary data streams remains active. Authorities maintain a favorable long-term outlook based on current trajectory."
        }

    def _generate_intelligence_brief(self, article_obj: NewsArticle) -> Dict:
        """Transforms NLP and full text into our proprietary report format"""
        
        # NLP Summary
        raw_summary = article_obj.summary if hasattr(article_obj, 'summary') and article_obj.summary else ""
        if not raw_summary: raw_summary = article_obj.text[:500]

        # Executive Summary (Proprietary Tone)
        exec_summary = self._formalize(" ".join(raw_summary.split('\n')[:2]))
        
        # Insights — split by newline first, fall back to sentence splitting
        raw_insights = [s.strip() for s in raw_summary.split('\n') if len(s.strip()) > 30]
        if not raw_insights:
            import re as _re
            sentences = _re.split(r'(?<=[.!?])\s+', raw_summary)
            raw_insights = [s.strip() for s in sentences if len(s.strip()) > 30]
        formal_insights = [self._formalize(p) for p in raw_insights[:3]]
        
        # FULL RECONSTRUCTED CONTENT (De-plagiarized version of the entire article)
        full_report = self._reconstruct_content(article_obj.text)

        return {
            "executive_summary": exec_summary,
            "critical_insights": formal_insights,
            "full_reconstructed_report": full_report,
            "strategic_outlook": "Monitoring of these proprietary data streams remains active. Authorities maintain a favorable long-term outlook based on current trajectory."
        }

    def _fetch_with_google_fallback(self, url: str) -> Optional[str]:
        """
        Try to fetch article using Google's text-only version
        Works for many paywalled sites
        """
        try:
            # Use Google text-only version
            google_url = f"https://r.jina.ai/{url}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "X-With-Generated-Alt": "true"
            }
            response = requests.get(google_url, headers=headers, timeout=15)
            if response.status_code == 200 and len(response.text) > 200:
                return response.text
        except Exception as e:
            print(f"Google fallback failed: {e}")
        return None
    
    def _fetch_with_textise(self, url: str) -> Optional[str]:
        """
        Use textise dot iitty - works for many news sites
        """
        try:
            textise_url = f"https://r.jina.ai/http://{url}"
            response = requests.get(textise_url, timeout=15)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"Textise fallback failed: {e}")
        return None
    
    def _fetch_direct_with_headers(self, url: str) -> Optional[str]:
        """
        Try direct fetch with browser-like headers
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive"
            }
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extract article content
                paragraphs = soup.find_all('p')
                content = '\n\n'.join([p.get_text() for p in paragraphs if len(p.get_text()) > 50])
                return content if len(content) > 200 else None
        except Exception as e:
            print(f"Direct fetch failed: {e}")
        return None

    def _fetch_with_jina(self, url: str) -> Optional[str]:
        """Jina AI reader — best at bypassing paywalls and JS-heavy sites"""
        try:
            jina_url = f"https://r.jina.ai/{url}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/plain,text/html,*/*",
                "X-With-Generated-Alt": "true",
                "X-Return-Format": "text",
            }
            response = requests.get(jina_url, headers=headers, timeout=20)
            if response.status_code == 200 and len(response.text.strip()) > 300:
                return response.text
        except Exception as e:
            print(f"Jina fetch failed: {e}")
        return None

    def _fetch_with_curl_cffi(self, url: str) -> Optional[str]:
        """curl_cffi impersonates a real browser — bypasses Cloudflare & JS checks"""
        try:
            from curl_cffi import requests as cffi_requests
            resp = cffi_requests.get(url, impersonate="chrome120", timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer", "aside", "ads"]):
                    tag.decompose()
                # Try article/main tags first, fallback to all <p>
                container = soup.find("article") or soup.find("main") or soup
                paragraphs = container.find_all("p")
                content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
                if len(content) > 300:
                    return content
        except Exception as e:
            print(f"curl_cffi fetch failed: {e}")
        return None

    def fetch_article(self, url: str) -> Optional[Dict]:
        """Fetch with waterfall: Jina AI → curl_cffi → newspaper3k → direct headers.
        Results are cached in SQLite so repeated opens are instant."""
        try:
            with _db() as conn:
                row = conn.execute("SELECT payload FROM articles WHERE url=?", (url,)).fetchone()
                if row:
                    print(f"[Fetcher] Cache hit: {url}")
                    return json.loads(row[0])
        except Exception:
            pass

        content = None
        method_used = "unknown"

        # Method 1: Jina AI reader (best paywall bypass)
        print(f"[Fetcher] Trying Jina AI for: {url}")
        content = self._fetch_with_jina(url)
        if content:
            method_used = "jina_ai"

        # Method 2: curl_cffi browser impersonation
        if not content:
            print(f"[Fetcher] Trying curl_cffi for: {url}")
            content = self._fetch_with_curl_cffi(url)
            if content:
                method_used = "curl_cffi"

        # Method 3: newspaper3k
        if not content:
            try:
                print(f"[Fetcher] Trying newspaper3k for: {url}")
                article = NewsArticle(url)
                article.download()
                article.parse()
                try:
                    article.nlp()
                except Exception:
                    pass
                if article.text and len(article.text.strip()) > 200:
                    content = article.text
                    method_used = "newspaper3k"
            except Exception as e:
                print(f"[Fetcher] newspaper3k failed: {e}")

        # Method 4: Direct fetch with browser headers
        if not content:
            print(f"[Fetcher] Trying direct headers for: {url}")
            content = self._fetch_direct_with_headers(url)
            if content:
                method_used = "direct_headers"

        # If all methods failed
        if not content or len(content.strip()) < 200:
            print(f"All extraction methods failed for: {url}")
            return {
                'success': False,
                'url': url,
                'reason': 'Content unavailable - site blocks automated access',
                'fallback_summary': 'Article content could not be retrieved due to paywall or technical restrictions.'
            }
        
        # Process the content we got
        try:
            brief = self._generate_intelligence_brief_from_text(content, url)
            result = {
                'title': brief.get('title', 'Intelligence Report'),
                'published_date': datetime.now().isoformat(),
                'intel_brief': brief,
                'image': '',
                'success': True,
                'url': url,
                'extraction_method': method_used
            }
            try:
                with _db() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO articles (url, payload, fetched_at) VALUES (?,?,?)",
                        (url, json.dumps(result), datetime.now().isoformat())
                    )
            except Exception:
                pass
            return result
        except Exception as e:
            print(f"Processing failed after successful fetch: {e}")
            return {'success': False, 'url': url, 'reason': str(e)}

article_fetcher = ArticleFetcher()
