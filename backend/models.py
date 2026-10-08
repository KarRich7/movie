"""
SQLAlchemy models for two separate databases:
1. movies.db (MovieBase): Movie, Genre, Actor, Director, Award
2. users.db (UserBase): User, PhoneVerificationCode, Review, Favorite, WatchHistory
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, Table, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.database import MovieBase, UserBase

# ==================== 1. MOVIES DATABASE (movies.db) ====================

movie_genres = Table(
    "movie_genres",
    MovieBase.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)
)

movie_actors = Table(
    "movie_actors",
    MovieBase.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("actor_id", Integer, ForeignKey("actors.id", ondelete="CASCADE"), primary_key=True),
    Column("order_num", Integer, default=0)
)

movie_directors = Table(
    "movie_directors",
    MovieBase.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("director_id", Integer, ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True)
)


class Movie(MovieBase):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    kp_id = Column(String(50), unique=True, index=True, nullable=True)
    title = Column(String(255), nullable=False, index=True)
    original_title = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True, index=True)
    slogan = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    poster = Column(String(500), nullable=True)
    posters_json = Column(Text, nullable=True)  # JSON-encoded array of URLs
    duration = Column(String(100), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    age = Column(String(20), nullable=True)
    country = Column(String(255), nullable=True)
    budget = Column(String(100), nullable=True)
    boxoffice = Column(String(100), nullable=True)
    rating_kp = Column(Float, nullable=True, default=0.0, index=True)
    rating_site = Column(Float, nullable=True, default=0.0, index=True)
    trailer = Column(String(500), nullable=True)
    watch_kp = Column(String(500), nullable=True)
    watch_rutube = Column(String(500), nullable=True)
    watch_vk = Column(String(500), nullable=True)
    gallery_json = Column(Text, nullable=True)  # JSON-encoded array of URLs
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships within movies.db
    genres = relationship("Genre", secondary=movie_genres, back_populates="movies", lazy="selectin")
    actors = relationship("Actor", secondary=movie_actors, back_populates="movies", lazy="selectin")
    directors = relationship("Director", secondary=movie_directors, back_populates="movies", lazy="selectin")
    awards = relationship("Award", back_populates="movie", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title}', year={self.year})>"


class Genre(MovieBase):
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    movies = relationship("Movie", secondary=movie_genres, back_populates="genres")

    def __repr__(self):
        return f"<Genre(id={self.id}, name='{self.name}')>"


class Actor(MovieBase):
    __tablename__ = "actors"

    id = Column(Integer, primary_key=True, index=True)
    kp_id = Column(String(50), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    photo_url = Column(String(500), nullable=True)

    movies = relationship("Movie", secondary=movie_actors, back_populates="actors")

    def __repr__(self):
        return f"<Actor(id={self.id}, name='{self.name}')>"


class Director(MovieBase):
    __tablename__ = "directors"

    id = Column(Integer, primary_key=True, index=True)
    kp_id = Column(String(50), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    photo_url = Column(String(500), nullable=True)

    movies = relationship("Movie", secondary=movie_directors, back_populates="directors")

    def __repr__(self):
        return f"<Director(id={self.id}, name='{self.name}')>"


class Award(MovieBase):
    __tablename__ = "awards"

    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)  # e.g., "Оскар", "Золотой глобус"
    year = Column(Integer, nullable=True, index=True)
    nomination = Column(Text, nullable=True)
    is_winner = Column(Boolean, default=True)

    movie = relationship("Movie", back_populates="awards")

    def __repr__(self):
        return f"<Award(id={self.id}, name='{self.name}', movie_id={self.movie_id})>"


# ==================== 2. USERS DATABASE (users.db) ====================

class User(UserBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(50), unique=True, nullable=True, index=True)
    vk_id = Column(String(100), unique=True, nullable=True, index=True)
    google_id = Column(String(100), unique=True, nullable=True, index=True)
    auth_provider = Column(String(50), default="email")  # "email", "phone", "vk", "google"
    hashed_password = Column(String(255), nullable=True)
    salt = Column(String(64), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships within users.db
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    watch_history = relationship("WatchHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', auth_provider='{self.auth_provider}')>"


class PhoneVerificationCode(UserBase):
    __tablename__ = "phone_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(50), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

    def __repr__(self):
        return f"<PhoneVerificationCode(phone='{self.phone}', code='{self.code}', used={self.is_used})>"


class Review(UserBase):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(Integer, nullable=False, index=True)  # References Movie in movies.db logically
    rating = Column(Integer, nullable=False)  # 1 to 10
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="reviews", lazy="joined")

    __table_args__ = (
        Index("idx_review_movie_user", "movie_id", "user_id"),
    )

    def __repr__(self):
        return f"<Review(id={self.id}, user_id={self.user_id}, movie_id={self.movie_id}, rating={self.rating})>"


class Favorite(UserBase):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(Integer, nullable=False, index=True)  # References Movie in movies.db logically
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie_favorite"),
    )

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, movie_id={self.movie_id})>"


class WatchHistory(UserBase):
    __tablename__ = "watch_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(Integer, nullable=False, index=True)  # References Movie in movies.db logically
    watched_at = Column(DateTime, default=datetime.utcnow, index=True)
    progress_seconds = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)

    user = relationship("User", back_populates="watch_history")

    __table_args__ = (
        Index("idx_history_user_movie", "user_id", "movie_id"),
    )

    def __repr__(self):
        return f"<WatchHistory(user_id={self.user_id}, movie_id={self.movie_id}, watched_at={self.watched_at})>"
