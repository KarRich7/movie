"""
Reviews router: protected submission, viewing, updating, and deletion of reviews.
"""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Review, Movie, User
from backend.schemas import ReviewCreateRequest, ReviewResponse
from backend.security import get_current_user

router = APIRouter(prefix="/api", tags=["Отзывы и рецензии"])


@router.get("/movies/{movie_id}/reviews", response_model=List[ReviewResponse], summary="Список отзывов к фильму")
def get_movie_reviews(movie_id: int, db: Session = Depends(get_db)):
    """Возвращает все отзывы к фильму, отсортированные по дате добавления."""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Фильм #{movie_id} не найден"
        )
    
    reviews = db.query(Review).filter(Review.movie_id == movie_id).order_by(Review.created_at.desc()).all()
    return [
        ReviewResponse(
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
        ) for r in reviews
    ]


@router.post("/movies/{movie_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED, summary="Защищенная публикация отзыва к фильму")
def create_or_update_movie_review(
    movie_id: int,
    req: ReviewCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Защищенный эндпоинт отправки отзыва (требует JWT Bearer токен).
    Пользователь ставит оценку от 1 до 10 и пишет текст отзыва.
    Если пользователь уже оставлял отзыв к этому фильму, его отзыв обновляется.
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Фильм #{movie_id} не найден"
        )

    # Check for existing review by this user
    existing_review = db.query(Review).filter(
        Review.movie_id == movie_id,
        Review.user_id == current_user.id
    ).first()

    if existing_review:
        existing_review.rating = req.rating
        existing_review.title = req.title
        existing_review.content = req.content
        existing_review.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_review)
        review = existing_review
    else:
        review = Review(
            movie_id=movie_id,
            user_id=current_user.id,
            rating=req.rating,
            title=req.title,
            content=req.content
        )
        db.add(review)
        db.commit()
        db.refresh(review)

    return ReviewResponse(
        id=review.id,
        movie_id=review.movie_id,
        user_id=review.user_id,
        user_username=current_user.username,
        user_avatar=current_user.avatar_url,
        rating=review.rating,
        title=review.title,
        content=review.content,
        created_at=review.created_at,
        updated_at=review.updated_at
    )


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удаление отзыва")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удаляет отзыв. Доступно только автору отзыва или администратору.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Отзыв #{review_id} не найден"
        )

    if review.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете удалять только собственные отзывы"
        )

    db.delete(review)
    db.commit()
    return None
