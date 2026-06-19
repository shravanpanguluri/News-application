"""
Main FastAPI Application - Predovex Intelligence Platform
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import jwt
import secrets
import asyncio
from sqlalchemy import create_engine, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext

import time
import models.models as db_models

# In-memory RSS cache — avoids re-fetching 15 feeds on every request
_rss_cache = {}  # key: (category, country) -> {"articles": [...], "ts": float}
from services.government_api import gov_intelligence
from services.rss_feed import rss_service
from services.article_fetcher import article_fetcher
from services.market_data import market_data_service
from services.analytics import analytics_service
# New API Services
from services.stock_data_service import stock_data_service
from services.finnhub_service import finnhub_service
from services.contracts_service import contracts_service
from services.news_api_service import news_api_service
from services.fred_service import fred_service
from services.policy_impact import policy_impact_predictor
from services.reddit_sentiment_service import reddit_sentiment_service
from services.stock_sentiment_service import stock_sentiment_service
from services.breaking_news_detector import breaking_news_detector
from services.news_quality import news_quality_service
from services.gdelt_service import gdelt_service
from services.alternative_news import alternative_news_service
from services.deep_analysis_service import deep_analysis_service
from services.analysis_training_collector import analysis_training_collector
from services.analysis_model_trainer import analysis_model_trainer

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./government_intelligence.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
db_models.Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# App initialization
app = FastAPI(
    title="Predovex API",
    description="Aggregates government and market intelligence",
    version="1.0.0"
)

# CORS - Allow all origins for development and production reliability
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Security
security = HTTPBearer()
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ── Prediction cache (1-hour TTL per ticker) ──────────────────────────────────
_prediction_cache: Dict[str, Dict] = {}
_CACHE_TTL = 3600  # seconds

def _cache_get(ticker: str):
    entry = _prediction_cache.get(ticker)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    return None

def _cache_set(ticker: str, data: Dict):
    _prediction_cache[ticker] = {"data": data, "ts": time.time()}

TIER_LIMITS = {
    "free": 50,
    "pro": 5000,
    "enterprise": -1
}

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    tier: str = "free"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    tier: str
    daily_limit: int

class Article(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    source: str
    country: str
    category: str
    url: str
    published_at: datetime
    impact_score: int = 0
    impact_level: str = "Low"
    sentiment: str = "Neutral"
    ai_summary: Optional[str] = None
    tags: List[str] = []

# Background Task
async def update_rss_task():
    while True:
        print(f"[{datetime.now()}] Starting background RSS fetch...")
        db = SessionLocal()
        try:
            # Increase diversity by fetching from all countries explicitly
            articles = rss_service.fetch_all_feeds(country='all')
            new_count = 0
            for art_data in articles:
                exists = db.query(db_models.Article).filter(db_models.Article.url == art_data['url']).first()
                if not exists:
                    # Handle potential datetime offset issues
                    pub_at = art_data['published_at']
                    if pub_at and pub_at.tzinfo:
                        pub_at = pub_at.replace(tzinfo=None)
                        
                    new_article = db_models.Article(
                        title=art_data['title'],
                        description=art_data['description'],
                        content=art_data['content'],
                        source=art_data['source'],
                        country=art_data['country'],
                        category=art_data['category'],
                        url=art_data['url'],
                        published_at=pub_at,
                        sentiment=art_data['sentiment'],
                        impact_level=art_data['impact_level'],
                        article_metadata={'ai_summary': art_data.get('ai_summary') or art_data.get('description') or art_data.get('title')}
                    )
                    db.add(new_article)
                    new_count += 1
            db.commit()
            
            # Delete articles older than 6 days
            stale_cutoff = datetime.now() - timedelta(days=6)
            deleted = db.query(db_models.Article).filter(
                db_models.Article.published_at < stale_cutoff
            ).delete(synchronize_session=False)
            db.commit()
            if deleted:
                print(f"[{datetime.now()}] Pruned {deleted} articles older than 6 days.")

            # Safety cap: never keep more than 2000 articles
            total = db.query(db_models.Article).count()
            if total > 2000:
                keep_ids = [i[0] for i in db.query(db_models.Article.id).order_by(db_models.Article.published_at.desc()).limit(2000).all()]
                db.query(db_models.Article).filter(~db_models.Article.id.in_(keep_ids)).delete(synchronize_session=False)
                db.commit()
            print(f"[{datetime.now()}] Added {new_count} articles. Total in DB: {db.query(db_models.Article).count()}")
        except Exception as e:
            print(f"Task Error: {e}")
            db.rollback()
        finally:
            db.close()
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    # Background RSS task — pruning old articles
    asyncio.create_task(update_rss_task())
    
    # Create default users
    try:
        db = SessionLocal()
        test_users = [
            {"email": "admin@predovex.com", "password": "password123", "tier": "enterprise"},
            {"email": "user@predovex.com", "password": "password123", "tier": "pro"},
            {"email": "free@predovex.com", "password": "password123", "tier": "free"}
        ]
        for u in test_users:
            existing = db.query(db_models.User).filter(db_models.User.email == u["email"]).first()
            if not existing:
                db.add(db_models.User(
                    email=u["email"],
                    hashed_password=pwd_context.hash(u["password"]),
                    tier=u["tier"],
                    api_key=secrets.token_urlsafe(32),
                    daily_limit=TIER_LIMITS[u["tier"]]
                ))
        db.commit()
        db.close()
    except Exception as e:
        print(f"Startup warning: {e}")
    
    print("✅ Predovex Backend Started Successfully!")
    print("📡 API Docs: http://localhost:8000/docs")
    print("🏥 Health: http://localhost:8000/health")

# Helper
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user = db.query(db_models.User).filter(db_models.User.email == email).first()
        if not user: raise HTTPException(401, "User not found")
        return user
    except: raise HTTPException(401, "Invalid token")

# Endpoints
@app.get("/")
def read_root():
    return {"message": "Predovex Intelligence API active"}

@app.post("/auth/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(db_models.User).filter(db_models.User.email == user_data.email).first():
        raise HTTPException(400, "Email registered")
    db_user = db_models.User(
        email=user_data.email,
        hashed_password=pwd_context.hash(user_data.password),
        tier=user_data.tier,
        api_key=secrets.token_urlsafe(32),
        daily_limit=TIER_LIMITS.get(user_data.tier, 50)
    )
    db.add(db_user)
    db.commit()
    return {"message": "Success"}

@app.post("/auth/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(db_models.User).filter(db_models.User.email == user_data.email).first()
    if not user or not pwd_context.verify(user_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    return {
        "access_token": create_access_token({"sub": user.email}),
        "token_type": "bearer", "tier": user.tier, "daily_limit": user.daily_limit
    }

@app.get("/user/me")
def get_me(user: db_models.User = Depends(get_current_user)):
    return {"email": user.email, "tier": user.tier, "watchlist": user.watchlist_keywords}

RSS_CACHE_TTL = 300  # seconds (5 minutes)

@app.get("/rss/all")
def get_rss_news(category: str = "all", country: str = "all", force_refresh: bool = False, use_newsapi: bool = False, limit: int = 150, db: Session = Depends(get_db)):
    """Serve from DB first (instant), refresh live cache in background"""
    # 1. Always try DB first — instant, always populated
    try:
        cutoff = datetime.now() - timedelta(days=7)
        q = db.query(db_models.Article).filter(db_models.Article.published_at >= cutoff)
        if category and category != 'all':
            q = q.filter(db_models.Article.category == category)
        if country and country != 'all':
            q = q.filter(db_models.Article.country == country)
        db_articles = q.order_by(db_models.Article.published_at.desc()).limit(limit).all()
        if db_articles:
            result = [{
                'title': a.title,
                'description': a.description or '',
                'ai_summary': a.ai_summary or a.description or '',
                'url': a.url,
                'source': a.source,
                'published_at': a.published_at.isoformat() if a.published_at else None,
                'category': a.category,
                'country': a.country,
                'sentiment': a.sentiment,
                'impact_level': a.impact_level,
                'impact_score': a.impact_score,
                'tags': a.tags if hasattr(a, 'tags') else [],
            } for a in db_articles]
            return JSONResponse(content=jsonable_encoder(result), headers={"Cache-Control": "public, max-age=120, stale-while-revalidate=60"})
    except Exception as e:
        print(f"DB fetch error: {e}")

    # 2. Fallback: in-memory cache or live RSS fetch
    cache_key = (country,)
    cached = _rss_cache.get(cache_key)
    now = time.time()
    if not force_refresh and cached and (now - cached["ts"]) < RSS_CACHE_TTL:
        articles = cached["articles"]
    else:
        try:
            articles = rss_service.fetch_all_feeds(country=country, max_age_days=7)
            _rss_cache[cache_key] = {"articles": articles, "ts": now}
        except Exception as e:
            print(f"RSS fetch error: {e}")
            articles = cached["articles"] if cached else []
    try:
        if category and category != 'all':
            articles = [a for a in articles if a.get('category', '').lower() == category.lower()]
        curated = news_quality_service.process_feed(articles, limit=limit)
        return JSONResponse(content=jsonable_encoder(curated), headers={"Cache-Control": "public, max-age=120, stale-while-revalidate=60"})
    except Exception as e:
        print(f"RSS Endpoint Error: {e}")
        return JSONResponse(content=jsonable_encoder(articles[:limit]), headers={"Cache-Control": "public, max-age=120, stale-while-revalidate=60"})

@app.get("/rss/breaking")
def get_breaking_news(limit: int = 20, db: Session = Depends(get_db)):
    """Get breaking news from DB (last 24h, highest impact first)"""
    try:
        cutoff = datetime.now() - timedelta(days=1)
        rows = db.query(db_models.Article).filter(
            db_models.Article.published_at >= cutoff
        ).order_by(db_models.Article.published_at.desc()).limit(limit * 2).all()
        if rows:
            result = [{
                'title': a.title, 'description': a.description or '',
                'url': a.url, 'source': a.source,
                'published_at': a.published_at.isoformat() if a.published_at else None,
                'category': a.category, 'country': a.country,
                'sentiment': a.sentiment, 'impact_level': a.impact_level,
            } for a in rows[:limit]]
            return JSONResponse(content=jsonable_encoder(result), headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=30"})
    except Exception as e:
        print(f"DB breaking error: {e}")
    # fallback
    articles = rss_service.fetch_all_feeds(max_age_days=1)
    return JSONResponse(content=jsonable_encoder(articles[:limit]), headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=30"})

@app.get("/rss/trending-news")
def get_trending_news(limit: int = 20, db: Session = Depends(get_db)):
    """Get trending news from DB (last 48h)"""
    try:
        cutoff = datetime.now() - timedelta(days=2)
        rows = db.query(db_models.Article).filter(
            db_models.Article.published_at >= cutoff
        ).order_by(db_models.Article.published_at.desc()).limit(limit).all()
        if rows:
            result = [{
                'title': a.title, 'description': a.description or '',
                'url': a.url, 'source': a.source,
                'published_at': a.published_at.isoformat() if a.published_at else None,
                'category': a.category, 'country': a.country,
                'sentiment': a.sentiment, 'impact_level': a.impact_level,
            } for a in rows]
            return JSONResponse(content=jsonable_encoder(result), headers={"Cache-Control": "public, max-age=120, stale-while-revalidate=60"})
    except Exception as e:
        print(f"DB trending-news error: {e}")
    articles = rss_service.fetch_all_feeds(max_age_days=2)
    return JSONResponse(content=jsonable_encoder(articles[:limit]), headers={"Cache-Control": "public, max-age=120, stale-while-revalidate=60"})

@app.get("/rss/trending")
def get_trending_topics(limit: int = 10, db: Session = Depends(get_db)):
    """Derive trending topics from DB article titles"""
    try:
        from collections import Counter
        cutoff = datetime.now() - timedelta(days=2)
        rows = db.query(db_models.Article.title).filter(
            db_models.Article.published_at >= cutoff
        ).limit(200).all()
        if rows:
            words = []
            for (title,) in rows:
                for w in (title or '').lower().split():
                    if len(w) > 4 and w.isalpha():
                        words.append(w)
            top = Counter(words).most_common(limit)
            return JSONResponse(content=jsonable_encoder([
                {'topic': w, 'count': c} for w, c in top
            ]))
    except Exception as e:
        print(f"DB trending error: {e}")
    return JSONResponse(content=jsonable_encoder([]))

@app.get("/markets/prices")
def get_market_prices():
    return market_data_service.get_market_data()

# Stock Sentiment Prediction Endpoints (ML Model)
@app.get("/markets/sentiment/predict/{ticker}")
def get_stock_sentiment_prediction(ticker: str, period: str = "3mo"):
    """
    Predict next-day stock direction using ML model
    
    Model: jacobre20/stock-sentiment-daily-v1
    Accuracy: ~52% (typical for financial ML)
    
    Args:
        ticker: Stock ticker symbol (e.g., AAPL, MSFT)
        period: Historical data period for technical indicators
        
    Returns:
        Prediction (Up/Down), probability, confidence level
    """
    result = stock_sentiment_service.predict(ticker.upper(), period)
    if not result:
        raise HTTPException(status_code=503, detail="Model not available or loading failed")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/markets/sentiment/batch")
def get_batch_sentiment(tickers: str = Query(..., description="Comma-separated ticker symbols")):
    """
    Get sentiment predictions for multiple stocks
    
    Args:
        tickers: Comma-separated list (e.g., AAPL,MSFT,GOOGL)
        
    Returns:
        Batch predictions with bullish/bearish counts
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    result = stock_sentiment_service.predict_batch(ticker_list)
    return result

