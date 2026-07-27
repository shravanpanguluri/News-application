from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tier = Column(String, default="free")  # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    api_key = Column(String, unique=True, index=True)

    # Tier limits
    daily_limit = Column(Integer, default=50)  # 50 for free, 5000 for pro, unlimited for enterprise
    requests_today = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)
    watchlist_keywords = Column(JSON, default=list)  # ["H1B", "GST", "Bitcoin"]

    articles = relationship("Article", back_populates="user")
    alerts = relationship("Alert", back_populates="user")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text)
    source = Column(String)  # pib, federal_register, govinfo, data_gov_in
    country = Column(String)  # in, us
    category = Column(String)  # economy, health, education, regulation, etc.
    url = Column(String, unique=True, nullable=False)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    impact_score = Column(Integer, default=0)  # 0-10
    impact_level = Column(String, default="Low")  # Low, Medium, High
    sentiment = Column(String, default="Neutral")  # Positive, Negative, Neutral
    tags = Column(JSON, default=list)
    article_metadata = Column(JSON, default=dict)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="articles")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="alerts")

    keyword = Column(String)
    category = Column(String)
    country = Column(String)
    alert_type = Column(String)  # email, push, webhook
    webhook_url = Column(String)  # for enterprise tier
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(String)  # free, pro, enterprise
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    amount = Column(Integer)  # in INR


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    endpoint = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    response_time = Column(Float)  # in milliseconds


class ReadingHistory(Base):
    __tablename__ = "reading_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    article_id = Column(String)  # Store article URL or ID
    category = Column(String)
    topics = Column(JSON, default=list)  # Extracted topics/keywords
    read_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_duration = Column(Integer, default=0)  # seconds spent reading
    
    user = relationship("User", backref="reading_history")
