"""Scheduled Render jobs for the Predovex backend.

Each invocation performs one bounded task and exits. Render cron jobs are a
better fit than an infinite loop because the web service can scale and restart
independently from collection work.

Usage:
    python render_worker.py --job news
    python render_worker.py --job market
    python render_worker.py --job predictions
    python render_worker.py --job government
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")


def _write_snapshot(name: str, payload: object) -> None:
    """Write a small operational snapshot for diagnostics and later caching."""
    path = ROOT / name
    path.write_text(
        json.dumps(
            {"updated_at": datetime.utcnow().isoformat() + "Z", "data": payload},
            default=str,
            indent=2,
        )
    )


def run_news() -> dict:
    """Fetch RSS articles and persist new records in the configured database."""
    from main import SessionLocal, db_models, rss_service

    db = SessionLocal()
    added = 0
    try:
        for article in rss_service.fetch_all_feeds(country="all"):
            url = article.get("url")
            if not url or db.query(db_models.Article).filter_by(url=url).first():
                continue

            published_at = article.get("published_at")
            if published_at is not None and published_at.tzinfo:
                published_at = published_at.replace(tzinfo=None)

            db.add(
                db_models.Article(
                    title=article.get("title") or "Untitled article",
                    description=article.get("description"),
                    content=article.get("content"),
                    source=article.get("source", "RSS"),
                    country=article.get("country", "all"),
                    category=article.get("category", "general"),
                    url=url,
                    published_at=published_at,
                    sentiment=article.get("sentiment", "Neutral"),
                    impact_level=article.get("impact_level", "Low"),
                    article_metadata={
                        "ai_summary": article.get("ai_summary")
                        or article.get("description")
                        or article.get("title")
                    },
                )
            )
            added += 1

        db.commit()
        result = {"job": "news", "added": added}
        _write_snapshot("last_news_job.json", result)
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_market() -> dict:
    """Refresh the stock snapshot without blocking API requests."""
    from services.stock_data_service import stock_data_service

    snapshot = stock_data_service.get_screener()
    result = {"job": "market", "count": len(snapshot) if isinstance(snapshot, list) else 0}
    _write_snapshot("last_market_job.json", {"summary": result, "stocks": snapshot})
    return result


def run_predictions() -> dict:
    """Warm predictions for the core watchlist and save the result for review."""
    from services.stock_sentiment_service import stock_sentiment_service

    tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "XOM", "BA"]
    predictions = stock_sentiment_service.predict_batch(tickers)
    result = {"job": "predictions", "count": len(predictions) if isinstance(predictions, dict) else 0}
    _write_snapshot("last_predictions_job.json", {"summary": result, "predictions": predictions})
    return result


def run_government() -> dict:
    """Run the existing bounded government-signal collector."""
    from collect_gov_signals import main as collect_main

    # collect_gov_signals uses argparse directly from sys.argv.
    original_argv = sys.argv
    try:
        sys.argv = ["collect_gov_signals.py"]
        collect_main()
    finally:
        sys.argv = original_argv
    result = {"job": "government", "status": "completed"}
    _write_snapshot("last_government_job.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", choices=["news", "market", "predictions", "government"], required=True)
    args = parser.parse_args()

    jobs = {
        "news": run_news,
        "market": run_market,
        "predictions": run_predictions,
        "government": run_government,
    }
    result = jobs[args.job]()
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
