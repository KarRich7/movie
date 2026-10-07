"""
Movies router with advanced search, filtering, detailed view, and the 'Random movie for the evening' generator.
"""
import json
import random
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, and_, desc, asc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Movie, Genre, Actor, Director, Award, Review, Favorite, WatchHistory, User
)
from backend.schemas import (
    MovieListItemResponse, MovieDetailResponse, PaginatedMoviesResponse,
    RandomMovieResponse, GenreResponse, ActorResponse, DirectorResponse,
    AwardResponse, ReviewResponse
)
from backend.security import get_current_user_optional

router = APIRouter(prefix="/api/movies", tags=["Фильмы и поиск"])


def _calculate_user_rating(movie: Movie) -> tuple[Optional[float], int]:
    """Calculates average user review rating and review count."""
    reviews = movie.reviews or []
    if not reviews:
        return None, 0
    avg = sum(r.rating for r in reviews) / len(reviews)
    return round(avg, 1), len(reviews)


def _movie_to_list_item(m: Movie) -> MovieListItemResponse:
    """Helper to transform SQLAlchemy Movie model to MovieListItemResponse."""
    user_avg, rev_count = _calculate_user_rating(m)
    return MovieListItemResponse(
        id=m.id,
        kp_id=m.kp_id,
        title=m.title,
        original_title=m.original_title,
        year=m.year,
        slogan=m.slogan,
        description=m.description,
        poster=m.poster,
        duration=m.duration,
        age=m.age,
        country=m.country,
        rating_kp=m.rating_kp,
        rating_site=m.rating_site,
        user_rating_avg=user_avg,
        reviews_count=rev_count,
        genres=[g.name for g in m.genres],
        directors=[d.name for d in m.directors],
        awards_count=len(m.awards or []),
        trailer=m.trailer
    )


def _movie_to_detail(m: Movie, current_user: Optional[User], db: Session) -> MovieDetailResponse:
    """Helper to transform SQLAlchemy Movie model to full MovieDetailResponse."""
    user_avg, rev_count = _calculate_user_rating(m)
    
    posters = []
    if m.posters_json:
        try:
            posters = json.loads(m.posters_json)
        except Exception:
            pass

    gallery = []
    if m.gallery_json:
        try:
            gallery = json.loads(m.gallery_json)
        except Exception:
            pass

    # Personal flags
    is_favorite = False
    in_watch_history = False
    if current_user:
        is_favorite = db.query(Favorite).filter(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == m.id
        ).first() is not None

        in_watch_history = db.query(WatchHistory).filter(
            WatchHistory.user_id == current_user.id,
            WatchHistory.movie_id == m.id
        ).first() is not None

    # Reviews with user metadata
    review_responses = []
    for r in (m.reviews or []):
        review_responses.append(ReviewResponse(
            id=r.id,
            movie_id=r.movie_id,
            user_id=r.user_id,
            user_username=r.user.username if r.user else "Аноним",
            user_avatar=r.user.avatar_url if r.user else None,
            rating=r.rating,
            title=r.title,
            content=r.content,
            created_at=r.created_at,
            updated_at=r.updated_at
        ))

    return MovieDetailResponse(
        id=m.id,
        kp_id=m.kp_id,
        title=m.title,
        original_title=m.original_title,
        year=m.year,
        slogan=m.slogan,
        description=m.description,
        poster=m.poster,
        posters=posters,
        duration=m.duration,
        age=m.age,
        country=m.country,
        budget=m.budget,
        boxoffice=m.boxoffice,
        rating_kp=m.rating_kp,
        rating_site=m.rating_site,
        user_rating_avg=user_avg,
        reviews_count=rev_count,
        trailer=m.trailer,
        watch_kp=m.watch_kp,
        watch_rutube=m.watch_rutube,
        watch_vk=m.watch_vk,
        gallery=gallery,
        genres=[GenreResponse.model_validate(g) for g in m.genres],
        actors=[ActorResponse.model_validate(a) for a in m.actors],
        directors=[DirectorResponse.model_validate(d) for d in m.directors],
        awards=[AwardResponse.model_validate(aw) for aw in m.awards],
        reviews=review_responses,
        is_favorite=is_favorite,
        in_watch_history=in_watch_history
    )