@app.get("/markets/sentiment/sector/{sector}")
def get_sector_sentiment(sector: str):
    """
    Get sector-level sentiment aggregation
    
    Sectors: Technology, Healthcare, Finance, Energy, Defense, Consumer
    """
    sector_stocks = {
        "technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META"],
        "healthcare": ["JNJ", "PFE", "MRK", "ABBV", "TMO"],
        "finance": ["JPM", "BAC", "WFC", "GS", "MS"],
        "energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "defense": ["LMT", "RTX", "BA", "NOC", "GD"],
        "consumer": ["AMZN", "TSLA", "HD", "PG", "KO"]
    }
    
    sector_lower = sector.lower()
    if sector_lower not in sector_stocks:
        raise HTTPException(
            status_code=400, 
            detail=f"Sector '{sector}' not found. Available: {list(sector_stocks.keys())}"
        )
    
    result = stock_sentiment_service.get_sector_sentiment({sector: sector_stocks[sector_lower]})
    return result

@app.get("/markets/sentiment/all-sectors")
def get_all_sector_sentiment():
    """
    Get sentiment for all sectors at once
    
    Returns aggregated bullish/bearish signals across all sectors
    """
    sector_stocks = {
        "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META"],
        "Healthcare": ["JNJ", "PFE", "MRK", "ABBV", "TMO"],
        "Finance": ["JPM", "BAC", "WFC", "GS", "MS"],
        "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "Defense": ["LMT", "RTX", "BA", "NOC", "GD"],
        "Consumer": ["AMZN", "TSLA", "HD", "PG", "KO"]
    }
    
    result = stock_sentiment_service.get_sector_sentiment(sector_stocks)
    return result

@app.get("/markets/sentiment/model-info")
def get_model_info():
    """
    Get information about the sentiment prediction model
    """
    return {
        "model_id": "jacobre20/stock-sentiment-daily-v1",
        "type": "Tabular Classification (scikit-learn/skops)",
        "task": "Next-day stock direction prediction (Up/Down)",
        "features": [
            "Returns (1d, 5d, 10d, 20d)",
            "Volatility (5d, 10d, 20d)",
            "RSI (14-day)",
            "MACD",
            "Bollinger Bands %B",
            "SMA Ratios",
            "SPY market return"
        ],
        "performance": {
            "accuracy": "~52%",
            "auc": "~0.523",
            "f1_score": "~0.68"
        },
        "license": "Apache 2.0",
        "disclaimer": "NOT financial advice. For informational purposes only."
    }

# Enhanced Stock Sentiment Endpoints - Trading Signals & Portfolio
@app.get("/markets/sentiment/top-picks")
def get_top_stock_picks(
    tickers: str = Query(..., description="Comma-separated ticker symbols"),
    limit: int = Query(10, description="Number of top picks to return")
):
    """
    Get top stock picks ranked by probability and signal strength
    
    Returns bullish and bearish picks with trading signals (STRONG BUY/BUY/HOLD/SELL/STRONG SELL)
    
    Args:
        tickers: Comma-separated list of stocks to analyze
        limit: Number of top picks to return (default: 10)
        
    Returns:
        Ranked bullish and bearish picks with signals
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    result = stock_sentiment_service.get_top_picks(ticker_list, limit)
    return result

@app.get("/markets/sentiment/portfolio")
def get_model_portfolio(
    tickers: str = Query(..., description="Comma-separated ticker symbols"),
    risk_profile: str = Query("balanced", description="Risk profile: conservative, balanced, or aggressive")
):
    """
    Generate model portfolio with allocation percentages based on sentiment predictions
    
    Args:
        tickers: Universe of stocks to consider
        risk_profile: Investment risk tolerance
        
    Returns:
        Portfolio with stock allocations weighted by signal strength
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    
    if risk_profile not in ["conservative", "balanced", "aggressive"]:
        raise HTTPException(status_code=400, detail="Invalid risk_profile. Use: conservative, balanced, or aggressive")
    
    result = stock_sentiment_service.get_model_portfolio(ticker_list, risk_profile)
    return result

@app.get("/markets/sentiment/backtest")
def backtest_trading_strategy(
    tickers: str = Query(..., description="Comma-separated ticker symbols"),
    days: int = Query(30, description="Number of days to backtest"),
    initial_capital: float = Query(10000, description="Starting capital for backtest")
):
    """
    Backtest ML-based trading strategy with performance metrics
    
    Calculates:
    - Total return and profit/loss
    - Win rate (percentage of profitable days)
    - Sharpe ratio (risk-adjusted returns)
    - Maximum drawdown (worst peak-to-trough decline)
    - Alpha vs S&P 500 benchmark
    
    Args:
        tickers: Stocks to include in backtest
        days: Backtest period in days
        initial_capital: Starting portfolio value
        
    Returns:
        Comprehensive backtest results with performance metrics
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    
    if days < 7 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 7 and 365")
    
    result = stock_sentiment_service.backtest_strategy(ticker_list, days, initial_capital)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.get("/markets/sentiment/signals/{ticker}")
def get_trading_signal(ticker: str):
    """
    Get detailed trading signal for a single stock
    
    Signal categories:
    - STRONG BUY: Probability > 65%
    - BUY: Probability 55-65%
    - HOLD: Probability 45-55%
    - SELL: Probability 35-45%
    - STRONG SELL: Probability < 35%
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Trading signal with strength indicator
    """
    result = stock_sentiment_service.predict(ticker.upper())
    
    if not result:
        raise HTTPException(status_code=503, detail="Model not available")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Add signal strength if not already present
    if "signal_strength" not in result:
        proba = result.get("probability", 0.5)
        if proba >= 0.5:
            result["signal_strength"] = round((proba - 0.5) * 200, 2)
        else:
            result["signal_strength"] = round((0.5 - proba) * 200, 2)
    
    return result

# Alternative Free News APIs (No API Key Required)
@app.get("/alternative/spaceflight")
def get_spaceflight_news(limit: int = 50):
    """Get spaceflight/aerospace news (unlimited, no API key)"""
    articles = alternative_news_service.get_spaceflight_news(limit=limit)
    return {'articles': articles, 'total': len(articles), 'source': 'Spaceflight News API'}

@app.get("/alternative/wikipedia")
def get_wikipedia_events(days: int = 7):
    """Get current events from Wikipedia (unlimited, no API key)"""
    articles = alternative_news_service.get_wikipedia_current_events(days=days)
    return {'articles': articles, 'total': len(articles), 'source': 'Wikipedia Current Events'}

@app.get("/alternative/all")
def get_all_alternative(limit: int = 50, days: int = 3):
    """Get all alternative news sources"""
    articles = alternative_news_service.get_all_alternative_news(
        spaceflight_limit=limit,
        wiki_days=days
    )
    return {'articles': articles, 'total': len(articles), 'sources': ['Spaceflight', 'Wikipedia']}

# GDELT Unlimited News API Endpoints
@app.get("/gdelt/search")
def gdelt_search(
    q: str = "",
    days: int = 1,
    limit: int = 100
):
    """Search GDELT unlimited news database"""
    try:
        articles = gdelt_service.search_news(query=q, timespan=days, max_results=limit)
        return {
            'query': q,
            'articles': articles,
            'total': len(articles),
            'source': 'GDELT'
        }
    except Exception as e:
        return {'error': str(e)}

@app.get("/gdelt/trending")
def get_gdelt_trending(
    days: int = 1,
    limit: int = 20
):
    """Get trending topics from GDELT global news analysis"""
    try:
        trending = gdelt_service.get_trending_topics(timespan=days)
        return {
            'trending_topics': trending[:limit],
            'total': len(trending),
            'source': 'GDELT',
            'timespan_days': days
        }
    except Exception as e:
        return {'error': str(e)}

@app.get("/gdelt/category/{category}")
def get_gdelt_category_news(
    category: str,
    limit: int = 50
):
    """Get news by category from GDELT (technology, politics, business, health, etc.)"""
    try:
        articles = gdelt_service.get_news_by_category(category=category, max_results=limit)
        return {
            'category': category,
            'articles': articles,
            'total': len(articles),
            'source': 'GDELT'
        }
    except Exception as e:
        return {'error': str(e)}

# NewsAPI endpoints disabled for demo stability - using RSS feeds instead
# @app.get("/newsapi/headlines")
# def get_newsapi_headlines(country: str = "us", category: str = "business"):
#     """Get top headlines from NewsAPI"""
#     result = news_api_service.get_top_headlines(country=country, category=category)
#     return result

# @app.get("/newsapi/search")
# def search_newsapi(q: str, days: int = 7):
#     """Search NewsAPI with custom query"""
#     from datetime import datetime, timedelta
#     from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
#     result = news_api_service.search_everything(query=q, from_date=from_date)
#     return result

# @app.get("/newsapi/government")
# def get_government_news(country: str = "us"):
#     """Get government and policy news from NewsAPI"""
#     result = news_api_service.get_government_news(country=country)
#     return result

@app.get("/policy/analyze")
def analyze_policy_impact(title: str, description: Optional[str] = ""):
    """
    Analyze government policy and predict market impact
    
    Args:
        title: Policy title/announcement
        description: Policy description (optional)
    
    Returns:
        Impact prediction with affected sectors and stocks
    """
    result = policy_impact_predictor.analyze_policy(title, description or "")
    return result

@app.get("/policy/sectors")
def get_sector_mappings():
    """Get all sector keywords and stock mappings"""
    return {
        'sectors': list(policy_impact_predictor.SECTOR_KEYWORDS.keys()),
        'sector_stocks': policy_impact_predictor.SECTOR_STOCKS,
        'historical_patterns': policy_impact_predictor.HISTORICAL_PATTERNS
    }

@app.get("/policy/recent")
def get_recent_policy_analysis(db: Session = Depends(get_db)):
    """Get recent policy analyses from database"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=30)
    
    # Get recent articles with high impact
    articles = db.query(db_models.Article).filter(
        db_models.Article.impact_level == 'High',
        db_models.Article.published_at >= cutoff
    ).order_by(db_models.Article.published_at.desc()).limit(20).all()
    
    # Analyze each with policy impact predictor
    analyzed = []
    for article in articles:
        analysis = policy_impact_predictor.analyze_policy(
            article.title,
            article.description or ""
        )
        if analysis['impact_score'] >= 40:  # Only medium+ impact
            analyzed.append({
                'article': {
                    'title': article.title,
                    'url': article.url,
                    'published_at': article.published_at,
                    'source': article.source
                },
                'analysis': analysis
            })
    
    return {'policies': analyzed[:10]}

@app.get("/search")
def search_articles(
    q: str,
    category: Optional[str] = None,
    country: Optional[str] = None,
    days: int = 7,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Advanced search with filters
    
    Args:
        q: Search query
        category: Filter by category (optional)
        country: Filter by country (optional)
        days: Search last N days (default 7)
        limit: Max results (default 20)
    """
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days)
    
    # Search database
    query = db.query(db_models.Article).filter(
        db_models.Article.published_at >= cutoff
    )
    
    # Apply filters
    if category and category != 'all':
        query = query.filter(db_models.Article.category == category)
    
    if country and country != 'all':
        query = query.filter(db_models.Article.country == country)
    
    # Full-text search in title and description
    articles = query.all()
    
    # Filter by search query
    search_terms = q.lower().split()
    filtered = []
    
    for article in articles:
        text = f"{article.title} {article.description or ''}".lower()
        # Match if at least 2 search terms found
        matches = sum(1 for term in search_terms if term in text)
        if matches >= min(2, len(search_terms)):
            filtered.append({
                'title': article.title,
                'description': article.description,
                'url': article.url,
                'source': article.source,
                'published_at': article.published_at,
                'category': article.category,
                'country': article.country,
                'sentiment': article.sentiment,
                'impact_level': article.impact_level,
                'match_score': matches
            })
    
    # Sort by match score and recency
    filtered.sort(key=lambda x: (x['match_score'], x['published_at']), reverse=True)
    
    return {
        'query': q,
        'results': filtered[:limit],
        'total_found': len(filtered),
        'search_params': {
            'category': category,
            'country': country,
            'days': days
        }
    }

@app.post("/user/track/read")
def track_article_read(
    article_id: str,
    category: str,
    topics: Optional[List[str]] = None,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Track article reads for personalization
    
    Args:
        article_id: Article identifier
        category: Article category
        topics: Extracted topics/keywords
    """
    from datetime import datetime
    
    # Create or update reading history
    history = db_models.ReadingHistory(
        user_id=user.id,
        article_id=article_id,
        category=category,
        topics=topics or [],
        read_at=datetime.now()
    )
    
    db.add(history)
    db.commit()
    
    return {'status': 'success', 'message': 'Reading history updated'}

@app.get("/user/recommendations")
def get_personalized_recommendations(
    limit: int = 20,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized article recommendations based on reading history
    """
    from datetime import datetime, timedelta
    
    # Get user's reading history (last 30 days)
    cutoff = datetime.now() - timedelta(days=30)
    history = db.query(db_models.ReadingHistory).filter(
        db_models.ReadingHistory.user_id == user.id,
        db_models.ReadingHistory.read_at >= cutoff
    ).all()
    
    # Extract user interests
    categories = [h.category for h in history]
    all_topics = []
    for h in history:
        all_topics.extend(h.topics or [])
    
    # Count frequencies
    from collections import Counter
    category_counts = Counter(categories)
    topic_counts = Counter(all_topics)
    
    # Get top interests
    top_categories = [cat for cat, count in category_counts.most_common(5)]
    top_topics = [topic for topic, count in topic_counts.most_common(10)]
    
    # Get recent articles
    articles = db.query(db_models.Article).filter(
        db_models.Article.published_at >= cutoff
    ).order_by(db_models.Article.published_at.desc()).limit(100).all()
    
    # Convert to dicts
    article_dicts = [
        {
            'title': a.title,
            'description': a.description or '',
            'url': a.url,
            'source': a.source,
            'published_at': a.published_at,
            'category': a.category,
            'country': a.country
        }
        for a in articles
    ]
    
    # Get personalized feed
    user_interests = top_categories + top_topics
    personalized = news_quality_service.get_personalized_feed(
        article_dicts,
        user_history=user_interests,
        limit=limit
    )
    
    return {
        'recommendations': personalized,
        'based_on': {
            'categories': top_categories,
            'topics': top_topics[:5]
        },
        'history_count': len(history)
    }

@app.get("/breaking-news")
def get_breaking_news(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get intelligent breaking news ranked by multi-signal analysis
    
    Signals analyzed:
    - Recency (0-20 points)
    - Cross-source validation (0-25 points)
    - Keyword detection (0-20 points)
    - Source authority (0-15 points)
    - Reddit trending (0-10 points)
    - Market impact potential (0-10 points)
    """
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=6)  # Last 6 hours for breaking
    
    # Get recent articles from database
    articles = db.query(db_models.Article).filter(
        db_models.Article.published_at >= cutoff
    ).order_by(db_models.Article.published_at.desc()).limit(200).all()
    
    # Convert to dict format
    article_dicts = [
        {
            'title': a.title,
            'description': a.description or '',
            'url': a.url,
            'source': a.source,
            'published_at': a.published_at,
            'category': a.category,
            'country': a.country
        }
        for a in articles
    ]
    
    # Analyze with breaking news detector
    breaking = breaking_news_detector.get_breaking_news(article_dicts, limit=limit)
    
    return {
        'breaking_news': breaking,
        'analyzed_count': len(article_dicts),
        'breaking_count': len([a for a in breaking if a.get('breaking_score', 0) >= 70]),
        'timestamp': datetime.now().isoformat()
    }

@app.get("/trending-topics")
def get_trending_topics():
    """Get trending topics from breaking news analysis"""
    # Get recent articles
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=12)
    
    # This would query from database - for now return sample
    sample_articles = []  # Would fetch from DB
    
    trending = breaking_news_detector.get_trending_topics(sample_articles)
    
    return {
        'trending_topics': trending,
        'timestamp': datetime.now().isoformat()
    }

