"""
Pydantic schemas (DTOs) for request validation and response serialization.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==================== User Schemas ====================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя (от 3 до 50 символов)")
    email: str = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=6, max_length=100, description="Пароль (от 6 символов)")
    avatar_url: Optional[str] = Field(None, description="URL аватара")


class UserLoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Логин или Email")
    password: str = Field(..., description="Пароль")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    is_admin: bool = False
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==================== Genre, Actor, Director, Award Schemas ====================

class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    movies_count: Optional[int] = None


class ActorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kp_id: Optional[str] = None
    name: str
    photo_url: Optional[str] = None


class DirectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kp_id: Optional[str] = None
    name: str
    photo_url: Optional[str] = None


class AwardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    year: Optional[int] = None
    nomination: Optional[str] = None
    is_winner: bool = True


# ==================== Review Schemas ====================

class ReviewCreateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=10, description="Оценка от 1 до 10")
    title: Optional[str] = Field(None, max_length=255, description="Заголовок отзыва")
    content: str = Field(..., min_length=5, description="Текст отзыва")


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    user_id: int
    user_username: str
    user_avatar: Optional[str] = None
    rating: int
    title: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== Movie Schemas ====================

class MovieListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kp_id: Optional[str] = None
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    slogan: Optional[str] = None
    description: Optional[str] = None
    poster: Optional[str] = None
    duration: Optional[str] = None
    age: Optional[str] = None
    country: Optional[str] = None
    rating_kp: Optional[float] = None
    rating_site: Optional[float] = None
    user_rating_avg: Optional[float] = None
    reviews_count: Optional[int] = 0
    genres: List[str] = []
    directors: List[str] = []
    awards_count: int = 0
    trailer: Optional[str] = None


class MovieDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kp_id: Optional[str] = None
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    slogan: Optional[str] = None
    description: Optional[str] = None
    poster: Optional[str] = None
    posters: List[str] = []
    duration: Optional[str] = None
    age: Optional[str] = None
    country: Optional[str] = None
    budget: Optional[str] = None
    boxoffice: Optional[str] = None
    rating_kp: Optional[float] = None
    rating_site: Optional[float] = None
    user_rating_avg: Optional[float] = None
    reviews_count: int = 0
    trailer: Optional[str] = None
    watch_kp: Optional[str] = None
    watch_rutube: Optional[str] = None
    watch_vk: Optional[str] = None
    gallery: List[str] = []

    genres: List[GenreResponse] = []
    actors: List[ActorResponse] = []
    directors: List[DirectorResponse] = []
    awards: List[AwardResponse] = []
    reviews: List[ReviewResponse] = []

    # Personal user flags (if authenticated)
    is_favorite: bool = False
    in_watch_history: bool = False


class PaginatedMoviesResponse(BaseModel):
    items: List[MovieListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== User Features Schemas (Favorites & History) ====================

class FavoriteItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    created_at: datetime
    movie: MovieListItemResponse


class WatchHistoryCreateRequest(BaseModel):
    progress_seconds: int = Field(0, ge=0, description="Прогресс просмотра в секундах")
    is_completed: bool = Field(False, description="Завершен ли просмотр")


class WatchHistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    watched_at: datetime
    progress_seconds: int
    is_completed: bool
    movie: MovieListItemResponse


# ==================== Randomizer & Stats ====================

class RandomMovieResponse(BaseModel):
    movie: MovieDetailResponse
    reason: str = "Идеальный выбор на вечер!"
    match_mood: Optional[str] = None


class CatalogStatsResponse(BaseModel):
    total_movies: int
    total_actors: int
    total_directors: int
    total_genres: int
    total_awards: int
    total_users: int
    total_reviews: int
    avg_rating: float