@router.get("", response_model=PaginatedMoviesResponse, summary="Продвинутый поиск и фильтрация фильмов")
def list_movies(
    q: Optional[str] = Query(None, description="Поисковый запрос (по названию, слогану или описанию)"),
    genre: Optional[str] = Query(None, description="Название или слаг жанра (например: фантастика, драма)"),
    year_from: Optional[int] = Query(None, ge=1895, le=2035, description="Минимальный год выпуска"),
    year_to: Optional[int] = Query(None, ge=1895, le=2035, description="Максимальный год выпуска"),
    rating_min: Optional[float] = Query(None, ge=0.0, le=10.0, description="Минимальный рейтинг Кинопоиска"),
    rating_max: Optional[float] = Query(None, ge=0.0, le=10.0, description="Максимальный рейтинг Кинопоиска"),
    award: Optional[str] = Query(None, description="Название награды (например: Оскар, Золотой глобус, Сатурн)"),
    has_awards: Optional[bool] = Query(None, description="Только фильмы, имеющие награды"),
    actor: Optional[str] = Query(None, description="Имя актера"),
    director: Optional[str] = Query(None, description="Имя режиссера"),
    country: Optional[str] = Query(None, description="Страна производства"),
    sort_by: str = Query("rating_desc", pattern="^(rating_desc|rating_asc|year_desc|year_asc|title_asc|title_desc)$", description="Сортировка"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(12, ge=1, le=100, description="Количество фильмов на странице"),
    db: Session = Depends(get_db)
):
    """
    Продвинутая фильтрация и поиск фильмов:
    - Полнотекстовый поиск по названию, слогану и описанию
    - Фильтрация по жанрам, диапазону годов (year_from, year_to)
    - Фильтрация по рейтингу (rating_min, rating_max)
    - Фильтрация по наградам (Оскар, Сатурн и др.) или наличию наград
    - Фильтрация по актерам и режиссерам
    - Пагинация и сортировки
    """
    query = db.query(Movie).distinct()

    # Search query
    if q:
        search_pattern = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Movie.title).like(search_pattern),
                func.lower(Movie.original_title).like(search_pattern),
                func.lower(Movie.slogan).like(search_pattern),
                func.lower(Movie.description).like(search_pattern)
            )
        )

    # Genre filter
    if genre:
        g_clean = genre.strip().lower()
        query = query.join(Movie.genres).filter(
            or_(
                func.lower(Genre.name).like(f"%{g_clean}%"),
                Genre.slug == g_clean
            )
        )

    # Year range
    if year_from:
        query = query.filter(Movie.year >= year_from)
    if year_to:
        query = query.filter(Movie.year <= year_to)

    # Rating range
    if rating_min is not None:
        query = query.filter(Movie.rating_kp >= rating_min)
    if rating_max is not None:
        query = query.filter(Movie.rating_kp <= rating_max)

    # Award filter
    if award:
        aw_clean = award.strip().lower()
        query = query.join(Movie.awards).filter(func.lower(Award.name).like(f"%{aw_clean}%"))
    elif has_awards:
        query = query.join(Movie.awards)

    # Actor filter
    if actor:
        act_clean = actor.strip().lower()
        query = query.join(Movie.actors).filter(func.lower(Actor.name).like(f"%{act_clean}%"))

    # Director filter
    if director:
        dir_clean = director.strip().lower()
        query = query.join(Movie.directors).filter(func.lower(Director.name).like(f"%{dir_clean}%"))

    # Country
    if country:
        cntry_clean = country.strip().lower()
        query = query.filter(func.lower(Movie.country).like(f"%{cntry_clean}%"))

    # Count total
    total = query.count()

    # Sorting
    if sort_by == "rating_desc":
        query = query.order_by(desc(Movie.rating_kp), desc(Movie.year))
    elif sort_by == "rating_asc":
        query = query.order_by(asc(Movie.rating_kp), asc(Movie.year))
    elif sort_by == "year_desc":
        query = query.order_by(desc(Movie.year), desc(Movie.rating_kp))
    elif sort_by == "year_asc":
        query = query.order_by(asc(Movie.year), desc(Movie.rating_kp))
    elif sort_by == "title_asc":
        query = query.order_by(asc(Movie.title))
    elif sort_by == "title_desc":
        query = query.order_by(desc(Movie.title))

    # Pagination
    offset = (page - 1) * page_size
    movies = query.offset(offset).limit(page_size).all()

    items = [_movie_to_list_item(m) for m in movies]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedMoviesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/random", response_model=RandomMovieResponse, summary="Рандомайзер: «Случайный фильм на вечер»")
