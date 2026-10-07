"""
Automated pytest tests for Metadata & Statistics:
- GET /api/genres
- GET /api/actors (Search & Limit)
- GET /api/directors (Search & Limit)
- GET /api/awards
- GET /api/stats
"""
import pytest


class TestMetadataEndpoints:
    def test_get_genres(self, client):
        """Test retrieving all genres with movie counts."""
        res = client.get("/api/genres")
        assert res.status_code == 200
        genres = res.json()
        assert len(genres) >= 3
        genre_names = [g["name"] for g in genres]
        assert "фантастика" in genre_names
        assert "драма" in genre_names

        # Check structure
        g0 = genres[0]
        assert "id" in g0
        assert "name" in g0
        assert "slug" in g0
        assert "movies_count" in g0
        assert g0["movies_count"] >= 0

    def test_get_actors(self, client):
        """Test retrieving actors with search query."""
        # 1. All actors
        res = client.get("/api/actors")
        assert res.status_code == 200
        actors = res.json()
        assert len(actors) >= 3

        # 2. Search actor
        res_search = client.get("/api/actors?q=Хэнкс")
        assert res_search.status_code == 200
        results = res_search.json()
        assert len(results) == 1
        assert "Хэнкс" in results[0]["name"]

    def test_get_directors(self, client):
        """Test retrieving directors with search query."""
        res = client.get("/api/directors?q=Нолан")
        assert res.status_code == 200
        results = res.json()
        assert len(results) == 1
        assert "Нолан" in results[0]["name"]

    def test_get_awards(self, client):
        """Test retrieving unique award categories."""
        res = client.get("/api/awards")
        assert res.status_code == 200
        awards = res.json()
        assert isinstance(awards, list)
        assert "Оскар" in awards
        assert "Сатурн" in awards

    def test_get_catalog_stats(self, client):
        """Test catalog analytics stats endpoint."""
        res = client.get("/api/stats")
        assert res.status_code == 200
        stats = res.json()
        assert stats["total_movies"] == 3
        assert stats["total_actors"] >= 3
        assert stats["total_directors"] >= 2
        assert stats["total_genres"] >= 3
        assert stats["total_awards"] >= 2
        assert stats["total_users"] >= 2
        assert stats["total_reviews"] >= 1
        assert stats["avg_rating"] > 0
