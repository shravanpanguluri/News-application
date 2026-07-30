"""Bounded Crawl4AI ingestion worker for Predovex.

This worker is intentionally separate from the FastAPI web process. Crawl4AI
starts a headless Chromium browser, so it must run on a crawler-sized worker,
not on Render's 512 MB Free instance.

Usage:
    CRAWL_URLS=https://example.gov/article python crawl4ai_worker.py --once

The worker only crawls URLs supplied through CRAWL_URLS and optionally checks
CRAWL_ALLOWED_DOMAINS. It does not bypass paywalls or authentication.
Set CRAWL4AI_WRITE_DB=1 to persist successful pages to the configured DB.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _configured_urls() -> list[str]:
    raw = os.getenv("CRAWL_URLS", "")
    return [url.strip() for url in raw.split(",") if url.strip()]


def _allowed(url: str) -> bool:
    allowed = {
        domain.strip().lower()
        for domain in os.getenv("CRAWL_ALLOWED_DOMAINS", "").split(",")
        if domain.strip()
    }
    if not allowed:
        return True
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


def _clean_markdown(markdown: str, limit: int = 12000) -> str:
    # Crawl4AI v0.9 may return a MarkdownGenerationResult rather than a raw
    # string, depending on the configured markdown generator.
    raw = getattr(markdown, "raw_markdown", markdown) or ""
    text = re.sub(r"\n{3,}", "\n\n", str(raw)).strip()
    return text[:limit]


def _title(markdown: str, url: str) -> str:
    for line in (markdown or "").splitlines():
        candidate = re.sub(r"^#+\s*", "", line).strip()
        if candidate and len(candidate) > 8:
            return candidate[:500]
    return urlparse(url).path.rsplit("/", 1)[-1].replace("-", " ").title() or "Crawled article"


def _article_from_result(url: str, result) -> dict:
    content = _clean_markdown(getattr(result, "markdown", "") or "")
    title = _title(content, url)
    description = next((line.strip() for line in content.splitlines() if len(line.strip()) > 40), title)
    return {
        "title": title,
        "description": description[:2000],
        "content": content,
        "source": (urlparse(url).hostname or "Crawl4AI").replace("www.", ""),
        "country": "all",
        "category": "general",
        "url": url,
        "published_at": datetime.utcnow(),
        "sentiment": "Neutral",
        "impact_level": "Low",
        "article_metadata": {
            "ingestion_method": "crawl4ai",
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        },
    }


def _persist(articles: list[dict]) -> int:
    # Imported only when DB persistence is requested, keeping dry runs light.
    from main import SessionLocal, db_models

    db = SessionLocal()
    added = 0
    try:
        for article in articles:
            if db.query(db_models.Article).filter_by(url=article["url"]).first():
                continue
            db.add(db_models.Article(**article))
            added += 1
        db.commit()
        return added
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def crawl_once(urls: list[str]) -> list[dict]:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

    browser = BrowserConfig(headless=True, java_script_enabled=True)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        word_count_threshold=20,
        page_timeout=60000,
    )
    articles = []
    async with AsyncWebCrawler(config=browser) as crawler:
        for url in urls:
            try:
                result = await crawler.arun(url=url, config=run_config)
                if getattr(result, "success", False):
                    articles.append(_article_from_result(url, result))
                    print(f"[crawl4ai] OK {url}")
                else:
                    print(f"[crawl4ai] FAILED {url}: {getattr(result, 'error_message', 'unknown error')}")
            except Exception as exc:
                print(f"[crawl4ai] ERROR {url}: {exc}")
    return articles


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one bounded crawl and exit")
    args = parser.parse_args()
    if not args.once:
        parser.error("Only --once is supported; schedule this worker externally")

    urls = [url for url in _configured_urls() if url.startswith(("http://", "https://")) and _allowed(url)]
    if not urls:
        print("[crawl4ai] No permitted URLs. Set CRAWL_URLS and optionally CRAWL_ALLOWED_DOMAINS.")
        return

    articles = asyncio.run(crawl_once(urls[: int(os.getenv("CRAWL_MAX_URLS", "10"))]))
    if os.getenv("CRAWL4AI_WRITE_DB", "0").lower() in {"1", "true", "yes"}:
        print(f"[crawl4ai] Added {_persist(articles)} new articles")
    else:
        print(f"[crawl4ai] Dry run complete: {len(articles)} articles; set CRAWL4AI_WRITE_DB=1 to persist")


if __name__ == "__main__":
    main()
