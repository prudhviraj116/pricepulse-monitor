import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default to local SQLite database in the backend directory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pricepulse.db")

# If using SQLite, we need to allow access from multiple threads (e.g. for FastAPI and the background scheduler)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
