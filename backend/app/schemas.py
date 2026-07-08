from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Competitor URL Schemas
class CompetitorURLCreate(BaseModel):
    url: str

class CompetitorURLResponse(BaseModel):
    id: str
    product_id: str
    url: str
    domain_selector_key: str
    last_scraped_price: Optional[Decimal] = None
    last_scraped_at: Optional[datetime] = None
    last_notified_price: Optional[Decimal] = None
    error_count: int
    last_error_message: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

# Price History Schemas
class PriceHistoryResponse(BaseModel):
    id: str
    competitor_url_id: str
    price: Decimal
    scraped_at: datetime

    class Config:
        from_attributes = True

# Product Schemas
class ProductCreate(BaseModel):
    name: str
    target_price: Decimal = Field(..., gt=0)
    alert_threshold_percent: Optional[Decimal] = Decimal("5.00")
    is_active: Optional[bool] = True

class ProductResponse(BaseModel):
    id: str
    user_id: str
    name: str
    target_price: Decimal
    alert_threshold_percent: Decimal
    is_active: bool
    created_at: datetime
    competitor_urls: List[CompetitorURLResponse] = []

    class Config:
        from_attributes = True

# Sent Alert Schemas
class SentAlertResponse(BaseModel):
    id: str
    product_id: str
    competitor_url_id: str
    previous_price: Optional[Decimal] = None
    new_price: Decimal
    price_drop_percent: Decimal
    recipient_email: str
    sent_at: datetime

    class Config:
        from_attributes = True

# Analytics Node (aggregated for charts)
class PriceHistoryNode(BaseModel):
    scraped_at: datetime
    price: Decimal
    competitor_url: str
