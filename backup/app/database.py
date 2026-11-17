from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Creates the PostgreSQL database engine using your configuration settings
engine = create_engine(settings.DATABASE_URL)

# Session factory for handling database transactions per request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your SQLAlchemy models
Base = declarative_base()

# Dependency used in routers to get an active database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()