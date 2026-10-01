import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

database_url = make_url(settings.DATABASE_URL)
if database_url.get_backend_name() != "postgresql" and os.getenv("AHAAR_TESTING") != "1":
    raise RuntimeError(
        "Aahar requires PostgreSQL. Configure DATABASE_URL with a PostgreSQL URL; "
        "SQLite is permitted only when AHAAR_TESTING=1."
    )

engine = create_engine(database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