def get_random_movie(
    mood: Optional[str] = Query(None, description="Настроение: epic, drama, mindfuck, uplifting, chill"),
    genre: Optional[str] = Query(None, description="Предпочтительный жанр"),
    min_rating: Optional[float] = Query(7.5, ge=0.0, le=10.0, description="Минимальный рейтинг"),
    year_from: Optional[int] = Query(None, ge=1900, description="Не старше года"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Классная фича: Умный рандомайзер фильмов на вечер!
    Подбирает идеальный фильм по настроению, минимальному рейтингу и жанру,
    генерируя персональную причину для вечернего просмотра.
    """
    query = db.query(Movie)

    if min_rating:
        query = query.filter(Movie.rating_kp >= min_rating)
    if year_from:
        query = query.filter(Movie.year >= year_from)

    # Mood mappings
    mood_reasons = {
        "epic": "Масштабная история, захватывающий дух визуал и эпический размах для полного погружения!",
        "drama": "Глубокая эмоциональная драма, которая заставит задуматься и тронет до глубины души.",
        "mindfuck": "Интеллектуальная головоломка с непредсказуемыми поворотами сюжета — скучать точно не придется!",
        "uplifting": "Вдохновляющая и светлая картина, которая наполнит вечер надеждой и теплом.",
        "chill": "Идеальное кино для расслабления и приятного вечера после тяжелого дня."
    }

    if mood:
        mood_clean = mood.lower().strip()
        if mood_clean in ["epic", "эпик"]:
            query = query.join(Movie.genres).filter(
                or_(func.lower(Genre.name).like("%фантастика%"), func.lower(Genre.name).like("%приключения%"))
            )
        elif mood_clean in ["drama", "драма"]:
            query = query.join(Movie.genres).filter(func.lower(Genre.name).like("%драма%"))
        elif mood_clean in ["mindfuck", "загадка", "головоломка"]:
            query = query.join(Movie.genres).filter(
                or_(func.lower(Genre.name).like("%триллер%"), func.lower(Genre.name).like("%детектив%"), func.lower(Genre.name).like("%фантастика%"))
            )
        elif mood_clean in ["uplifting", "вдохновение"]:
            query = query.join(Movie.genres).filter(
                or_(func.lower(Genre.name).like("%комедия%"), func.lower(Genre.name).like("%биография%"), func.lower(Genre.name).like("%приключения%"))
            )

    if genre:
        query = query.join(Movie.genres).filter(func.lower(Genre.name).like(f"%{genre.strip().lower()}%"))

    candidates = query.distinct().all()

    if not candidates:
        # Fallback to any high-rated movie
        candidates = db.query(Movie).filter(Movie.rating_kp >= 7.0).all()
        if not candidates:
            candidates = db.query(Movie).all()

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="В базе данных пока нет подходящих фильмов для рекомендации"
        )

    chosen = random.choice(candidates)
    reason = mood_reasons.get(mood.lower(), f"Топ-рейтинг Кинопоиска {chosen.rating_kp} и признание миллионов зрителей!") if mood else f"Высокий рейтинг {chosen.rating_kp}, мощный сюжет и идеальный хронометраж для сегодняшнего вечера!"

    movie_detail = _movie_to_detail(chosen, current_user, db)
    return RandomMovieResponse(
        movie=movie_detail,
        reason=reason,
        match_mood=mood
    )


@router.get("/{movie_id}", response_model=MovieDetailResponse, summary="Детальная информация о фильме")
def get_movie_detail(
    movie_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Возвращает исчерпывающую информацию о фильме:
    - Все постеры и кадры галереи
    - Список актеров с ID Кинопоиска
    - Режиссеры и полученные награды (Оскар, Сатурн и др.)
    - Трейлеры и ссылки на онлайн-просмотр (Кинопоиск, Rutube, VK)
    - Пользовательские отзывы и средний балл
    - Персональные статусы: в избранном ли фильм у текущего пользователя и есть ли в истории
    """
    # Accept internal id or kp_id
    movie = None
    if movie_id.isdigit():
        movie = db.query(Movie).filter(
            or_(Movie.id == int(movie_id), Movie.kp_id == movie_id)
        ).first()
    else:
        movie = db.query(Movie).filter(Movie.kp_id == movie_id).first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Фильм с идентификатором '{movie_id}' не найден"
        )

    return _movie_to_detail(movie, current_user, db)
