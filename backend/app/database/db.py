from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging

logger = logging.getLogger(__name__)

# Use DATABASE_URL from env, or fall back to SQLite in the current directory
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./codereviewer.db"

# For SQLite — ensure the directory exists (needed when using Docker volumes)
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

# SQLite needs check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def wait_for_db(max_retries: int = 10, retry_interval: float = 1.0):
    """Verify the DB is reachable. For SQLite this is near-instant."""
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"Database ready (attempt {attempt})")
            return
        except Exception as e:
            if attempt < max_retries:
                import time
                logger.warning(f"DB not ready ({attempt}/{max_retries}): {e}. Retrying...")
                time.sleep(retry_interval)
            else:
                raise


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()