import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use PostgreSQL in Docker, SQLite local fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # required for SQLite
    )

SessionLocal = sessionmaker(bind=engine)