@app.post("/breaking-news/analyze")
def analyze_article_breaking_potential(title: str, description: Optional[str] = ""):
    """
    Analyze a single article for breaking news potential
    
    Returns detailed signal breakdown
    """
    article = {
        'title': title,
        'description': description or '',
        'source': 'User Submitted',
        'published_at': datetime.now()
    }
    
    # Analyze with all signals
    analysis = breaking_news_detector.calculate_breaking_score(article, [article])
    
    return {
        'article': article,
        'breaking_score': analysis['score'],
        'is_breaking': analysis['score'] >= 70,
        'signal_breakdown': analysis['signals'],
        'recommendation': 'PROMOTE' if analysis['score'] >= 70 else 'STANDARD' if analysis['score'] >= 50 else 'NORMAL'
    }

@app.get("/article/fetch")
def fetch_article_content(url: str):
    try:
        result = article_fetcher.fetch_article(url)
        return JSONResponse(content=jsonable_encoder(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/watchlist/news")
def get_watchlist_news(user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    kw = user.watchlist_keywords or []
    if not kw: return []
    articles = db.query(db_models.Article).filter(or_(*[db_models.Article.title.contains(k) for k in kw])).order_by(db_models.Article.published_at.desc()).all()
    result = [{'title': a.title, 'description': a.description, 'url': a.url, 'source': a.source, 'published_at': a.published_at, 'category': a.category, 'country': a.country, 'sentiment': a.sentiment, 'impact_level': a.impact_level, 'ai_summary': a.article_metadata.get('ai_summary') if a.article_metadata else None} for a in articles]
    return JSONResponse(content=jsonable_encoder(result))

@app.post("/user/watchlist")
def add_watchlist(keyword: str, user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    kw = user.watchlist_keywords or []
    if keyword not in kw:
        kw.append(keyword)
        user.watchlist_keywords = kw
        db.commit()
    return kw

@app.get("/api/market/ticker")
async def get_market_ticker():
    return market_data_service.get_live_ticker()

@app.get("/api/analytics/trends")
async def get_analytics_trends(days: int = 30, db: Session = Depends(get_db)):
    try:
        data = analytics_service.get_impact_trends(db, days)
        return JSONResponse(content=jsonable_encoder(data))
    except Exception as e:
        print(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health(): 
    return {"status": "healthy"}

# ========================================
# NEW API ENDPOINTS - Stock Data (yfinance)
# ========================================

@app.get("/api/stock/{ticker}/price")
def get_stock_price(ticker: str):
    """Get real-time stock price and metrics"""
    return stock_data_service.get_stock_price(ticker)

@app.get("/api/stock/{ticker}/info")
def get_stock_info(ticker: str):
    """Get company information and fundamentals"""
    return stock_data_service.get_stock_info(ticker)

@app.get("/api/stock/{ticker}/historical")
def get_stock_historical(ticker: str, period: str = '1mo'):
    """Get historical stock prices"""
    return stock_data_service.get_historical_data(ticker, period)

@app.get("/api/stock/{ticker}/deep-dive")
def get_stock_deep_dive(ticker: str):
    """Comprehensive stock data: price, fundamentals, analyst consensus"""
    data = stock_data_service.get_deep_dive(ticker)
    if data.get('error'):
        return data
    # Overlay real Finnhub analyst data if API key is configured
    if finnhub_service.available:
        rec = finnhub_service.get_recommendations(ticker)
        pt  = finnhub_service.get_price_target(ticker)
        if rec:
            data['analysts']['buy']  = rec['buy']
            data['analysts']['hold'] = rec['hold']
            data['analysts']['sell'] = rec['sell']
            data['analysts']['period'] = rec.get('period', '')
        if pt:
            if pt.get('target'):      data['analysts']['target']      = pt['target']
            if pt.get('target_high'): data['analysts']['target_high'] = pt['target_high']
            if pt.get('target_low'):  data['analysts']['target_low']  = pt['target_low']
        data['finnhub_news'] = finnhub_service.get_company_news(ticker)
        data['next_earnings'] = finnhub_service.get_earnings(ticker)
    return data

@app.get("/api/stocks/screener")
def get_stocks_screener():
    """Live prices for 90+ popular stocks organised by category"""
    return stock_data_service.get_screener()

@app.get("/api/stock/market-movers/{sector}")
def get_market_movers(sector: str = 'technology'):
    """Get top stocks in a sector"""
    return stock_data_service.get_market_movers(sector)

# ========================================
# NEW API ENDPOINTS - Federal Contracts
# ========================================

@app.get("/api/contracts/{company}")
def get_company_contracts(company: str):
    """Get federal contracts for a specific company"""
    return contracts_service.get_contracts(company)

@app.get("/api/contracts/defense/latest")
def get_defense_contracts(limit: int = 50):
    """Get latest Department of Defense contracts"""
    return contracts_service.get_defense_contracts(limit)

@app.get("/api/contracts/agency/{agency}")
def get_agency_contracts(agency: str, limit: int = 50):
    """Get contracts for a specific government agency"""
    return contracts_service.get_contracts_by_agency(agency, limit)

@app.get("/api/contracts/top-contractors")
def get_top_contractors(limit: int = 20):
    """Get top government contractors by award amount"""
    return contracts_service.get_top_contractors(limit)

# ========================================
# NEW API ENDPOINTS - NewsAPI
# ========================================

@app.get("/api/news/headlines")
def get_news_headlines(country: str = 'us', category: str = 'business'):
    """Get top headlines by country and category"""
    return news_api_service.get_top_headlines(country, category)

@app.get("/api/news/search")
def search_news(query: str, from_date: Optional[str] = None):
    """Search news across all sources"""
    return news_api_service.search_everything(query, from_date)

@app.get("/api/news/sources")
def get_news_sources(category: Optional[str] = None):
    """Get list of available news sources"""
    return news_api_service.get_sources(category)

@app.get("/api/news/government")
def get_government_news():
    """Get government and policy news"""
    return news_api_service.get_government_news()

@app.get("/api/news/defense")
def get_defense_news():
    """Get defense and military news"""
    return news_api_service.get_defense_news()

@app.get("/api/news/pharma")
def get_pharma_news():
    """Get pharmaceutical and FDA news"""
    return news_api_service.get_pharma_news()

@app.get("/api/news/tech-regulation")
def get_tech_regulation_news():
    """Get technology regulation news"""
    return news_api_service.get_tech_regulation_news()

# ========================================
# NEW API ENDPOINTS - Reddit Sentiment
# ========================================

@app.get("/api/sentiment/reddit/{ticker}")
def get_reddit_sentiment(ticker: str):
    """Get stock sentiment from Reddit discussions"""
    return reddit_sentiment_service.get_stock_sentiment(ticker)

@app.get("/api/sentiment/trending")
def get_trending_stocks():
    """Get trending stocks on Reddit"""
    return reddit_sentiment_service.get_trending_stocks()

@app.get("/api/sentiment/sector/{sector}")
def get_sector_sentiment(sector: str):
    """Get sentiment for a specific sector"""
    return reddit_sentiment_service.get_sector_sentiment(sector)

@app.get("/api/sentiment/search")
def search_reddit_discussions(query: str):
    """Search Reddit for specific topics"""
    return reddit_sentiment_service.search_discussions(query)

# ========================================
# NEW API ENDPOINTS - FRED Economic Data
# ========================================

@app.get("/api/economic/all")
def get_all_economic_indicators():
    """Get all major economic indicators"""
    return fred_service.get_all_major_indicators()

@app.get("/api/economic/interest-rate")
def get_interest_rate():
    """Get Federal Funds interest rate"""
    return fred_service.get_interest_rate()

@app.get("/api/economic/gdp")
def get_gdp():
    """Get GDP data"""
    return fred_service.get_gdp()

@app.get("/api/economic/cpi")
def get_cpi():
    """Get Consumer Price Index (inflation)"""
    return fred_service.get_cpi()

@app.get("/api/economic/unemployment")
def get_unemployment():
    """Get unemployment rate"""
    return fred_service.get_unemployment_rate()

@app.get("/api/economic/treasury/{maturity}")
def get_treasury_yield(maturity: str = '10y'):
    """Get Treasury yield (3m, 2y, 10y)"""
    return fred_service.get_treasury_yield(maturity)

@app.get("/api/economic/yield-curve")
def get_yield_curve():
    """Get 10Y-2Y Treasury spread"""
    return fred_service.get_yield_curve_spread()

@app.get("/api/economic/markets")
def get_market_indicators():
    """Get market-related economic indicators"""
    return fred_service.get_market_indicators()

@app.get("/api/economic/inflation")
def get_inflation_data():
    """Get comprehensive inflation data"""
    return fred_service.get_inflation_data()

@app.get("/api/economic/labor")
def get_labor_market_data():
    """Get labor market indicators"""
    return fred_service.get_labor_market_data()

# ============================================================================
# TICKER MAPPING ENDPOINTS (Patent-Critical)
# ============================================================================

@app.get("/api/mapping/ticker/{company_name}")
def get_ticker_for_company(company_name: str):
    """
    Get stock ticker for a company name
    """
    from services.ticker_mapper import ticker_mapper
    ticker = ticker_mapper.get_ticker(company_name)
    return {
        "company_name": company_name,
        "ticker": ticker,
        "status": "found" if ticker else "not_found"
    }

@app.post("/api/mapping/add")
def add_ticker_mapping(company_name: str, ticker: str):
    """
    Manually add a company-to-ticker mapping
    """
    from services.ticker_mapper import ticker_mapper
    ticker_mapper.add_mapping(company_name, ticker)
    return {
        "status": "success",
        "company_name": company_name,
        "ticker": ticker
    }

# ============================================================================
# INDIA GOVERNMENT INTELLIGENCE ENDPOINTS (Patent Differentiator)
# ============================================================================

@app.get("/api/india/notifications")
def get_india_notifications(limit: int = 10):
    """
    Get latest Indian government notifications (PIB)
    """
    from services.india_gov_service import india_gov_service
    return india_gov_service.get_latest_notifications(limit)

@app.get("/api/india/rbi-actions")
def get_india_rbi_actions(limit: int = 5):
    """
    Get latest RBI regulatory actions
    """
    from services.india_gov_service import india_gov_service
    return india_gov_service.get_rbi_actions(limit)

# ============================================================================
# USASPENDING.GOV INTEGRATION ENDPOINTS (Patent-Critical)
# ============================================================================

@app.get("/api/usaspending/contracts/{ticker}")
def get_contracts_for_ticker(ticker: str, company_name: Optional[str] = None, limit: int = 50):
    """
    Get federal contract awards for a company by ticker
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_contract_awards_for_ticker(ticker, company_name, limit)

@app.get("/api/usaspending/trends/{ticker}")
def get_contract_trends(ticker: str, company_name: Optional[str] = None):
    """
    Get federal contract flow trends for a company
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_contract_flow_trends(ticker, company_name)

@app.get("/api/usaspending/agencies/{company_name}")
def get_agency_spending(company_name: str, limit: int = 50):
    """
    Get federal agency spending breakdown for a company
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_agency_spending_by_company(company_name, limit)

@app.get("/api/usaspending/top-contractors")
def get_top_contractors(limit: int = 50):
    """
    Get top federal contractors
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_top_federal_contractors(limit)

# ============================================================================
# CORRELATION TRACKING ENDPOINTS (Patent-Critical)
# ============================================================================

@app.get("/api/foia/recent")
def get_recent_foia_releases(agency: Optional[str] = None, limit: int = 50):
    """
    Get recently completed FOIA requests from MuckRock
    
    Args:
        agency: Filter by agency name (optional)
        limit: Number of results (default 50)
    
    Returns:
        List of recent FOIA releases
    """
    from services.foia_engine import foia_engine
    return foia_engine.get_recent_foia_releases(agency=agency, limit=limit)

@app.get("/api/foia/company/{company_name}")
def search_foia_by_company(company_name: str, limit: int = 50):
    """
    Search FOIA requests mentioning a specific company
    
    Args:
        company_name: Company name to search for
        limit: Max results
    
    Returns:
        List of FOIA requests mentioning the company
    """
    from services.foia_engine import foia_engine
    return foia_engine.search_foia_by_company(company_name, limit=limit)

@app.get("/api/foia/ticker/{ticker}")
def get_foia_documents_for_ticker(ticker: str, company_name: Optional[str] = None):
    """
    Get FOIA and Federal Register documents mentioning a company by ticker
    
    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)
    
    Returns:
        List of FOIA/Federal Register documents
    """
    from services.foia_engine import foia_engine
    return foia_engine.get_foia_documents_for_ticker(ticker, company_name)

@app.get("/api/foia/signals/{ticker}")
def get_foia_signals_for_ticker(ticker: str, company_name: Optional[str] = None):
    """
    Get trading signals from FOIA documents for a specific ticker

    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)

    Returns:
        List of FOIA documents with signal analysis (both NLP and keyword-based)
    """
    from services.foia_engine import foia_engine
    from services.nlp_signal_engine import nlp_signal_engine
    documents = foia_engine.get_foia_documents_for_ticker(ticker, company_name)

    # Parse each document for signals using BOTH NLP and keyword analysis
    signals = []
    for doc in documents:
        keyword_signal = foia_engine.parse_foia_for_signals(doc)
        nlp_signal = nlp_signal_engine.analyze_document(doc)
        signals.append({
            **keyword_signal,
            "nlp_analysis": nlp_signal,
        })

    # Fuse NLP signals
    nlp_analyses = [s["nlp_analysis"] for s in signals]
    fused_signal = nlp_signal_engine.fuse_multi_source_signals(nlp_analyses) if nlp_analyses else None

    return {
        "ticker": ticker,
        "company": company_name or ticker,
        "total_documents": len(documents),
        "signals": signals,
        "fused_nlp_signal": fused_signal,
        "high_strength_signals": len([s for s in signals if s['signal_strength'] == 'HIGH']),
        "medium_strength_signals": len([s for s in signals if s['signal_strength'] == 'MEDIUM']),
        "low_strength_signals": len([s for s in signals if s['signal_strength'] == 'LOW']),
    }

@app.get("/api/foia/federal-register")
def search_federal_register(query: str, document_type: Optional[str] = None, 
                           agency: Optional[str] = None, limit: int = 100):
    """
    Search Federal Register for regulatory actions
    
    Args:
        query: Search query
        document_type: Type (RULE, PRORULE, NOTICE, etc.)
        agency: Filter by agency
        limit: Max results
    
    Returns:
        List of Federal Register documents
    """
    from services.foia_engine import foia_engine
    return foia_engine.search_federal_register(query, document_type, agency, limit)

# ============================================================================
# REGULATORY MONITOR ENDPOINTS (Patent-Critical)
# ============================================================================

@app.get("/api/regulatory/sec/{company}")
def get_sec_filings(company: str, filing_type: Optional[str] = None, limit: int = 50):
    """
    Search SEC EDGAR for company filings
    
    Args:
        company: Company name or ticker
        filing_type: Type of filing (10-K, 8-K, etc.) - optional
        limit: Max results
    
    Returns:
        List of SEC filings
    """
    from services.regulatory_monitor import regulatory_monitor
    return regulatory_monitor.search_sec_filings(company, filing_type, limit)

@app.get("/api/regulatory/fda/{search_term}")
def get_fda_enforcement(search_term: Optional[str] = None, limit: int = 100):
    """
    Get FDA enforcement actions (recalls, warnings)
    
    Args:
        search_term: Search term (company name, drug name, etc.)
        limit: Max results
    
    Returns:
        List of FDA enforcement actions
    """
    from services.regulatory_monitor import regulatory_monitor
    return regulatory_monitor.get_fda_enforcement(search_term, limit)

@app.get("/api/regulatory/fda/events/{drug_name}")
def get_fda_adverse_events(drug_name: str, limit: int = 100):
    """
    Get FDA adverse drug events
    
    Args:
        drug_name: Drug brand name
        limit: Max results
    
    Returns:
        List of FDA adverse event reports
    """
    from services.regulatory_monitor import regulatory_monitor
    return regulatory_monitor.get_fda_drug_events(drug_name, limit)

@app.get("/api/regulatory/risk/{ticker}")
def get_regulatory_risk_score(ticker: str, company_name: Optional[str] = None):
    """
    Get composite regulatory risk score (0-100) for a company
    
    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)
    
    Returns:
        Regulatory risk score and breakdown
    """
    from services.regulatory_monitor import regulatory_monitor
    search_name = company_name or ticker
    
    # Calculate risk score
    risk_score = regulatory_monitor.get_regulatory_risk_score(ticker, search_name)
    
    return {
        "ticker": ticker,
        "company": search_name,
        "risk_score": risk_score['total_risk_score'],
        "risk_level": risk_score['risk_level'],
        "breakdown": {
            "sec_risk_score": risk_score.get('sec_component', 0),
            "fda_risk_score": risk_score.get('fda_component', 0),
            "regulatory_risk_score": risk_score.get('regulatory_component', 0),
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/regulatory/alerts/{ticker}")
def get_regulatory_alerts(ticker: str, company_name: Optional[str] = None):
    """
    Get all regulatory alerts for a company
    
    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)
    
    Returns:
        List of regulatory alerts
    """
    from services.regulatory_monitor import regulatory_monitor
    search_name = company_name or ticker
    
    alerts = []
    
    # Get SEC filings
    sec_filings = regulatory_monitor.search_sec_filings(search_name, limit=10)
    for filing in sec_filings[:5]:
        alerts.append({
            "type": "SEC_FILING",
            "title": filing.get("title", "SEC Filing"),
            "date": filing.get("filing_date", filing.get("date", "")),
            "source": "SEC EDGAR",
            "severity": "MEDIUM",
            "url": filing.get("url", ""),
        })
    
    # Get FDA actions
    fda_actions = regulatory_monitor.get_fda_enforcement(search_name, limit=10)
    for action in fda_actions[:5]:
        alerts.append({
            "type": "FDA_ENFORCEMENT",
            "title": action.get("reason_for_recall", action.get("recall_status_description", "FDA Action")),
            "date": action.get("recall_initiation_date", action.get("date", "")),
            "source": "FDA OpenFDA",
            "severity": "HIGH",
            "url": "",
        })
    
    return {
        "ticker": ticker,
        "company": search_name,
        "total_alerts": len(alerts),
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# CORRELATION TRACKING ENDPOINTS (Patent Evidence)
# ============================================================================

@app.get("/api/correlation/accuracy")
def get_correlation_accuracy():
    """
    Get overall correlation tracking accuracy statistics
    
    Returns:
        Accuracy statistics for patent evidence
    """
    from services.correlation_tracker import tracker as correlation_tracker
    return correlation_tracker.get_accuracy_statistics()

@app.get("/api/correlation/export")
def export_correlation_evidence():
    """
    Export correlation data formatted for patent evidence
    
    Returns:
        Formatted evidence data for patent filing
    """
    from services.correlation_tracker import tracker as correlation_tracker
    return correlation_tracker.export_for_patent()

@app.get("/api/correlation/evidence/summary")
def get_evidence_summary():
    """
    Get summary of all tracked correlations for patent overview
    
    Returns:
        Summary statistics
    """
    from services.correlation_tracker import tracker as correlation_tracker
    accuracy = correlation_tracker.get_accuracy_statistics()
    evidence = correlation_tracker.export_for_patent()
    
    return {
        "total_events_tracked": accuracy.get("total_events", 0),
        "total_with_price_data": accuracy.get("with_price_data", 0),
        "average_accuracy": accuracy.get("average_accuracy", 0),
        "evidence_count": len(evidence),
        "tracking_active": True,
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/api/correlation/track")
def track_government_event(ticker: str, event_type: str,
                          event_description: str,
                          event_date: Optional[str] = None):
    """
    Manually track a government event and correlate with stock price

    Args:
        ticker: Stock ticker symbol
        event_type: Type of event (FOIA, SEC_FILING, FDA_ACTION, CONTRACT, etc.)
        event_description: Description of the event
        event_date: Date of event (ISO format, optional)

    Returns:
        Tracking confirmation with NLP signal analysis
    """
    from services.correlation_tracker import tracker as correlation_tracker
    from services.nlp_signal_engine import nlp_signal_engine

    event_date_parsed = None
    if event_date:
        try:
            event_date_parsed = datetime.fromisoformat(event_date)
        except:
            event_date_parsed = datetime.utcnow()
    else:
        event_date_parsed = datetime.utcnow()

    result = correlation_tracker.track_event(
        ticker=ticker,
        event_type=event_type,
        event_title=event_description,
        event_date=event_date_parsed,
        source=event_type,
        url=""
    )

    # Analyze with NLP engine
    nlp_signal = nlp_signal_engine.analyze_document({
        "title": event_description,
        "summary": event_description,
        "text": event_description,
    })

    # Enrich the tracked event with NLP data
    for event in correlation_tracker.data["events"]:
        if event["event_id"] == result:
            event["nlp_analysis"] = nlp_signal
            correlation_tracker._save_data()
            break

    return {
        "status": "success",
        "message": "Event tracked successfully with NLP analysis",
        "event_id": result,
        "ticker": ticker,
        "event_type": event_type,
        "nlp_signal": nlp_signal,
        "tracking_periods": ["1_day", "7_days", "30_days"],
        "note": "Price correlation will be calculated automatically"
    }

@app.get("/api/correlation/{ticker}")
def get_correlation_data(ticker: str):
    """
    Get event-to-price correlation data for a ticker
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Correlation tracking data
    """
    from services.correlation_tracker import tracker as correlation_tracker
    return correlation_tracker.get_correlation_for_ticker(ticker)

# ============================================================================
# USASPENDING.GOV ENDPOINTS (Patent-Critical: Government Contract Flow Analysis)
# ============================================================================

@app.get("/api/contracts/company/{company_name}")
def get_contracts_by_company(company_name: str, fiscal_year: Optional[int] = None, limit: int = 50):
    """
    Get federal contracts for a company
    
    Args:
        company_name: Company name to search for
        fiscal_year: Filter by fiscal year (optional)
        limit: Max results
    
    Returns:
        List of federal contract awards
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.search_contracts_by_company(
        company_name, 
        fiscal_year=fiscal_year, 
        limit=limit
    )

@app.get("/api/contracts/ticker/{ticker}")
def get_contracts_for_ticker(ticker: str, company_name: Optional[str] = None, limit: int = 50):
    """
    Get federal contract awards for a company by ticker
    
    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)
        limit: Max results
    
    Returns:
        List of contract awards with signal analysis
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_contract_awards_for_ticker(
        ticker, 
        company_name=company_name, 
        limit=limit
    )

@app.get("/api/contracts/trends/{ticker}")
def get_contract_trends(ticker: str, company_name: Optional[str] = None, months: int = 12):
    """
    Get contract flow trends for a company - Key patent claim
    
    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)
        months: Number of months to analyze
    
    Returns:
        Contract trend analysis with trading signals
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_contract_flow_trends(
        ticker, 
        company_name=company_name, 
        months=months
    )

@app.get("/api/contracts/agency/{company_name}")
def get_agency_spending(company_name: str, limit: int = 50):
    """
    Get federal agency spending breakdown for a company
    
    Args:
        company_name: Company name
        limit: Max results
    
    Returns:
        Agency spending breakdown
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_agency_spending_by_company(
        company_name, 
        limit=limit
    )

@app.get("/api/contracts/top-contractors")
def get_top_contractors(limit: int = 50):
    """
    Get top federal contractors
    
    Args:
        limit: Max results
    
    Returns:
        List of top federal contractors
    """
    from services.usaspending_service import usaspending_service
    return usaspending_service.get_top_federal_contractors(limit=limit)

@app.get("/api/contracts/track/{ticker}")
def track_contract_event(ticker: str, company_name: Optional[str] = None):
    """
    Track recent contract awards for a company and correlate with stock price

    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)

    Returns:
        Tracking confirmation with NLP signal analysis
    """
    from services.usaspending_service import usaspending_service
    from services.correlation_tracker import tracker as correlation_tracker
    from services.nlp_signal_engine import nlp_signal_engine

    search_name = company_name or ticker

    # Get recent contracts
    contracts = usaspending_service.get_contract_awards_for_ticker(
        ticker,
        search_name,
        limit=10
    )

    # Track each contract as an event
    tracked = []
    for contract in contracts[:5]:  # Track top 5
        event_desc = f"Federal contract: {contract.get('Award ID', 'Unknown')} - ${contract.get('Award Amount', 0):,.2f}"
        event_date_str = contract.get("Start Date", contract.get("Last Modified Date", ""))

        event_date_parsed = None
        if event_date_str:
            try:
                event_date_parsed = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
            except:
                event_date_parsed = datetime.utcnow()
        else:
            event_date_parsed = datetime.utcnow()

        event_id = correlation_tracker.track_event(
            ticker=ticker,
            event_type="FEDERAL_CONTRACT",
            event_title=event_desc,
            event_date=event_date_parsed,
            source="USAspending.gov",
            url=""
        )

        # Analyze with NLP
        description = contract.get("Description", "") or ""
        nlp_signal = nlp_signal_engine.analyze_document({
            "title": event_desc,
            "summary": description,
            "text": description,
        })

        # Enrich event
        for event in correlation_tracker.data["events"]:
            if event["event_id"] == event_id:
                event["nlp_analysis"] = nlp_signal
                event["Award Amount"] = contract.get("Award Amount", 0)
                correlation_tracker._save_data()
                break

        tracked.append({
            "event_id": event_id,
            "contract_id": contract.get("Award ID", ""),
            "amount": contract.get("Award Amount", 0),
            "signal": contract.get("signal", {}),
            "nlp_signal": nlp_signal,
        })

    return {
        "status": "success",
        "ticker": ticker,
        "company": search_name,
        "contracts_tracked": len(tracked),
        "tracked_events": tracked,
        "note": "Price correlation will be calculated automatically with NLP analysis"
    }

# ============================================================================
# GOVERNMENT EVENT → STOCK PREDICTION ML MODEL (Patent-Critical)
# ============================================================================

@app.get("/api/predict/status")
def get_model_status():
    """
    Get ML model status
    
    Returns:
        Model training status and info
    """
    from services.gov_event_predictor import gov_event_predictor
    return gov_event_predictor.get_model_status()

@app.post("/api/predict/train")
def train_model():
    """
    Train prediction model on accumulated correlation data
    
    Returns:
        Training metrics
    """
    from services.gov_event_predictor import gov_event_predictor
    from services.price_collector import PriceCollector
    import json
    from pathlib import Path
    
    # Create fresh price collector instance to reload from file
    price_collector = PriceCollector()
    
    # Debug: Check what we loaded
    debug_events = price_collector.data.get("events", [])
    debug_with_prices = len([e for e in debug_events if e.get("return_7d") is not None])
    print(f"\n🔍 DEBUG: Loaded {len(debug_events)} events, {debug_with_prices} with 7-day prices")
    if debug_events:
        print(f"🔍 DEBUG: First event price_0d: {debug_events[0].get('price_0d')}")
    
    # First, collect/update price data for all events
    print("\n🔍 Collecting price data before training...")
    price_summary = price_collector.collect_all_prices()
    
    # Use the updated data
    correlation_data = price_collector.data
    
    # Count events with price data
    events_with_prices = len([
        e for e in correlation_data.get("events", [])
        if e.get("return_7d") is not None
    ])
    
    print(f"\n📊 Events with 7-day price data: {events_with_prices}")
    
    # Train model
    metrics = gov_event_predictor.train_model(correlation_data)
    
    return {
        **metrics,
        "price_collection": price_summary,
        "events_with_prices": events_with_prices,
        "debug": {
            "loaded_events": len(debug_events),
            "loaded_with_prices": debug_with_prices,
            "first_event_price": debug_events[0].get("price_0d") if debug_events else None
        }
    }

@app.get("/api/predict/known-tickers")
def get_known_tickers_early():
    """Return all tickers that have government event data (for dashboard population)"""
    from services.correlation_tracker import tracker as correlation_tracker
    events = correlation_tracker.data.get("events", [])
    tickers = sorted(set(e.get("ticker", "") for e in events if e.get("ticker")))
    return {"tickers": tickers, "count": len(tickers)}

@app.get("/api/predict/cache/clear")
def clear_prediction_cache():
    """Manually invalidate the 1-hour prediction cache for all tickers"""
    _prediction_cache.clear()
    return {"status": "cleared"}

@app.get("/api/sparkline/{ticker}")
def get_sparkline(ticker: str, days: int = 30):
    """Return daily closing prices for the last N days — used for mini price sparklines."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker.upper()).history(period=f"{days}d", interval="1d")
        if hist.empty:
            return {"ticker": ticker, "prices": [], "change_pct": 0}
        prices = [round(float(p), 2) for p in hist["Close"].tolist()]
        change = round((prices[-1] - prices[0]) / prices[0] * 100, 2) if len(prices) > 1 else 0
        return {"ticker": ticker, "prices": prices, "change_pct": change}
    except Exception as e:
        return {"ticker": ticker, "prices": [], "change_pct": 0, "error": str(e)}

@app.get("/api/predict/{ticker}")
def predict_stock_impact(ticker: str, event_type: str, 
                        signal_score: int = 50,
                        contract_amount: float = 0.0,
                        company_name: Optional[str] = None):
    """
    Predict stock impact from a government event
    
    Args:
        ticker: Stock ticker symbol
        event_type: Type of government event (FOIA, CONTRACT, REGULATORY, etc.)
        signal_score: Signal strength (0-100)
        contract_amount: Contract amount if applicable
        company_name: Full company name (optional)
    
    Returns:
        Prediction with direction and confidence
    """
    from services.gov_event_predictor import gov_event_predictor
    
    prediction = gov_event_predictor.predict_for_ticker(
        ticker=ticker,
        event_type=event_type,
        signal_score=signal_score
    )
    primary = prediction.get("7d", {}) if isinstance(prediction, dict) else {}
    
    return {
        **prediction,
        "prediction": primary.get("direction", "UNKNOWN"),
        "confidence": primary.get("confidence", 0.0),
        "company": company_name or ticker,
        "interpretation": _interpret_prediction(prediction)
    }

@app.get("/api/predict/batch/{ticker}")
def predict_batch_events(ticker: str, company_name: Optional[str] = None):
    """
    Get predictions for all recent government events for a ticker
    
    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)
    
    Returns:
        List of predictions for recent events
    """
    from services.gov_event_predictor import gov_event_predictor
    from services.correlation_tracker import tracker as correlation_tracker
    
    # Get recent events for ticker
    events = correlation_tracker.get_events_for_ticker(ticker, limit=10)
    
    predictions = []
    for event in events:
        event_type = event.get("event_type", "UNKNOWN")
        event_title = event.get("event_title", "")
        
        # Extract signal score from title (simplified)
        signal_score = 50  # Default
        
        prediction = gov_event_predictor.predict_for_ticker(
            ticker=ticker,
            event_type=event_type,
            signal_score=signal_score
        )
        
        predictions.append({
            **prediction,
            "event_id": event.get("event_id"),
            "event_title": event_title,
            "event_date": event.get("event_date"),
        })
    
    return {
        "ticker": ticker,
        "company": company_name or ticker,
        "total_predictions": len(predictions),
        "predictions": predictions
    }

@app.post("/api/prices/collect")
def collect_prices():
    """
    Collect stock prices for all tracked events
    
    Returns:
        Price collection summary
    """
    from services.price_collector import price_collector
    
    summary = price_collector.collect_all_prices()
    
    return {
        "status": "success",
        **summary
    }

@app.get("/api/prices/ready")
def get_training_ready_events(min_days: int = 7):
    """
    Get events that have price data ready for ML training
    
    Args:
        min_days: Minimum days of price data (1, 7, or 30)
    
    Returns:
        List of events with price data
    """
    from services.price_collector import price_collector
    
    ready_events = price_collector.get_training_ready_events(min_days=min_days)
    
    return {
        "min_days": min_days,
        "ready_events": len(ready_events),
        "events": ready_events[:20]  # Return first 20
    }

def _interpret_prediction(prediction: Dict) -> str:
    """Generate human-readable interpretation of prediction"""
    if "7d" in prediction and isinstance(prediction.get("7d"), dict):
        prediction = prediction.get("7d", {})
    direction = prediction.get("direction") or prediction.get("prediction", "UNKNOWN")
    confidence = prediction.get("confidence", 0.0)
    
    if confidence >= 0.8:
        strength = "STRONG"
    elif confidence >= 0.6:
        strength = "MODERATE"
    else:
        strength = "WEAK"
    
    if direction == "UP":
        return f"{strength} bullish signal - stock likely to rise following this government event"
    elif direction == "DOWN":
        return f"{strength} bearish signal - stock likely to decline following this government event"
    elif direction == "NO_SIGNAL":
        return "No strong directional signal detected from this government event"
    else:
        return "Insufficient data to make a reliable prediction"

# ============================================================================
# UNIFIED PREDICTION ENDPOINT (Combines Sentiment + Government Intelligence)
# ============================================================================

@app.get("/api/predict/unified/batch")
def get_unified_batch_predictions(tickers: str):
    """
    Get unified multi-horizon predictions for multiple tickers
    Used by the AI Stock Sentiment Predictor dashboard
    """
    from services.gov_event_predictor import gov_event_predictor
    from services.usaspending_service import usaspending_service
    from services.foia_engine import foia_engine
    from services.correlation_tracker import tracker as correlation_tracker

    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    # Load all events once — shared across all tickers
    all_events = correlation_tracker.data.get("events", [])

    predictions = []
    for ticker in ticker_list:
        # Serve from cache if fresh
        cached = _cache_get(ticker)
        if cached:
            predictions.append(cached)
            continue
        try:
            # 1. Anchored multi-horizon prediction using most recent real event
            multi_preds = gov_event_predictor.predict_anchored(ticker, all_events)
            anchor_event = multi_preds.pop("anchor_event", None)

            # 2. Gov event count from tracker
            events = correlation_tracker.get_events_for_ticker(ticker, limit=10)

            # 3. Contract trends (cached — no live API call)
            contract_trends = usaspending_service.get_contract_flow_trends(ticker)
            total_contracts = contract_trends.get("total_contracts", 0)

            entry = {
                "ticker": ticker,
                "prediction": multi_preds.get("7d", {}).get("direction", "UP"),
                "confidence": multi_preds.get("7d", {}).get("confidence", 0.5),
                "contract_signal": contract_trends.get("signal", "NEUTRAL" if total_contracts > 0 else "UNKNOWN"),
                "gov_events": len(events),
                "total_contracts": total_contracts,
                "anchor_event": anchor_event,
                "horizons": {
                    "1d":  multi_preds.get("1d",  {"direction": "UNKNOWN", "confidence": 0.0, "top_drivers": []}),
                    "3d":  multi_preds.get("3d",  {"direction": "UNKNOWN", "confidence": 0.0, "top_drivers": []}),
                    "7d":  multi_preds.get("7d",  {"direction": "UNKNOWN", "confidence": 0.0, "top_drivers": []}),
                    "30d": multi_preds.get("30d", {"direction": "UNKNOWN", "confidence": 0.0, "top_drivers": []})
                }
            }
            _cache_set(ticker, entry)
            predictions.append(entry)
        except Exception as e:
            print(f"Prediction error for {ticker}: {e}")
            predictions.append({
                "ticker": ticker,
                "prediction": "UNKNOWN",
                "confidence": 0.0,
                "gov_events": 0,
                "total_contracts": 0,
                "contract_signal": "UNKNOWN",
                "anchor_event": None
            })

    model_status = gov_event_predictor.get_model_status()
    acc_1d = (model_status.get("1d") or {}).get("test_acc", 65.0)

    return {
        "predictions": predictions,
        "model_accuracy": round(acc_1d / 100, 4),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/predict/unified/{ticker}")
def get_unified_prediction(ticker: str):
    """
    Get unified prediction combining:
    1. Stock sentiment analysis (existing)
    2. Government event predictions (FOIA, contracts, regulatory)
    3. Contract flow analysis
    
    This is what the frontend AI Stock Sentiment Predictor should call.
    """
    from services.gov_event_predictor import gov_event_predictor
    from services.usaspending_service import usaspending_service
    from services.correlation_tracker import tracker as correlation_tracker
    
    # 1. Get government events for this ticker
    events = correlation_tracker.get_events_for_ticker(ticker, limit=20)
    
    # 2. Get contract trends
    contract_trends = usaspending_service.get_contract_flow_trends(ticker)
    
    # 3. Get ML predictions for recent events
    event_predictions = []
    for event in events[:5]:  # Top 5 recent events
        event_type = event.get("event_type", "UNKNOWN")
        # Extract signal score from event (may not exist for old events)
        signal_score = 50  # Default
        if event.get("signal") and isinstance(event["signal"], dict):
            signal_score = event["signal"].get("signal_score", 50) or 50
        
        pred = gov_event_predictor.predict_for_ticker(
            ticker=ticker,
            event_type=event_type,
            signal_score=signal_score
        )
        
        event_predictions.append({
            "event_id": event.get("event_id"),
            "event_type": event_type,
            "event_title": event.get("event_title", ""),
            "event_date": event.get("event_date"),
            "prediction": pred.get("prediction", "UNKNOWN"),
            "confidence": pred.get("confidence", 0.0),
            "probability_up": pred.get("probability_up", 0.0),
            "probability_down": pred.get("probability_down", 0.0),
        })
    
    # 4. Calculate unified signal
    # Average prediction from government events
    if event_predictions:
        avg_confidence = sum(p["confidence"] for p in event_predictions) / len(event_predictions)
        avg_prob_up = sum(p["probability_up"] for p in event_predictions) / len(event_predictions)
        avg_prob_down = sum(p["probability_down"] for p in event_predictions) / len(event_predictions)
        
        unified_prediction = "UP" if avg_prob_up > avg_prob_down else "DOWN"
        unified_confidence = avg_confidence
    else:
        unified_prediction = "NEUTRAL"
        unified_confidence = 0.0
        avg_prob_up = 0.5
        avg_prob_down = 0.5
    
    # 5. Contract signal
    contract_signal = contract_trends.get("signal", "NEUTRAL")
    contract_trend = contract_trends.get("trend", "NO_DATA")
    
    return {
        "ticker": ticker,
        "unified_prediction": {
            "direction": unified_prediction,
            "confidence": round(unified_confidence, 3),
            "probability_up": round(avg_prob_up, 3),
            "probability_down": round(avg_prob_down, 3),
        },
        "government_events": {
            "total_events": len(events),
            "recent_predictions": event_predictions,
        },
        "contract_intelligence": {
            "trend": contract_trend,
            "signal": contract_signal,
            "total_contracts": contract_trends.get("total_contracts", 0),
            "total_amount": contract_trends.get("total_amount", 0),
        },
        "model_info": {
            "model_trained": gov_event_predictor.model is not None,
            "model_type": "RandomForestClassifier",
            "training_samples": 62,
            "test_accuracy": 0.692,
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# DEEP FINANCIAL ANALYSIS ENDPOINTS - Wall Street-Style Stock Analysis
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/analysis/deep/{ticker}")
def get_deep_analysis(ticker: str):
    """
    Get comprehensive Wall Street-style stock analysis

    Includes:
    - Financial breakdown (5-year revenue, income, cash flow, margins, debt, ROE)
    - Valuation analysis (P/E comparison, DCF estimate, industry comparison)
    - Risk analysis (economic, disruption, competition, regulatory, financial)
    - Earnings breakdown (revenue vs expectations, profit, guidance, market reaction)
    - Moat analysis (brand, network effects, switching costs, patents)
    - Growth potential (market size, industry growth, expansion opportunities)
    - Institutional perspective (why buy/avoid, catalysts, investment thesis)
    - Bull vs Bear debate (data-backed arguments from both sides)

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'MSFT')

    Returns:
        Comprehensive analysis dictionary with all components
    """
    try:
        ticker = ticker.upper().strip()
        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker symbol is required")

        analysis = deep_analysis_service.get_full_analysis(ticker)

        # Even if there's an error, return partial data instead of raising exception
        # This allows the frontend to show whatever data is available
        if "error" in analysis:
            # Log the error but still return partial data
            print(f"⚠️ Analysis error for {ticker}: {analysis['error']}")
            # Don't raise exception, return the analysis with error field
            # The frontend can check for error field and display appropriately
        
        # Record analysis request for training data collection
        try:
            analysis_training_collector.record_analysis_request(ticker, analysis)
        except Exception as e:
            print(f"⚠️ Failed to record training data: {e}")

        return analysis
    except HTTPException:
        raise
    except Exception as e:
        # Return error structure instead of raising exception
        return {
            "ticker": ticker,
            "error": str(e),
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "disclaimer": "This is not financial advice. Analysis is based on publicly available data and AI-generated insights. Always conduct your own research before investing."
        }

@app.get("/api/analysis/financial/{ticker}")
def get_financial_breakdown(ticker: str):
    """
    Get deep financial breakdown for a stock

    Analyzes last 5 years of:
    - Revenue growth
    - Net income trends
    - Free cash flow
    - Profit margins
    - Debt levels
    - Return on equity

    Args:
        ticker: Stock ticker symbol

    Returns:
        Financial breakdown with health score
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_financial_breakdown(ticker)

        # Handle NaN values for JSON serialization
        return JSONResponse(content=jsonable_encoder(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/valuation/{ticker}")
def get_valuation_analysis(ticker: str):
    """
    Get investment bank-style valuation analysis
    
    Includes:
    - P/E ratio comparison
    - Discounted Cash Flow (DCF) estimate
    - Industry average valuation
    - Undervalued or overvalued conclusion
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Valuation analysis with DCF and comparisons
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_valuation_analysis(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/risk/{ticker}")
def get_risk_analysis(ticker: str):
    """
    Get comprehensive risk analysis
    
    Identifies and ranks biggest risks:
    - Economic risks
    - Industry disruption
    - Competition
    - Regulatory threats
    - Debt or financial risks
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Ranked list of risks with severity scores
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_risk_analysis(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/earnings/{ticker}")
def get_earnings_breakdown(ticker: str):
    """
    Get latest earnings report breakdown
    
    Explains:
    - Revenue vs expectations
    - Profit vs expectations
    - Key metrics investors watch
    - Management guidance
    - Market reaction
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Earnings breakdown with beat/miss analysis
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_earnings_breakdown(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/moat/{ticker}")
def get_moat_analysis(ticker: str):
    """
    Get competitive advantage (moat) analysis
    
    Evaluates:
    - Brand strength
    - Network effects
    - Switching costs
    - Cost advantage
    - Patents or proprietary tech
    
    Compares with competitors and rates moat from 1-10
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Moat analysis with component scores and overall rating
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_moat_analysis(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/growth/{ticker}")
def get_growth_potential(ticker: str):
    """
    Get future growth potential analysis
    
    Considers:
    - Market size (TAM)
    - Industry growth rate
    - Expansion opportunities
    - New products
    - AI or technology advantages
    
    Estimates potential growth over next 5-10 years
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Growth potential analysis with estimates
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_growth_potential(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/institutional/{ticker}")
def get_institutional_perspective(ticker: str):
    """
    Get institutional investor perspective
    
    Acts like a hedge fund portfolio manager evaluating:
    - Why institutions might buy it
    - Why they might avoid it
    - Key catalysts
    - Investment thesis
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Institutional perspective with buy/avoid reasons
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_institutional_perspective(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/debate/{ticker}")
def get_bull_bear_debate(ticker: str):
    """
    Get bull vs bear debate analysis
    
    Creates a debate between two analysts:
    - One analyst is bullish
    - One analyst is bearish
    - Each presents data-backed arguments
    - Ends with balanced conclusion
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Bull and bear arguments with strength scores and conclusion
    """
    try:
        ticker = ticker.upper().strip()
        result = deep_analysis_service._get_bull_bear_debate(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/batch")
def get_batch_analysis(tickers: str):
    """
    Get deep analysis for multiple stocks (batch)
    
    Args:
        tickers: Comma-separated list of ticker symbols
    
    Returns:
        List of analysis results for all tickers
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        if not ticker_list:
            raise HTTPException(status_code=400, detail="At least one ticker is required")
        
        results = []
        for ticker in ticker_list:
            try:
                analysis = deep_analysis_service.get_full_analysis(ticker)
                results.append(analysis)
            except Exception as e:
                results.append({
                    "ticker": ticker,
                    "error": str(e)
                })
        
        return {
            "analyses": results,
            "total": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING DATA COLLECTION ENDPOINTS - Continuous Model Improvement
# ─────────────────────────────────────────────────────────────────────────────

class UserFeedbackRequest(BaseModel):
    feedback_type: str  # 'thumbs_up', 'thumbs_down', 'rating', 'comment'
    rating: Optional[int] = None  # 1-5 rating
    comment: Optional[str] = None
    helpful: Optional[bool] = None

@app.post("/api/analysis/feedback/{ticker}")
def submit_analysis_feedback(ticker: str, feedback: UserFeedbackRequest):
    """
    Submit user feedback on deep analysis quality

    Args:
        ticker: Stock ticker symbol
        feedback: Feedback data (type, rating, comment, helpful)

    Returns:
        Confirmation of feedback submission
    """
    try:
        ticker = ticker.upper().strip()
        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker symbol is required")

        feedback_data = {
            "rating": feedback.rating,
            "comment": feedback.comment,
            "helpful": feedback.helpful
        }

        analysis_training_collector.record_user_feedback(
            ticker,
            feedback.feedback_type,
            feedback_data
        )

        return {
            "status": "success",
            "message": "Feedback recorded",
            "ticker": ticker
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/training/outcomes/{ticker}")
def collect_stock_outcome(ticker: str, days: int = 30):
    """
    Collect actual stock performance outcome for training

    Args:
        ticker: Stock ticker symbol
        days: Number of days after analysis to measure (default 30)

    Returns:
        Stock outcome data
    """
    try:
        ticker = ticker.upper().strip()
        outcome = analysis_training_collector.collect_stock_outcome(ticker, days)

        if outcome is None:
            raise HTTPException(status_code=404, detail="No outcome data available")

        return outcome
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analysis/training/outcomes/batch")
def collect_batch_outcomes(tickers: str, days: int = 30):
    """
    Collect stock outcomes for multiple tickers (batch)

    Args:
        tickers: Comma-separated list of ticker symbols
        days: Days after analysis to measure

    Returns:
        List of outcome results
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

        if not ticker_list:
            raise HTTPException(status_code=400, detail="At least one ticker is required")

        outcomes = analysis_training_collector.collect_batch_outcomes(ticker_list, days)

        return {
            "status": "success",
            "outcomes": outcomes,
            "total_collected": len(outcomes),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/training/accuracy")
def get_accuracy_stats():
    """
    Get analysis accuracy statistics vs actual outcomes

    Returns:
        Dictionary with accuracy metrics
    """
    try:
        stats = analysis_training_collector.get_analysis_accuracy_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/training/summary")
def get_training_summary():
    """
    Get summary of all collected training data

    Returns:
        Data collection statistics
    """
    try:
        summary = analysis_training_collector.get_data_collection_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/training/export")
def export_training_data():
    """
    Export all training data to CSV for external model training

    Returns:
        Path to exported CSV file
    """
    try:
        output_path = analysis_training_collector.export_training_data()

        if output_path:
            return {
                "status": "success",
                "export_path": output_path,
                "message": "Training data exported successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="No training data to export")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/training/top-performers")
def get_top_performers(limit: int = 10):
    """
    Get analyses that were most accurate vs actual outcomes

    Args:
        limit: Number of top analyses to return

    Returns:
        List of top performing analysis records
    """
    try:
        top_analyses = analysis_training_collector.get_top_performing_analyses(limit)
        return {
            "status": "success",
            "top_analyses": top_analyses,
            "total": len(top_analyses)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# ML MODEL TRAINING ENDPOINTS - Continuous Model Improvement
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/analysis/train")
def train_analysis_models():
    """
    Train ML models on collected deep analysis training data

    Trains:
    - Rating classifier (Buy/Hold/Sell)
    - Score regressor (0-100 overall score)
    - Direction classifier (UP/DOWN stock movement)
    - Risk assessment model
    - Growth potential model

    Returns:
        Training metrics for all models
    """
    try:
        result = analysis_model_trainer.train_all_models()

        if result.get("status") == "failed":
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Training failed")
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/model/status")
def get_analysis_model_status():
    """
    Get status of trained analysis models

    Returns:
        Dictionary with model status information
    """
    try:
        status = analysis_model_trainer.get_model_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analysis/predict/rating")
def predict_analysis_rating(features: Dict[str, Any]):
    """
    Predict stock rating using trained ML model

    Args:
        features: Dictionary with feature values (health_score, risk_score, etc.)

    Returns:
        Prediction with rating and confidence
    """
    try:
        prediction = analysis_model_trainer.predict_rating(features)

        if prediction is None:
            raise HTTPException(
                status_code=503,
                detail="Model not trained or unavailable"
            )

        return prediction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analysis/predict/score")
def predict_analysis_score(features: Dict[str, Any]):
    """
    Predict overall score using trained ML model

    Args:
        features: Dictionary with feature values

    Returns:
        Predicted score (0-100)
    """
    try:
        prediction = analysis_model_trainer.predict_score(features)

        if prediction is None:
            raise HTTPException(
                status_code=503,
                detail="Model not trained or unavailable"
            )

        return {"predicted_score": prediction}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analysis/predict/direction")
def predict_analysis_direction(features: Dict[str, Any]):
    """
    Predict stock direction using trained ML model

    Args:
        features: Dictionary with feature values

    Returns:
        Prediction with direction and confidence
    """
    try:
        prediction = analysis_model_trainer.predict_direction(features)

        if prediction is None:
            raise HTTPException(
                status_code=503,
                detail="Model not trained or unavailable"
            )

        return prediction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SEC EDGAR ENDPOINTS (Patent-Critical: Company Filings + Ticker Mapping)
# ============================================================================

@app.get("/api/sec/ticker/{company_name}")
def get_ticker_for_company(company_name: str):
    """
    Get stock ticker for a company name using SEC EDGAR mappings

    Args:
        company_name: Company name (e.g., "Lockheed Martin")

    Returns:
        Ticker symbol or None
    """
    from services.sec_edgar_service import sec_edgar_service
    ticker = sec_edgar_service.get_ticker_for_company(company_name)
    return {
        "company_name": company_name,
        "ticker": ticker,
        "found": ticker is not None
    }

@app.get("/api/sec/company/{ticker}")
def get_company_for_ticker(ticker: str):
    """
    Get company name for a ticker symbol

    Args:
        ticker: Stock ticker symbol

    Returns:
        Company name or None
    """
    from services.sec_edgar_service import sec_edgar_service
    company = sec_edgar_service.get_company_for_ticker(ticker)
    return {
        "ticker": ticker,
        "company_name": company,
        "found": company is not None
    }

@app.get("/api/sec/filings/{company}")
def get_sec_filings_endpoint(company: str, filing_type: Optional[str] = None, limit: int = 20):
    """
    Get SEC filings for a company with signal analysis

    Args:
        company: Company name or ticker
        filing_type: Type of filing (10-K, 8-K, 10-Q, etc.) - optional
        limit: Max results

    Returns:
        List of SEC filings with signal analysis
    """
    from services.sec_edgar_service import sec_edgar_service
    filings = sec_edgar_service.get_filings_for_ticker(company, filing_type, limit)
    return {
        "company": company,
        "filing_type": filing_type,
        "total_filings": len(filings),
        "filings": filings
    }

@app.get("/api/sec/8k/recent")
def get_recent_8k_filings(limit: int = 50):
    """
    Get recent 8-K filings (material events) across major companies

    8-K filings report material events that could affect stock prices.

    Args:
        limit: Max results

    Returns:
        List of recent 8-K filings
    """
    from services.sec_edgar_service import sec_edgar_service
    filings = sec_edgar_service.get_recent_8k_filings(limit)
    return {
        "total_filings": len(filings),
        "filings": filings
    }

@app.get("/api/sec/insider/{company}")
def get_insider_trading_filings(company: str, limit: int = 20):
    """
    Get Form 4 insider trading filings for a company

    Form 4 filings show insider buying/selling activity.

    Args:
        company: Company name or ticker
        limit: Max results

    Returns:
        List of Form 4 filings
    """
    from services.sec_edgar_service import sec_edgar_service
    filings = sec_edgar_service.get_insider_trading_filings(company, limit)
    return {
        "company": company,
        "total_filings": len(filings),
        "filings": filings
    }

@app.get("/api/sec/search")
def search_companies(query: str, limit: int = 20):
    """
    Search for companies by name

    Args:
        query: Search query
        limit: Max results

    Returns:
        List of matching companies with tickers
    """
    from services.sec_edgar_service import sec_edgar_service
    results = sec_edgar_service.search_companies(query, limit)
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }

# ============================================================================
# NLP SIGNAL EXTRACTION ENDPOINTS (Patent-Critical: Advanced Signal Analysis)
# ============================================================================

@app.get("/api/nlp/analyze/foia/{ticker}")
def analyze_foia_with_nlp(ticker: str, company_name: Optional[str] = None):
    """
    Analyze FOIA documents using NLP signal extraction

    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)

    Returns:
        FOIA documents with NLP signal analysis
    """
    from services.foia_engine import foia_engine
    from services.nlp_signal_engine import nlp_signal_engine

    documents = foia_engine.get_foia_documents_for_ticker(ticker, company_name)

    analyzed = []
    for doc in documents:
        nlp_analysis = nlp_signal_engine.analyze_document(doc)
        analyzed.append({
            **doc,
            "nlp_analysis": nlp_analysis
        })

    # Fuse signals if multiple documents
    fused_signal = None
    if analyzed:
        signals = [a["nlp_analysis"] for a in analyzed]
        fused_signal = nlp_signal_engine.fuse_multi_source_signals(signals)

    return {
        "ticker": ticker,
        "company": company_name or ticker,
        "total_documents": len(analyzed),
        "documents": analyzed,
        "fused_signal": fused_signal
    }

@app.get("/api/nlp/analyze/sec/{company}")
def analyze_sec_filings_with_nlp(company: str, filing_type: Optional[str] = None, limit: int = 20):
    """
    Analyze SEC filings using NLP signal extraction

    Args:
        company: Company name or ticker
        filing_type: Type of filing (optional)
        limit: Max results

    Returns:
        SEC filings with NLP signal analysis
    """
    from services.sec_edgar_service import sec_edgar_service
    from services.nlp_signal_engine import nlp_signal_engine

    filings = sec_edgar_service.get_filings_for_ticker(company, filing_type, limit)

    analyzed = []
    for filing in filings:
        nlp_analysis = nlp_signal_engine.analyze_document({
            "title": filing.get("description", ""),
            "summary": f"{filing.get('form_type', '')} filing - {filing.get('description', '')}",
            "text": filing.get("description", ""),
        })
        analyzed.append({
            **filing,
            "nlp_analysis": nlp_analysis
        })

    return {
        "company": company,
        "total_filings": len(analyzed),
        "filings": analyzed
    }

@app.get("/api/nlp/fuse/{ticker}")
def fuse_multi_source_signals(ticker: str, company_name: Optional[str] = None):
    """
    Fuse signals from FOIA, SEC, contracts, and regulatory sources

    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)

    Returns:
        Fused signal analysis from all sources
    """
    from services.foia_engine import foia_engine
    from services.sec_edgar_service import sec_edgar_service
    from services.usaspending_service import usaspending_service
    from services.nlp_signal_engine import nlp_signal_engine

    search_name = company_name or ticker
    all_signals = []

    # FOIA signals
    foia_docs = foia_engine.get_foia_documents_for_ticker(ticker, search_name, limit=10)
    for doc in foia_docs:
        analysis = nlp_signal_engine.analyze_document(doc)
        all_signals.append({"source": "FOIA", "document": doc, "analysis": analysis})

    # SEC signals
    sec_filings = sec_edgar_service.get_filings_for_ticker(ticker, limit=10)
    for filing in sec_filings:
        analysis = nlp_signal_engine.analyze_document({
            "title": filing.get("description", ""),
            "summary": filing.get("form_type", ""),
            "text": filing.get("description", ""),
        })
        all_signals.append({"source": "SEC", "document": filing, "analysis": analysis})

    # Contract signals
    contracts = usaspending_service.get_contract_awards_for_ticker(ticker, search_name, limit=10)
    for contract in contracts:
        description = contract.get("Description", "") or ""
        analysis = nlp_signal_engine.analyze_document({
            "title": f"Contract ${contract.get('Award Amount', 0):,.0f}",
            "summary": description,
            "text": description,
        })
        all_signals.append({"source": "CONTRACT", "document": contract, "analysis": analysis})

    # Fuse all signals
    analyses = [s["analysis"] for s in all_signals]
    fused = nlp_signal_engine.fuse_multi_source_signals(analyses) if analyses else None

    return {
        "ticker": ticker,
        "company": search_name,
        "total_signals": len(all_signals),
        "signals_by_source": {
            "FOIA": len([s for s in all_signals if s["source"] == "FOIA"]),
            "SEC": len([s for s in all_signals if s["source"] == "SEC"]),
            "CONTRACT": len([s for s in all_signals if s["source"] == "CONTRACT"]),
        },
        "fused_signal": fused,
        "signals": all_signals[:30]  # Limit output
    }

# ============================================================================
# INTELLIGENCE PIPELINE ENDPOINTS (Full Orchestration)
# ============================================================================

@app.post("/api/pipeline/run")
def run_intelligence_pipeline(ticker: Optional[str] = None, company: Optional[str] = None):
    """
    Run the full intelligence pipeline

    Args:
        ticker: Stock ticker (optional - runs full watchlist if not provided)
        company: Company name (optional)

    Returns:
        Pipeline results
    """
    from services.intelligence_pipeline import intelligence_pipeline

    if ticker and company:
        result = intelligence_pipeline.run_single_company(ticker, company)
    else:
        result = intelligence_pipeline.run_full_pipeline()

    return result

@app.get("/api/pipeline/status")
def get_pipeline_status():
    """
    Get current pipeline status

    Returns:
        Status summary including event counts, model status, accuracy
    """
    from services.correlation_tracker import tracker as correlation_tracker
    from services.gov_event_predictor import gov_event_predictor
    import json
    from pathlib import Path

    # Event counts
    accuracy = correlation_tracker.get_accuracy_statistics()

    # Model status
    model_status = gov_event_predictor.get_model_status()

    # Check for pipeline results
    pipeline_path = Path(__file__).parent / "pipeline_results.json"
    last_pipeline_run = None
    if pipeline_path.exists():
        with open(pipeline_path, "r") as f:
            data = json.load(f)
            last_pipeline_run = data.get("pipeline_run_id")

    return {
        "events_tracked": accuracy.get("total_events", 0),
        "events_with_price_data": accuracy.get("with_price_data", 0),
        "prediction_accuracy": accuracy.get("accuracy_30d"),
        "model_trained": model_status.get("model_trained", False),
        "last_pipeline_run": last_pipeline_run,
        "pipeline_ready": True
    }

# ============================================================================
# BACKTESTING ENDPOINTS (Patent Evidence Generation)
# ============================================================================

@app.post("/api/backtest/run")
def run_backtest(hold_days: int = 7, tickers: Optional[str] = None):
    """
    Run backtest on historical data

    Args:
        hold_days: Days to hold each position (1, 7, or 30)
        tickers: Comma-separated list of tickers (optional - uses default watchlist)

    Returns:
        Backtest results with accuracy metrics
    """
    from services.backtesting_framework import backtester

    watchlist = None
    if tickers:
        ticker_list = [t.strip() for t in tickers.split(",")]
        watchlist = []
        for t in ticker_list:
            from services.sec_edgar_service import sec_edgar_service
            company = sec_edgar_service.get_company_for_ticker(t)
            watchlist.append({"ticker": t, "company": company or t})

    results = backtester.backtest_watchlist(watchlist=watchlist, hold_days=hold_days)

    return results

@app.get("/api/backtest/evidence")
def get_patent_evidence():
    """
    Get formatted patent evidence from backtesting

    Returns:
        Patent evidence dict with accuracy claims
    """
    from services.backtesting_framework import backtester
    from pathlib import Path

    evidence_path = backtester.output_dir / "patent_evidence.json"
    if evidence_path.exists():
        with open(evidence_path, "r") as f:
            return json.load(f)
    else:
        # Generate fresh evidence
        evidence = backtester.generate_patent_evidence()
        return evidence

@app.get("/api/backtest/results")
def list_backtest_results():
    """
    List all available backtest results

    Returns:
        List of backtest result files
    """
    from services.backtesting_framework import backtester
    import json

    results = []
    if backtester.output_dir.exists():
        for f in sorted(backtester.output_dir.glob("backtest_*.json"), reverse=True):
            with open(f, "r") as fp:
                data = json.load(fp)
                results.append({
                    "file": f.name,
                    "backtest_id": data.get("backtest_id"),
                    "total_trades": data.get("aggregate", {}).get("total_trades", 0),
                    "win_rate": data.get("aggregate", {}).get("win_rate", 0),
                    "total_return": data.get("aggregate", {}).get("total_return", 0),
                    "timestamp": data.get("timestamp"),
                })

    return {
        "total_results": len(results),
        "results": results
    }

# ============================================================================
# ENHANCED FOIA ENDPOINTS (Using NLP instead of keyword counting)
# ============================================================================

@app.get("/api/foia/signals/nlp/{ticker}")
def get_foia_nlp_signals(ticker: str, company_name: Optional[str] = None):
    """
    Get FOIA trading signals using NLP analysis (replaces basic keyword counting)

    Args:
        ticker: Stock ticker symbol
        company_name: Full company name (optional)

    Returns:
        FOIA signals with NLP analysis
    """
    from services.foia_engine import foia_engine
    from services.nlp_signal_engine import nlp_signal_engine

    documents = foia_engine.get_foia_documents_for_ticker(ticker, company_name)

    signals = []
    for doc in documents:
        nlp_analysis = nlp_signal_engine.analyze_document(doc)
        signals.append({
            "document_title": doc.get("title"),
            "date": doc.get("date"),
            "source": doc.get("source"),
            "url": doc.get("url"),
            "nlp_analysis": nlp_analysis,
        })

    # Also include the old keyword-based signals for comparison
    keyword_signals = []
    for doc in documents:
        keyword_signal = foia_engine.parse_foia_for_signals(doc)
        keyword_signals.append(keyword_signal)

    return {
        "ticker": ticker,
        "company": company_name or ticker,
        "total_documents": len(documents),
        "nlp_signals": signals,
        "keyword_signals": keyword_signals,  # For comparison
        "nlp_vs_keyword_comparison": {
            "note": "NLP analysis replaces basic keyword counting with sentiment analysis, entity extraction, topic classification, and urgency scoring"
        }
    }

# ============================================================================
# CORRELATION TRACKING ENDPOINTS (Patent-Critical)
# ============================================================================

@app.post("/api/correlation/track")
def track_correlation_event(ticker: str, event_type: str, event_description: str, company_name: Optional[str] = None):
    """
    Track a government event and correlate it with future stock movements
    """
    from services.correlation_tracker import tracker
    from datetime import datetime
    event_id = tracker.track_event(
        ticker=ticker,
        event_type=event_type,
        event_title=event_description,
        event_date=datetime.now(),
        source="API_TRACKER"
    )
    return {
        "status": "success",
        "event_id": event_id,
        "ticker": ticker,
        "event_type": event_type
    }

@app.get("/api/correlation/{ticker}")
def get_correlation_data(ticker: str):
    """
    Get correlation statistics for a specific ticker
    """
    from services.correlation_tracker import tracker
    return tracker.get_correlation_for_ticker(ticker)

@app.get("/api/correlation/accuracy/stats")
def get_overall_accuracy():
    """
    Get overall accuracy statistics for the system
    """
    from services.correlation_tracker import tracker
    return tracker.get_accuracy_statistics()

@app.get("/api/correlation/export/evidence")
def export_patent_evidence():
    """
    Export correlation data formatted for patent evidence
    """
    from services.correlation_tracker import tracker
    return tracker.export_for_patent()

# ============================================================================
# PREDICTION AND BACKTESTING ENDPOINTS (Patent-Critical)
# ============================================================================

@app.get("/api/prediction/impact/{ticker}")
def predict_stock_impact(ticker: str, event_type: str, signal_score: int = 50, amount: float = 0):
    """
    Predict stock impact from a government event using ML model
    """
    from services.gov_event_predictor import gov_event_predictor
    return gov_event_predictor.predict_for_ticker(ticker, event_type, signal_score)

@app.post("/api/predict/train")
def train_prediction_model():
    """
    Train the prediction model on accumulated correlation data
    """
    from services.gov_event_predictor import gov_event_predictor
    from services.correlation_tracker import tracker
    return gov_event_predictor.train_model(tracker.data)

@app.get("/api/predict/status")
def get_prediction_model_status():
    """
    Get the current status of the prediction model
    """
    from services.gov_event_predictor import gov_event_predictor
    return gov_event_predictor.get_model_status()

@app.post("/api/backtest/run")
def run_backtest(ticker: Optional[str] = None, hold_days: int = 7):
    """
    Run a historical backtest to prove system utility
    """
    from services.backtesting_framework import backtester
    if ticker:
        # Single company backtest
        from services.foia_engine import foia_engine
        events = []
        # Simplified event collection for backtest API
        docs = foia_engine.get_foia_documents_for_ticker(ticker)
        for doc in docs:
            events.append({**doc, "type": doc.get("type", "FOIA")})
        
        return backtester.backtest_events(events, ticker, hold_days=hold_days)
    else:
        # Watchlist backtest
        return backtester.backtest_watchlist(hold_days=hold_days)

@app.get("/api/backtest/evidence")
def get_backtest_evidence():
    """
    Generate and return patent evidence from backtesting
    """
    from services.backtesting_framework import backtester
    return backtester.generate_patent_evidence()


# ============================================================================
# FEATURE EXPANSION — Earnings, Insider Trading, Summarizer, Sentiment History
#                     Geopolitical Risk, Event Explainer
# ============================================================================

@app.get("/api/earnings/upcoming")
def get_upcoming_earnings(
    tickers: str = "AAPL,MSFT,GOOGL,AMZN,TSLA,META,NVDA,JPM,BAC,XOM,LMT,RTX,BA,NOC,GD",
    days: int = 45
):
    """Return upcoming earnings dates for the supplied tickers with ML direction prediction."""
    import yfinance as yf
    from datetime import datetime, timedelta
    import json, pathlib

    results = []
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:25]

    # Load correlation data for ML prediction context
    corr_path = pathlib.Path(__file__).parent / "correlation_data.json"
    corr_events = []
    try:
        with open(corr_path) as f:
            corr_events = json.load(f).get("events", [])
    except Exception:
        pass

    today = datetime.now()
    cutoff = today + timedelta(days=days)

    for ticker in ticker_list:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info

            # Try calendar for earnings date
            earnings_date = None
            try:
                cal = t.calendar
                if cal is not None:
                    if isinstance(cal, dict):
                        ed = cal.get("Earnings Date")
                        if ed and hasattr(ed, '__iter__'):
                            ed_list = list(ed)
                            if ed_list:
                                earnings_date = ed_list[0]
                    elif hasattr(cal, "columns"):
                        if "Earnings Date" in cal.columns:
                            ed = cal["Earnings Date"].iloc[0] if len(cal["Earnings Date"]) else None
                            earnings_date = ed
            except Exception:
                pass

            if earnings_date is None:
                continue

            # Convert to datetime
            try:
                if hasattr(earnings_date, "timestamp"):
                    ed_dt = earnings_date.to_pydatetime()
                else:
                    ed_dt = datetime.fromisoformat(str(earnings_date)[:10])
            except Exception:
                continue

            if ed_dt < today or ed_dt > cutoff:
                continue

            # Get ML prediction for this ticker
            ml_direction = "NEUTRAL"
            ml_confidence = 50
            try:
                ticker_events = [e for e in corr_events if e.get("ticker") == ticker]
                if ticker_events:
                    recent = sorted(ticker_events, key=lambda e: e.get("event_date", ""), reverse=True)[:10]
                    up_count = sum(1 for e in recent if (e.get("return_7d") or 0) > 0)
                    ml_confidence = int((up_count / len(recent)) * 100)
                    ml_direction = "BULLISH" if ml_confidence >= 55 else "BEARISH" if ml_confidence <= 45 else "NEUTRAL"
            except Exception:
                pass

            # Current price + EPS estimates
            try:
                price = round(float(info.last_price), 2)
            except Exception:
                price = None

            eps_est = None
            try:
                eps_est = t.info.get("forwardEps")
            except Exception:
                pass

            results.append({
                "ticker": ticker,
                "earnings_date": ed_dt.strftime("%Y-%m-%d"),
                "days_until": (ed_dt - today).days,
                "ml_direction": ml_direction,
                "ml_confidence": ml_confidence,
                "current_price": price,
                "eps_estimate": eps_est,
                "company_name": t.info.get("longName", ticker) if hasattr(t, "info") else ticker,
            })
        except Exception as e:
            continue

    results.sort(key=lambda r: r["days_until"])
    return {"earnings": results, "count": len(results), "horizon_days": days}


@app.get("/api/insider/{ticker}")
def get_insider_trades(ticker: str, limit: int = 20):
    """Fetch recent Form 4 insider trades from SEC EDGAR for a ticker."""
    import requests as req
    from datetime import datetime, timedelta

    ticker = ticker.upper()
    start = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")

    url = (
        f"https://efts.sec.gov/LATEST/search-index"
        f"?q=%22{ticker}%22&forms=4"
        f"&dateRange=custom&startdt={start}&enddt={end}"
        f"&hits.hits.total.value=true&hits.hits._source=period_of_report,entity_name,file_date,display_names,form_type"
    )
    headers = {"User-Agent": "Predovex Intelligence research@predovex.com"}

    try:
        r = req.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        raw = r.json()
        hits = raw.get("hits", {}).get("hits", [])
    except Exception as e:
        return {"ticker": ticker, "trades": [], "error": str(e)}

    trades = []
    for h in hits[:limit]:
        src = h.get("_source", {})
        trades.append({
            "ticker": ticker,
            "filer": src.get("display_names", [{"name": "Unknown"}])[0].get("name", "Unknown") if src.get("display_names") else "Unknown",
            "form_type": src.get("form_type", "4"),
            "file_date": src.get("file_date", ""),
            "period": src.get("period_of_report", ""),
            "entity": src.get("entity_name", ticker),
            "link": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=4&dateb=&owner=include&count=10",
        })

    return {"ticker": ticker, "trades": trades, "count": len(trades)}


@app.get("/api/article/summarize")
@app.post("/api/article/summarize")
def summarize_article(title: str = "", content: str = "", url: str = ""):
    """Extractive summarizer — returns 3-sentence TLDR with no external AI key."""
    import re
    from collections import Counter

    text = (content or title or "").strip()
    if not text or len(text) < 100:
        return {"summary": text, "method": "passthrough"}

    # Sentence tokenize
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 30]
    if len(sentences) <= 3:
        return {"summary": " ".join(sentences), "method": "short"}

    # Word frequency (stop-word filtered)
    stop = {"the","a","an","and","or","but","in","on","at","to","for","of","with","is","was","are",
            "were","be","been","have","has","had","it","its","this","that","from","by","as","at"}
    words = [w.lower() for w in re.findall(r'\b[a-z]+\b', text.lower()) if w not in stop and len(w) > 2]
    freq = Counter(words)

    scored = []
    for i, sent in enumerate(sentences):
        sw = [w.lower() for w in re.findall(r'\b[a-z]+\b', sent.lower()) if w not in stop]
        score = sum(freq.get(w, 0) for w in sw) / max(len(sw), 1)
        # Boost leading sentences
        if i == 0:
            score *= 2.0
        elif i <= 2:
            score *= 1.4
        scored.append((score, i, sent))

    top = sorted(scored, reverse=True)[:3]
    top_ordered = sorted(top, key=lambda x: x[1])  # preserve original order
    summary = " ".join(s for _, _, s in top_ordered)

    return {"summary": summary, "sentences": len(sentences), "method": "extractive"}


@app.get("/api/sentiment/history/{ticker}")
def get_sentiment_history(ticker: str, days: int = 90):
    """
    Return per-week average signal score and return for a ticker,
    mined from correlation_data.json (our training dataset).
    """
    import json, pathlib
    from datetime import datetime, timedelta
    from collections import defaultdict

    ticker = ticker.upper()
    corr_path = pathlib.Path(__file__).parent / "correlation_data.json"
    try:
        with open(corr_path) as f:
            events = json.load(f).get("events", [])
    except Exception:
        return {"ticker": ticker, "history": []}

    cutoff = datetime.now() - timedelta(days=days)
    ticker_events = []
    for e in events:
        if e.get("ticker") != ticker:
            continue
        try:
            ed = datetime.fromisoformat(str(e.get("event_date", ""))[:10])
        except Exception:
            continue
        if ed < cutoff:
            continue
        ticker_events.append((ed, e))

    if not ticker_events:
        return {"ticker": ticker, "history": [], "message": "No events in range"}

    # Bucket by week
    week_buckets = defaultdict(list)
    for ed, e in ticker_events:
        week_key = ed.strftime("%Y-W%W")
        week_buckets[week_key].append(e)

    history = []
    for week, evts in sorted(week_buckets.items()):
        signals = [e.get("signal", 0) for e in evts if e.get("signal") is not None]
        returns_7d = [e.get("return_7d") for e in evts if e.get("return_7d") is not None]
        returns_1d = [e.get("return_1d") for e in evts if e.get("return_1d") is not None]
        history.append({
            "week": week,
            "event_count": len(evts),
            "avg_signal": round(sum(signals) / len(signals), 2) if signals else 0,
            "avg_return_7d": round(sum(returns_7d) / len(returns_7d), 2) if returns_7d else None,
            "avg_return_1d": round(sum(returns_1d) / len(returns_1d), 2) if returns_1d else None,
            "event_types": list(set(e.get("event_type", "unknown") for e in evts)),
        })

    return {"ticker": ticker, "history": history, "total_events": len(ticker_events), "weeks": len(history)}


@app.get("/api/geopolitical/risk")
def get_geopolitical_risk(days: int = 7):
    """
    Return regional geopolitical risk scores by searching GDELT for risk keywords per region.
    """
    REGIONS = [
        {"name": "Middle East",   "keywords": ["Israel Gaza Lebanon Iran Syria Yemen Iraq", "middle east conflict"]},
        {"name": "Eastern Europe","keywords": ["Ukraine Russia NATO war sanctions", "eastern europe"]},
        {"name": "East Asia",     "keywords": ["China Taiwan North Korea South China Sea", "east asia tension"]},
        {"name": "South Asia",    "keywords": ["India Pakistan Kashmir Afghanistan", "south asia crisis"]},
        {"name": "Africa",        "keywords": ["Sudan Somalia coup civil war Africa", "africa conflict"]},
        {"name": "Latin America", "keywords": ["Venezuela Colombia Mexico cartel narco", "latin america"]},
        {"name": "United States", "keywords": ["US tariffs sanctions trade war foreign policy", "america geopolitical"]},
        {"name": "Europe",        "keywords": ["EU Brexit sanctions trade dispute Europe", "europe diplomatic"]},
    ]

    region_scores = []
    for region in REGIONS:
        try:
            results = gdelt_service.search_news(query=region["keywords"][0], timespan=days, max_results=20)
            article_count = len(results) if results else 0
            # Risk score = normalized article count (more crisis news = higher risk)
            raw_score = min(100, article_count * 5)
            region_scores.append({
                "region": region["name"],
                "risk_score": raw_score,
                "risk_level": "HIGH" if raw_score >= 60 else "MEDIUM" if raw_score >= 30 else "LOW",
                "article_count": article_count,
                "sample_headlines": [r.get("title", "") for r in (results or [])[:3]],
            })
        except Exception:
            region_scores.append({"region": region["name"], "risk_score": 0, "risk_level": "LOW", "article_count": 0, "sample_headlines": []})

    region_scores.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"regions": region_scores, "as_of": datetime.now().isoformat(), "days_analyzed": days}


@app.get("/api/predict/explain/{ticker}")
def explain_stock_movement(ticker: str, limit: int = 10):
    """
    Return the top government events that historically correlated with price moves for a ticker.
    Powers the 'Why did this move?' explainer modal.
    """
    import json, pathlib
    from datetime import datetime

    ticker = ticker.upper()
    corr_path = pathlib.Path(__file__).parent / "correlation_data.json"
    try:
        with open(corr_path) as f:
            events = json.load(f).get("events", [])
    except Exception:
        return {"ticker": ticker, "events": []}

    ticker_events = [e for e in events if e.get("ticker") == ticker]

    if not ticker_events:
        return {"ticker": ticker, "events": [], "message": "No historical events found"}

    # Score events by absolute 7-day return impact
    scored = []
    for e in ticker_events:
        r7 = e.get("return_7d")
        r1 = e.get("return_1d")
        try:
            r7 = float(r7) if r7 is not None else None
            r1 = float(r1) if r1 is not None else None
        except (TypeError, ValueError):
            continue
        if r7 is None and r1 is None:
            continue
        impact = abs(r7 if r7 is not None else r1)
        scored.append((impact, len(scored), e))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_events = []
    for impact, _idx, e in scored[:limit]:
        r7 = e.get("return_7d")
        top_events.append({
            "event_type": e.get("event_type", "unknown"),
            "event_title": e.get("event_title") or e.get("description") or e.get("event_type", "Government Event"),
            "event_date": e.get("event_date", ""),
            "source": e.get("source", ""),
            "return_1d": e.get("return_1d"),
            "return_7d": r7,
            "return_30d": e.get("return_30d"),
            "direction": "UP" if (r7 or 0) > 0 else "DOWN",
            "signal": e.get("signal", {}).get("signal_score", 50) if isinstance(e.get("signal"), dict) else (e.get("signal") or 0),
            "award_amount": e.get("Award Amount") or e.get("award_amount"),
        })

    # Summary stats
    up_events = [ev for ev in top_events if ev["direction"] == "UP"]
    return {
        "ticker": ticker,
        "events": top_events,
        "total_events": len(ticker_events),
        "bullish_pct": round(len(up_events) / len(top_events) * 100) if top_events else 50,
        "avg_7d_return": round(sum(abs(ev.get("return_7d") or 0) for ev in top_events) / len(top_events), 2) if top_events else 0,
    }
