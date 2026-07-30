# Crawl4AI worker

Crawl4AI is an optional ingestion worker for pages that do not provide a
usable RSS or API feed. The existing RSS/GDELT pipeline remains the default
because it is faster and much cheaper to operate.

## Required deployment shape

Run `Dockerfile.crawler` as a separate scheduled service. Do not add
Crawl4AI to the main API image or run it on Render Free: it launches Chromium
and needs a crawler-sized machine (target at least 4 GB RAM). Configure:

```text
CRAWL_URLS=https://approved.example.gov/article-1,https://approved.example.gov/article-2
CRAWL_ALLOWED_DOMAINS=example.gov
CRAWL4AI_WRITE_DB=1
CRAWL_MAX_URLS=10
DATABASE_URL=<same PostgreSQL URL as the API>
```

The worker is bounded and exits after one run, so schedule it every 15–60
minutes. Only crawl domains whose terms and robots rules permit it. This
worker does not bypass paywalls, logins, or access controls.

## Local smoke test

```bash
pip install -r backend/requirements-crawler.txt
crawl4ai-setup
CRAWL_URLS=https://example.com python backend/crawl4ai_worker.py --once
```
