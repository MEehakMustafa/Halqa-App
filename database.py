from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import DATABASE_URL

# engine — manages the actual connection to PostgreSQL
engine = create_engine(DATABASE_URL)

# SessionLocal — creates a new database session for each request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base — all our database models will inherit from this
Base = declarative_base()


def get_db():
    """
    Creates a database session, gives it to the route,
    then closes it automatically when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()