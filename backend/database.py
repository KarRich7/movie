"""
Database connection and session handling for two separate databases:
- movies.db: Movies, Genres, Actors, Directors, Awards
- users.db: Users, Auth/SMS codes, Reviews, Favorites, Watch History
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import MOVIES_DATABASE_URL, USERS_DATABASE_URL

# 1. Movies Database Engine (movies.db)
movies_engine = create_engine(
    MOVIES_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# 2. Users Database Engine (users.db)
users_engine = create_engine(
    USERS_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

def _setup_sqlite_connection(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
    dbapi_connection.create_function("lower", 1, lambda s: s.lower() if s is not None else None)

event.listen(movies_engine, "connect", _setup_sqlite_connection)
event.listen(users_engine, "connect", _setup_sqlite_connection)

# Session makers
MoviesSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=movies_engine)
UsersSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=users_engine)

# Declarative Bases
MovieBase = declarative_base()
UserBase = declarative_base()

# Backward compatibility aliases
Base = MovieBase
engine = movies_engine
SessionLocal = MoviesSessionLocal

def get_movies_db():
    """FastAPI dependency for Movie Catalog database session (movies.db)."""
    db = MoviesSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_users_db():
    """FastAPI dependency for Users, Auth & Profile database session (users.db)."""
    db = UsersSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Default get_db alias
get_db = get_movies_db

def ensure_database_schema():
    """Ensures tables exist in both databases and migrates data from movies.db to users.db if needed."""
    # Create movies.db tables
    MovieBase.metadata.create_all(bind=movies_engine)
    
    # Create users.db tables
    UserBase.metadata.create_all(bind=users_engine)

    # If users.db is brand new, check if we need to migrate existing user tables from movies.db
    with users_engine.connect() as u_conn:
        u_cursor = u_conn.connection.cursor()
        u_cursor.execute("SELECT COUNT(*) FROM users")
        user_count_in_users_db = u_cursor.fetchone()[0]

        if user_count_in_users_db == 0:
            # Check if movies.db has users
            with movies_engine.connect() as m_conn:
                m_cursor = m_conn.connection.cursor()
                m_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if m_cursor.fetchone():
                    m_cursor.execute("SELECT COUNT(*) FROM users")
                    if m_cursor.fetchone()[0] > 0:
                        print("📦 Migrating existing users from movies.db to users.db...")
                        # Copy users
                        m_cursor.execute("PRAGMA table_info(users)")
                        cols = [r[1] for r in m_cursor.fetchall()]
                        cols_str = ", ".join(cols)
                        m_cursor.execute(f"SELECT {cols_str} FROM users")
                        rows = m_cursor.fetchall()
                        placeholders = ", ".join(["?" for _ in cols])
                        u_cursor.executemany(f"INSERT OR IGNORE INTO users ({cols_str}) VALUES ({placeholders})", rows)
                        u_conn.connection.commit()

                        # Copy phone_verification_codes if any
                        m_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='phone_verification_codes'")
                        if m_cursor.fetchone():
                            m_cursor.execute("SELECT phone, code, created_at, expires_at, is_used FROM phone_verification_codes")
                            p_rows = m_cursor.fetchall()
                            if p_rows:
                                u_cursor.executemany(
                                    "INSERT OR IGNORE INTO phone_verification_codes (phone, code, created_at, expires_at, is_used) VALUES (?, ?, ?, ?, ?)",
                                    p_rows
                                )
                                u_conn.connection.commit()

                        # Copy reviews if any
                        m_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
                        if m_cursor.fetchone():
                            m_cursor.execute("SELECT id, user_id, movie_id, rating, title, content, created_at, updated_at FROM reviews")
                            r_rows = m_cursor.fetchall()
                            if r_rows:
                                u_cursor.executemany(
                                    "INSERT OR IGNORE INTO reviews (id, user_id, movie_id, rating, title, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    r_rows
                                )
                                u_conn.connection.commit()

                        # Copy favorites if any
                        m_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='favorites'")
                        if m_cursor.fetchone():
                            m_cursor.execute("SELECT id, user_id, movie_id, created_at FROM favorites")
                            f_rows = m_cursor.fetchall()
                            if f_rows:
                                u_cursor.executemany(
                                    "INSERT OR IGNORE INTO favorites (id, user_id, movie_id, created_at) VALUES (?, ?, ?, ?)",
                                    f_rows
                                )
                                u_conn.connection.commit()

                        # Copy watch_history if any
                        m_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watch_history'")
                        if m_cursor.fetchone():
                            m_cursor.execute("SELECT id, user_id, movie_id, watched_at, progress_seconds, is_completed FROM watch_history")
                            w_rows = m_cursor.fetchall()
                            if w_rows:
                                u_cursor.executemany(
                                    "INSERT OR IGNORE INTO watch_history (id, user_id, movie_id, watched_at, progress_seconds, is_completed) VALUES (?, ?, ?, ?, ?, ?)",
                                    w_rows
                                )
                                u_conn.connection.commit()
                        print("✨ Users & user features successfully migrated to users.db!")
        u_cursor.close()
