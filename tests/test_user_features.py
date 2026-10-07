"""
Automated pytest tests for User Features:
- Favorites System (Add, List, Check, Remove)
- Watch History System (Record Progress, List, Delete Item, Clear All)
"""
import pytest


class TestFavoritesSystem:
    def test_favorites_unauthorized_fails(self, client):
        """Test favorites endpoints return 401 without authentication."""
        assert client.get("/api/favorites").status_code == 401
        assert client.post("/api/favorites/1").status_code == 401
        assert client.delete("/api/favorites/1").status_code == 401

    def test_add_and_list_favorites(self, client, auth_headers):
        """Test adding movie to favorites and retrieving list."""
        res_movies = client.get("/api/movies/258687")
        movie_id = res_movies.json()["id"]

        # 1. Add to favorites
        res_add = client.post(f"/api/favorites/{movie_id}", headers=auth_headers)
        assert res_add.status_code == 201
        assert res_add.json()["is_favorite"] is True

        # 2. Check status endpoint
        res_check = client.get(f"/api/favorites/check/{movie_id}", headers=auth_headers)
        assert res_check.status_code == 200
        assert res_check.json()["is_favorite"] is True

        # 3. List favorites
        res_list = client.get("/api/favorites", headers=auth_headers)
        assert res_list.status_code == 200
        favs = res_list.json()
        assert len(favs) == 1
        assert favs[0]["movie_id"] == movie_id
        assert favs[0]["movie"]["title"] == "Интерстеллар"

    def test_remove_from_favorites(self, client, auth_headers):
        """Test removing movie from favorites."""
        res_movies = client.get("/api/movies/258687")
        movie_id = res_movies.json()["id"]

        # Add first
        client.post(f"/api/favorites/{movie_id}", headers=auth_headers)

        # Remove
        res_del = client.delete(f"/api/favorites/{movie_id}", headers=auth_headers)
        assert res_del.status_code == 200
        assert res_del.json()["is_favorite"] is False

        # Verify list is empty
        res_list = client.get("/api/favorites", headers=auth_headers)
        assert len(res_list.json()) == 0

    def test_add_nonexistent_movie_to_favorites(self, client, auth_headers):
        """Test adding non-existent movie to favorites returns 404."""
        res = client.post("/api/favorites/999999", headers=auth_headers)
        assert res.status_code == 404


class TestWatchHistorySystem:
    def test_history_unauthorized_fails(self, client):
        """Test history endpoints return 401 without authentication."""
        assert client.get("/api/history").status_code == 401
        assert client.post("/api/history/1", json={"progress_seconds": 120}).status_code == 401

    def test_record_watch_history_and_list(self, client, auth_headers):
        """Test recording viewing progress and retrieving history."""
        res_movies = client.get("/api/movies/326")
        movie_id = res_movies.json()["id"]

        # Record progress: 3600 seconds (1 hour)
        payload = {"progress_seconds": 3600, "is_completed": False}
        res_record = client.post(f"/api/history/{movie_id}", json=payload, headers=auth_headers)
        assert res_record.status_code == 200
        assert res_record.json()["progress_seconds"] == 3600

        # Retrieve history
        res_history = client.get("/api/history", headers=auth_headers)
        assert res_history.status_code == 200
        items = res_history.json()
        assert len(items) == 1
        assert items[0]["movie_id"] == movie_id
        assert items[0]["progress_seconds"] == 3600
        assert items[0]["movie"]["title"] == "Побег из Шоушенка"

    def test_delete_history_item(self, client, auth_headers):
        """Test deleting a single item from watch history."""
        res_movies = client.get("/api/movies/326")
        movie_id = res_movies.json()["id"]

        client.post(f"/api/history/{movie_id}", json={"progress_seconds": 500}, headers=auth_headers)
        res_del = client.delete(f"/api/history/{movie_id}", headers=auth_headers)
        assert res_del.status_code == 200

        # Verify history is now empty
        res_history = client.get("/api/history", headers=auth_headers)
        assert len(res_history.json()) == 0

    def test_clear_all_history(self, client, auth_headers):
        """Test clearing entire watch history."""
        res_movies = client.get("/api/movies")
        for m in res_movies.json()["items"]:
            client.post(f"/api/history/{m['id']}", json={"progress_seconds": 100}, headers=auth_headers)

        res_clear = client.delete("/api/history", headers=auth_headers)
        assert res_clear.status_code == 200

        res_history = client.get("/api/history", headers=auth_headers)
        assert len(res_history.json()) == 0
