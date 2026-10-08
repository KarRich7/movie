"""
Metadata router: genres, actors, directors, awards, and catalog statistics.
Uses db_movies (movies.db) for movie catalog entities and db_users (users.db) for user statistics.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_movies_db, get_users_db
from backend.models import Genre, Actor, Director, Award, Movie, User, Review
from backend.schemas import (
    GenreResponse, ActorResponse, DirectorResponse, AwardResponse, CatalogStatsResponse
)

router = APIRouter(prefix="/api", tags=["Справочники и метаданные"])


@router.get("/genres", response_model=List[GenreResponse], summary="Список всех жанров с количеством фильмов")
def get_genres(db: Session = Depends(get_movies_db)):
    """Возвращает список всех доступных жанров с подсчетом привязанных фильмов из movies.db."""
    genres = db.query(Genre).order_by(Genre.name.asc()).all()
    result = []
    for g in genres:
        result.append(GenreResponse(
            id=g.id,
            name=g.name,
            slug=g.slug,
            movies_count=len(g.movies)
        ))
    return result


@router.get("/actors", response_model=List[ActorResponse], summary="Список и поиск актеров")
def get_actors(
    q: Optional[str] = Query(None, description="Поиск по имени актера"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_movies_db)
):
    """Возвращает актеров с возможностью поиска по имени."""
    query = db.query(Actor)
    if q:
        query = query.filter(Actor.name.ilike(f"%{q.strip()}%"))
    actors = query.order_by(Actor.name.asc()).limit(limit).all()
    return [ActorResponse.model_validate(a) for a in actors]


@router.get("/directors", response_model=List[DirectorResponse], summary="Список режиссеров")
def get_directors(
    q: Optional[str] = Query(None, description="Поиск по имени режиссера"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_movies_db)
):
    """Возвращает режиссеров с возможностью поиска."""
    query = db.query(Director)
    if q:
        query = query.filter(Director.name.ilike(f"%{q.strip()}%"))
    directors = query.order_by(Director.name.asc()).limit(limit).all()
    return [DirectorResponse.model_validate(d) for d in directors]


@router.get("/awards", response_model=List[str], summary="Список категорий кинопремий")
def get_awards_list(db: Session = Depends(get_movies_db)):
    """Возвращает уникальные названия кинопремий (Оскар, Золотой глобус и т.д.)."""
    awards = db.query(Award.name).distinct().order_by(Award.name.asc()).all()
    return [a[0] for a in awards if a[0]]


@router.get("/stats", response_model=CatalogStatsResponse, summary="Общая статистика каталога")
def get_catalog_stats(
    db_movies: Session = Depends(get_movies_db),
    db_users: Session = Depends(get_users_db)
):
    """Возвращает аналитическую статистику из двух независимых баз данных (movies.db и users.db)."""
    total_movies = db_movies.query(Movie).count()
    total_actors = db_movies.query(Actor).count()
    total_directors = db_movies.query(Director).count()
    total_genres = db_movies.query(Genre).count()
    total_awards = db_movies.query(Award).count()

    total_users = db_users.query(User).count()
    total_reviews = db_users.query(Review).count()

    avg_rating_row = db_movies.query(func.avg(Movie.rating_kp)).first()
    avg_rating = round(float(avg_rating_row[0]), 2) if avg_rating_row and avg_rating_row[0] else 0.0

    return CatalogStatsResponse(
        total_movies=total_movies,
        total_actors=total_actors,
        total_directors=total_directors,
        total_genres=total_genres,
        total_awards=total_awards,
        total_users=total_users,
        total_reviews=total_reviews,
        avg_rating=avg_rating
    )
