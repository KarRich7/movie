"""
User features router: Favorites system and Watch History.
Uses db_users (users.db) to manage favorites & history,
and db_movies (movies.db) to look up movie cards and metadata.
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_movies_db, get_users_db
from backend.models import Favorite, WatchHistory, Movie, User
from backend.schemas import (
    FavoriteItemResponse, WatchHistoryItemResponse, WatchHistoryCreateRequest,
    MovieListItemResponse
)
from backend.security import get_current_user
from backend.routers.movies import _movie_to_list_item

router = APIRouter(prefix="/api", tags=["Избранное и история просмотров"])


# ==================== Favorites ====================

@router.get("/favorites", response_model=List[FavoriteItemResponse], summary="Список избранных фильмов пользователя")
def get_user_favorites(
    db_movies: Session = Depends(get_movies_db),
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Возвращает все фильмы, добавленные текущим пользователем в избранное."""
    favorites = db_users.query(Favorite).filter(
        Favorite.user_id == current_user.id
    ).order_by(Favorite.created_at.desc()).all()
    
    # Collect movie ids
    movie_ids = [fav.movie_id for fav in favorites]
    movies_map = {}
    if movie_ids:
        movies = db_movies.query(Movie).filter(Movie.id.in_(movie_ids)).all()
        movies_map = {m.id: m for m in movies}

    result = []
    for fav in favorites:
        movie = movies_map.get(fav.movie_id)
        if movie:
            result.append(FavoriteItemResponse(
                id=fav.id,
                movie_id=fav.movie_id,
                created_at=fav.created_at,
                movie=_movie_to_list_item(movie, db_users)
            ))
    return result


@router.post("/favorites/{movie_id}", status_code=status.HTTP_201_CREATED, summary="Добавить фильм в избранное")
def add_to_favorites(
    movie_id: int,
    db_movies: Session = Depends(get_movies_db),
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Добавляет фильм в избранное текущего пользователя."""
    movie = db_movies.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Фильм #{movie_id} не найден"
        )

    existing = db_users.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.movie_id == movie_id
    ).first()

    if existing:
        return {"detail": "Фильм уже находится в избранном", "movie_id": movie_id, "is_favorite": True}

    fav = Favorite(user_id=current_user.id, movie_id=movie_id)
    db_users.add(fav)
    db_users.commit()

    return {"detail": "Фильм успешно добавлен в избранное", "movie_id": movie_id, "is_favorite": True}


@router.delete("/favorites/{movie_id}", summary="Удалить фильм из избранного")
def remove_from_favorites(
    movie_id: int,
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Удаляет фильм из избранного текущего пользователя."""
    fav = db_users.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.movie_id == movie_id
    ).first()

    if not fav:
        return {"detail": "Фильм не был в избранном", "movie_id": movie_id, "is_favorite": False}

    db_users.delete(fav)
    db_users.commit()
    return {"detail": "Фильм удален из избранного", "movie_id": movie_id, "is_favorite": False}


@router.get("/favorites/check/{movie_id}", summary="Проверить статус избранного для фильма")
def check_favorite_status(
    movie_id: int,
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Быстрая проверка: находится ли фильм в избранном у пользователя."""
    is_fav = db_users.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.movie_id == movie_id
    ).first() is not None
    return {"movie_id": movie_id, "is_favorite": is_fav}


# ==================== Watch History ====================

@router.get("/history", response_model=List[WatchHistoryItemResponse], summary="История просмотров пользователя")
def get_user_watch_history(
    db_movies: Session = Depends(get_movies_db),
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Возвращает историю просмотров пользователя, отсортированную от недавних к старым."""
    history = db_users.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id
    ).order_by(WatchHistory.watched_at.desc()).all()

    movie_ids = [h.movie_id for h in history]
    movies_map = {}
    if movie_ids:
        movies = db_movies.query(Movie).filter(Movie.id.in_(movie_ids)).all()
        movies_map = {m.id: m for m in movies}

    result = []
    for h in history:
        movie = movies_map.get(h.movie_id)
        if movie:
            result.append(WatchHistoryItemResponse(
                id=h.id,
                movie_id=h.movie_id,
                watched_at=h.watched_at,
                progress_seconds=h.progress_seconds,
                is_completed=h.is_completed,
                movie=_movie_to_list_item(movie, db_users)
            ))
    return result


@router.post("/history/{movie_id}", summary="Зафиксировать просмотр фильма в истории")
def record_movie_watch(
    movie_id: int,
    req: WatchHistoryCreateRequest,
    db_movies: Session = Depends(get_movies_db),
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Добавляет фильм в историю или обновляет время последнего просмотра и прогресс."""
    movie = db_movies.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Фильм #{movie_id} не найден"
        )

    history_item = db_users.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id,
        WatchHistory.movie_id == movie_id
    ).first()

    if history_item:
        history_item.watched_at = datetime.utcnow()
        history_item.progress_seconds = req.progress_seconds
        history_item.is_completed = req.is_completed
    else:
        history_item = WatchHistory(
            user_id=current_user.id,
            movie_id=movie_id,
            watched_at=datetime.utcnow(),
            progress_seconds=req.progress_seconds,
            is_completed=req.is_completed
        )
        db_users.add(history_item)

    db_users.commit()
    return {
        "detail": "Просмотр зафиксирован",
        "movie_id": movie_id,
        "progress_seconds": history_item.progress_seconds,
        "is_completed": history_item.is_completed
    }


@router.delete("/history/{movie_id}", summary="Удалить фильм из истории просмотров")
def remove_from_history(
    movie_id: int,
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Удаляет конкретный фильм из истории просмотров."""
    item = db_users.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id,
        WatchHistory.movie_id == movie_id
    ).first()

    if item:
        db_users.delete(item)
        db_users.commit()

    return {"detail": "Фильм удален из истории просмотров", "movie_id": movie_id}


@router.delete("/history", summary="Полностью очистить историю просмотров")
def clear_all_history(
    db_users: Session = Depends(get_users_db),
    current_user: User = Depends(get_current_user)
):
    """Полностью очищает историю просмотров пользователя."""
    deleted_count = db_users.query(WatchHistory).filter(WatchHistory.user_id == current_user.id).delete()
    db_users.commit()
    return {"detail": "История просмотров очищена", "deleted_count": deleted_count}
