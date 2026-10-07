"""
Database connection and session handling using SQLite and SQLAlchemy.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import DATABASE_URL

# connect_args={"check_same_thread": False} is required for SQLite in multithreaded FastAPI apps
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Enable foreign key support, WAL mode, and Unicode-aware lower function for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
    # Enables full Unicode/Cyrillic case-insensitivity in SQL LOWER()
    dbapi_connection.create_function("lower", 1, lambda s: s.lower() if s is not None else None)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency to get a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
