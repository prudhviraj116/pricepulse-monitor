import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import bcrypt

from .database import engine, Base, get_db
from . import models, schemas, scraper, scheduler, alerts

# JWT Security Config
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_FOR_PRICEPULSE_MONITOR_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="api/auth/token", auto_error=False)

# Security Utility Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup
    Base.metadata.create_all(bind=engine)
    
    # Auto-create default demo user if not present
    db = next(get_db())
    try:
        demo_email = "demo@pricepulse.com"
        demo_user = db.query(models.User).filter(models.User.email == demo_email).first()
        if not demo_user:
            demo_user = models.User(
                email=demo_email,
                hashed_password=get_password_hash("demopassword")
            )
            db.add(demo_user)
            db.commit()
    finally:
        db.close()

    # Start background scheduler loop
    scheduler_task = asyncio.create_task(scheduler.start_scheduler_loop())
    yield
    scheduler_task.cancel()

app = FastAPI(
    title="PricePulse Competitor Price Monitor API",
    description="Automated scraping, calculations, and alerting for e-commerce price monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_bearer), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # If no token is provided, fall back to the default demo user to keep the app instantly runnable
    if not token:
        demo_user = db.query(models.User).filter(models.User.email == "demo@pricepulse.com").first()
        if demo_user:
            return demo_user
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


# --- AUTH ENDPOINTS ---

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/demo", response_model=schemas.Token)
def login_as_demo_user(db: Session = Depends(get_db)):
    """
    Returns an access token for the default demo account, enabling instant onboarding.
    """
    demo_email = "demo@pricepulse.com"
    user = db.query(models.User).filter(models.User.email == demo_email).first()
    if not user:
        # Create it if it doesn't exist
        user = models.User(
            email=demo_email,
            hashed_password=get_password_hash("demopassword")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- PRODUCTS ENDPOINTS ---

@app.post("/api/products/", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: schemas.ProductCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_product = models.Product(
        user_id=current_user.id,
        name=product.name,
        target_price=product.target_price,
        alert_threshold_percent=product.alert_threshold_percent if product.alert_threshold_percent is not None else Decimal("5.00"),
        is_active=product.is_active if product.is_active is not None else True
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/api/products/", response_model=List[schemas.ProductResponse])
def list_products(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(models.Product).filter(models.Product.user_id == current_user.id).all()
    return products

@app.delete("/api/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == id, models.Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return


# --- COMPETITOR URLS ENDPOINTS ---

@app.post("/api/products/{id}/competitors/", response_model=schemas.CompetitorURLResponse, status_code=status.HTTP_201_CREATED)
def add_competitor_url(
    id: str,
    payload: schemas.CompetitorURLCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify product belongs to user
    product = db.query(models.Product).filter(models.Product.id == id, models.Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    domain_key = scraper.detect_domain_key(payload.url)
    if not domain_key:
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL domain. Supported domains are: books.toscrape.com, webscraper.io, amazon, flipkart"
        )
        
    # Check if URL already added for this product
    existing = db.query(models.CompetitorURL).filter(
        models.CompetitorURL.product_id == id,
        models.CompetitorURL.url == payload.url
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This competitor URL is already tracked for this product")

    # Create record
    competitor = models.CompetitorURL(
        product_id=id,
        url=payload.url,
        domain_selector_key=domain_key
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    
    # Perform an initial scrape immediately so that we have a baseline price node right away!
    logger.info(f"Triggering initial scrape for new competitor URL: {competitor.url}")
    scrape_res = scraper.scrape_product(competitor.url, domain_key)
    if scrape_res["success"]:
        price_val = Decimal(str(scrape_res["price"]))
        
        # Save to Price History
        history = models.PriceHistory(
            competitor_url_id=competitor.id,
            price=price_val,
            scraped_at=datetime.utcnow()
        )
        db.add(history)
        
        # Reset error count on success
        competitor.error_count = 0
        competitor.last_error_message = None
        
        # Update competitor fields
        competitor.last_scraped_price = price_val
        competitor.last_scraped_at = datetime.utcnow()
        
        # Check alert state calculation using scheduler logic
        triggered = scheduler.should_trigger_alert(product, competitor, price_val)
        
        p_base = product.target_price
        delta_p = ((p_base - price_val) / p_base) * Decimal("100.0")
        
        # Reset last notified price if price rises back above threshold
        if delta_p < product.alert_threshold_percent:
            competitor.last_notified_price = None
            
        if triggered:
            alerts.send_email_alert(
                db=db,
                product=product,
                competitor_url=competitor,
                previous_price=None,
                new_price=price_val,
                price_drop_percent=delta_p,
                recipient_email=current_user.email
            )
            competitor.last_notified_price = price_val
            
        db.commit()
        db.refresh(competitor)
    else:
        # Scrape failed on initialization: track error state
        competitor.error_count = 1
        competitor.last_error_message = scrape_res["error"] or "Initial scrape failed"
        db.commit()
        db.refresh(competitor)
        
    return competitor

@app.delete("/api/competitors/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    competitor = db.query(models.CompetitorURL).join(models.Product).filter(
        models.CompetitorURL.id == id,
        models.Product.user_id == current_user.id
    ).first()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor URL not found")
        
    db.delete(competitor)
    db.commit()
    return


# --- ANALYTICS & ALERTS ENDPOINTS ---

@app.get("/api/analytics/price-history/{product_id}/", response_model=List[schemas.PriceHistoryNode])
def get_price_history(
    product_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify product ownership
    product = db.query(models.Product).filter(models.Product.id == product_id, models.Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get history nodes
    nodes = (
        db.query(models.PriceHistory)
        .join(models.CompetitorURL)
        .filter(models.CompetitorURL.product_id == product_id)
        .order_by(models.PriceHistory.scraped_at.asc())
        .all()
    )
    
    history_nodes = []
    for node in nodes:
        history_nodes.append(
            schemas.PriceHistoryNode(
                scraped_at=node.scraped_at,
                price=node.price,
                competitor_url=node.competitor_url.url
            )
        )
        
    return history_nodes

@app.get("/api/alerts/", response_model=List[schemas.SentAlertResponse])
def get_sent_alerts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch alerts for all products owned by current user
    alert_records = (
        db.query(models.SentAlert)
        .join(models.Product)
        .filter(models.Product.user_id == current_user.id)
        .order_by(models.SentAlert.sent_at.desc())
        .all()
    )
    return alert_records

@app.post("/api/products/scrape-all")
def trigger_scrape_all(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually triggers a scraping cycle for all active URLs and returns results immediately.
    Useful for demonstrating capabilities on demand.
    """
    results = scheduler.run_scraping_cycle(db)
    return results
