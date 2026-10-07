"""
Automated pytest tests for Reviews System:
- GET /api/movies/{movie_id}/reviews
- POST /api/movies/{movie_id}/reviews (Protected creation & updating)
- DELETE /api/reviews/{review_id} (Protected deletion with owner & admin permissions)
"""
import pytest


class TestReviewsListing:
    def test_get_movie_reviews_success(self, client):
        """Test getting reviews list for a movie."""
        res_movies = client.get("/api/movies/258687")
        movie_id = res_movies.json()["id"]

        res = client.get(f"/api/movies/{movie_id}/reviews")
        assert res.status_code == 200
        reviews = res.json()
        assert isinstance(reviews, list)
        assert len(reviews) >= 1
        r = reviews[0]
        assert "user_username" in r
        assert "rating" in r
        assert "content" in r

    def test_get_movie_reviews_nonexistent_movie(self, client):
        """Test getting reviews for non-existent movie returns 404."""
        res = client.get("/api/movies/999999/reviews")
        assert res.status_code == 404


class TestReviewsSubmission:
    def test_create_review_unauthorized_fails(self, client):
        """Test creating review without token fails with 401."""
        res_movies = client.get("/api/movies")
        movie_id = res_movies.json()["items"][0]["id"]

        payload = {
            "rating": 9,
            "title": "Отличный фильм",
            "content": "Очень понравился сюжет и игра актеров."
        }
        res = client.post(f"/api/movies/{movie_id}/reviews", json=payload)
        assert res.status_code == 401

    def test_create_review_authorized_success(self, client, auth_headers):
        """Test creating a review as authenticated user."""
        res_movies = client.get("/api/movies", params={"q": "Shawshank"})
        movie_id = res_movies.json()["items"][0]["id"]

        payload = {
            "rating": 10,
            "title": "Абсолютная классика",
            "content": "Один из лучших фильмов за всю историю человечества."
        }
        res = client.post(f"/api/movies/{movie_id}/reviews", json=payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["rating"] == 10
        assert data["title"] == "Абсолютная классика"
        assert data["user_username"] == "demo_user"

        # Verify it now appears in movie's reviews list
        res_reviews = client.get(f"/api/movies/{movie_id}/reviews")
        assert res_reviews.status_code == 200
        assert any(r["title"] == "Абсолютная классика" for r in res_reviews.json())

    def test_create_review_invalid_rating(self, client, auth_headers):
        """Test validation: rating must be between 1 and 10."""
        res_movies = client.get("/api/movies")
        movie_id = res_movies.json()["items"][0]["id"]

        # Rating 11 is invalid
        res = client.post(
            f"/api/movies/{movie_id}/reviews",
            json={"rating": 11, "content": "Слишком высокая оценка"},
            headers=auth_headers
        )
        assert res.status_code == 422

        # Rating 0 is invalid
        res = client.post(
            f"/api/movies/{movie_id}/reviews",
            json={"rating": 0, "content": "Слишком низкая оценка"},
            headers=auth_headers
        )
        assert res.status_code == 422

    def test_create_review_short_content(self, client, auth_headers):
        """Test validation: content must be at least 5 characters."""
        res_movies = client.get("/api/movies")
        movie_id = res_movies.json()["items"][0]["id"]

        res = client.post(
            f"/api/movies/{movie_id}/reviews",
            json={"rating": 8, "content": "Ок"},
            headers=auth_headers
        )
        assert res.status_code == 422

    def test_update_existing_review_by_same_user(self, client, auth_headers):
        """Test submitting a review for a movie already reviewed updates the existing review."""
        res_movies = client.get("/api/movies", params={"q": "Interstellar"})
        movie_id = res_movies.json()["items"][0]["id"]

        # demo_user already has a review in fixture for Interstellar; update it:
        update_payload = {
            "rating": 9,
            "title": "Обновленный отзыв: 9 из 10",
            "content": "Пересмотрел фильм спустя годы. Все еще великолепен, но финал немного наивный."
        }
        res = client.post(f"/api/movies/{movie_id}/reviews", json=update_payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["rating"] == 9
        assert data["title"] == "Обновленный отзыв: 9 из 10"


class TestReviewsDeletion:
    def test_delete_review_unauthorized_fails(self, client):
        """Test deleting review without token fails with 401."""
        res = client.delete("/api/reviews/1")
        assert res.status_code == 401

    def test_delete_review_non_owner_forbidden(self, client, admin_headers, auth_headers):
        """Test non-owner regular user cannot delete someone else's review."""
        # 1. Admin creates a review for movie 3 (Green Mile)
        res_movies = client.get("/api/movies/435")
        movie_id = res_movies.json()["id"]

        res_create = client.post(
            f"/api/movies/{movie_id}/reviews",
            json={"rating": 10, "title": "Отзыв админа", "content": "Сильное эмоциональное кино."},
            headers=admin_headers
        )
        admin_review_id = res_create.json()["id"]

        # 2. Regular demo_user tries to delete admin's review
        res_del = client.delete(f"/api/reviews/{admin_review_id}", headers=auth_headers)
        assert res_del.status_code == 403
        assert len(res_del.json().get("detail", "")) > 0

    def test_delete_review_by_owner_success(self, client, auth_headers):
        """Test owner can delete their own review."""
        res_movies = client.get("/api/movies/258687")
        movie_id = res_movies.json()["id"]

        res_reviews = client.get(f"/api/movies/{movie_id}/reviews")
        review_id = res_reviews.json()[0]["id"]

        # Delete by owner
        res_del = client.delete(f"/api/reviews/{review_id}", headers=auth_headers)
        assert res_del.status_code == 204

    def test_delete_review_by_admin_success(self, client, auth_headers, admin_headers):
        """Test administrator can delete any user's review."""
        # Create a review as demo_user
        res_movies = client.get("/api/movies/435")
        movie_id = res_movies.json()["id"]

        res_create = client.post(
            f"/api/movies/{movie_id}/reviews",
            json={"rating": 8, "content": "Очень трогательная история."},
            headers=auth_headers
        )
        review_id = res_create.json()["id"]

        # Admin deletes the review
        res_del = client.delete(f"/api/reviews/{review_id}", headers=admin_headers)
        assert res_del.status_code == 204
