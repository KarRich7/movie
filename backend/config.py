"""
Movie Catalog Backend Configuration
Two separate databases:
- movies.db: Movie Catalog, genres, actors, directors, awards
- users.db: Registered users, auth, reviews, favorites, watch history
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Separate SQLite Database Paths
MOVIES_DB_PATH = BASE_DIR / "movies.db"
USERS_DB_PATH = BASE_DIR / "users.db"

MOVIES_DATABASE_URL = f"sqlite:///{MOVIES_DB_PATH.as_posix()}"
USERS_DATABASE_URL = f"sqlite:///{USERS_DB_PATH.as_posix()}"

# Backward compatibility alias
DB_PATH = MOVIES_DB_PATH
DATABASE_URL = MOVIES_DATABASE_URL

# Security
SECRET_KEY = "super-secret-jwt-key-for-movie-catalog-antigravity-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

PARSED_MOVIES_DIR = BASE_DIR / "parsed_movies"
