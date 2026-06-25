from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    tier = Column(String, default="free")
    created_at = Column(DateTime, default=datetime.utcnow)
    api_key = Column(String, unique=True, index=True)
    daily_limit = Column(Integer, default=50)
    requests_today = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)
    watchlist_keywords = Column(JSON, default=list)

    articles = relationship("Article", back_populates="user")
    alerts = relationship("Alert", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    api_usage = relationship("APIUsage", back_populates="user")
    reading_history = relationship("ReadingHistory", back_populates="user")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text)
    source = Column(String)
    country = Column(String)
    category = Column(String)
    url = Column(String, nullable=False, unique=True)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    impact_score = Column(Integer, default=0)
    impact_level = Column(String, default="Low")
    sentiment = Column(String, default="Neutral")
    tags = Column(JSON, default=list)
    article_metadata = Column(JSON, default=dict)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="articles")

    @property
    def ai_summary(self):
        metadata = self.article_metadata or {}
        return metadata.get("ai_summary")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    keyword = Column(String)
    category = Column(String)
    country = Column(String)
    alert_type = Column(String)
    webhook_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(String)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    amount = Column(Integer)

    user = relationship("User", back_populates="subscriptions")


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    endpoint = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    response_time_ms = Column(Integer)

    user = relationship("User", back_populates="api_usage")


class ReadingHistory(Base):
    __tablename__ = "reading_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    article_id = Column(String)
    category = Column(String)
    topics = Column(JSON, default=list)
    read_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_duration = Column(Integer)

    user = relationship("User", back_populates="reading_history")
