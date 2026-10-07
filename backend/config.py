"""
Movie Catalog Backend Configuration
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "movies.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# Security
SECRET_KEY = "super-secret-jwt-key-for-movie-catalog-antigravity-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

PARSED_MOVIES_DIR = BASE_DIR / "parsed_movies"
