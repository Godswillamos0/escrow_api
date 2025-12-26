from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import DATABASE_URL

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Please check your .env file or environment variables.")

SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"sslmode": "require"},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()