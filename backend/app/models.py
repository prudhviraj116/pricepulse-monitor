import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Numeric, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    target_price = Column(Numeric(10, 2), nullable=False)
    alert_threshold_percent = Column(Numeric(5, 2), default=5.00)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="products")
    competitor_urls = relationship("CompetitorURL", back_populates="product", cascade="all, delete-orphan")
    sent_alerts = relationship("SentAlert", back_populates="product", cascade="all, delete-orphan")


class CompetitorURL(Base):
    __tablename__ = "competitor_urls"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)
    domain_selector_key = Column(String(50), nullable=False)  # e.g., 'books_toscrape', 'webscraper_io'
    last_scraped_price = Column(Numeric(10, 2), nullable=True)
    last_scraped_at = Column(DateTime, nullable=True)
    last_notified_price = Column(Numeric(10, 2), nullable=True)
    error_count = Column(Integer, default=0)
    last_error_message = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    product = relationship("Product", back_populates="competitor_urls")
    price_history = relationship("PriceHistory", back_populates="competitor_url", cascade="all, delete-orphan")
    sent_alerts = relationship("SentAlert", back_populates="competitor_url", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    competitor_url_id = Column(String, ForeignKey("competitor_urls.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    competitor_url = relationship("CompetitorURL", back_populates="price_history")


class SentAlert(Base):
    __tablename__ = "sent_alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    competitor_url_id = Column(String, ForeignKey("competitor_urls.id", ondelete="CASCADE"), nullable=False)
    previous_price = Column(Numeric(10, 2), nullable=True)
    new_price = Column(Numeric(10, 2), nullable=False)
    price_drop_percent = Column(Numeric(5, 2), nullable=False)
    recipient_email = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="sent_alerts")
    competitor_url = relationship("CompetitorURL", back_populates="sent_alerts")
