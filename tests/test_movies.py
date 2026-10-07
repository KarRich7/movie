"""
Automated pytest tests for Movie Catalog, Search, Filtering, Detail, and Randomizer:
- GET / and GET /health
- GET /api/movies (Pagination, Query Search, Genre, Year, Rating, Awards, Actors, Directors)
- GET /api/movies/{id} (by DB ID and KP ID)
- GET /api/movies/random (Mood, genre, rating filtering, reasons)
"""
import pytest


class TestRootAndHealth:
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information and documentation links."""
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert "endpoints" in data
        assert data["endpoints"]["movies"] == "/api/movies"

    def test_health_endpoint(self, client):
        """Test health endpoint returns healthy status."""
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "healthy"}


class TestMoviesListingAndFilters:
    def test_list_movies_all(self, client):
        """Test listing all movies with default pagination."""
        res = client.get("/api/movies")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["total_pages"] == 1

        # Check required item fields
        item = data["items"][0]
        assert "id" in item
        assert "title" in item
        assert "year" in item
        assert "rating_kp" in item
        assert "genres" in item
        assert "directors" in item

    def test_search_query_by_title(self, client):
        """Test full-text search by title."""
        res = client.get("/api/movies", params={"q": "Интерстеллар"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Интерстеллар"

    def test_search_query_by_original_title(self, client):
        """Test search by original title in English."""
        res = client.get("/api/movies", params={"q": "Shawshank"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["original_title"] == "The Shawshank Redemption"

    def test_search_query_by_slogan(self, client):
        """Test search by movie slogan."""
        res = client.get("/api/movies", params={"q": "кандалы"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Побег из Шоушенка"

    def test_filter_by_genre_name(self, client):
        """Test filtering movies by genre name."""
        res = client.get("/api/movies", params={"genre": "фантастика"})
        assert res.status_code == 200
        items = res.json()["items"]
        # Интерстеллар & Зеленая миля both have sci-fi
        assert len(items) == 2
        titles = [m["title"] for m in items]
        assert "Интерстеллар" in titles
        assert "Зеленая миля" in titles

    def test_filter_by_year_range(self, client):
        """Test filtering by year range."""
        res = client.get("/api/movies", params={"year_from": 1990, "year_to": 2000})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        for m in items:
            assert 1990 <= m["year"] <= 2000

    def test_filter_by_rating_min(self, client):
        """Test filtering by minimum rating."""
        res = client.get("/api/movies", params={"rating_min": 9.0})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2  # Shawshank (9.1) & Green Mile (9.1)
        for m in items:
            assert m["rating_kp"] >= 9.0

    def test_filter_by_awards_name(self, client):
        """Test filtering by award name (e.g. Оскар)."""
        res = client.get("/api/movies", params={"award": "Оскар"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Интерстеллар"

    def test_filter_by_has_awards(self, client):
        """Test filtering by has_awards=true."""
        res = client.get("/api/movies", params={"has_awards": "true"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["awards_count"] > 0

    def test_filter_by_actor(self, client):
        """Test filtering by actor name."""
        res = client.get("/api/movies", params={"actor": "Макконахи"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Интерстеллар"

    def test_filter_by_director(self, client):
        """Test filtering by director name."""
        res = client.get("/api/movies", params={"director": "Дарабонт"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2  # Shawshank & Green Mile
        titles = [m["title"] for m in items]
        assert "Побег из Шоушенка" in titles
        assert "Зеленая миля" in titles

    def test_sorting_by_year_desc(self, client):
        """Test sorting movies by year descending."""
        res = client.get("/api/movies", params={"sort_by": "year_desc"})
        assert res.status_code == 200
        items = res.json()["items"]
        years = [m["year"] for m in items]
        assert years == sorted(years, reverse=True)

    def test_sorting_by_title_asc(self, client):
        """Test sorting movies by title ascending."""
        res = client.get("/api/movies", params={"sort_by": "title_asc"})
        assert res.status_code == 200
        items = res.json()["items"]
        titles = [m["title"] for m in items]
        assert titles == sorted(titles)

    def test_pagination_page_size(self, client):
        """Test pagination limit with page_size=2."""
        res = client.get("/api/movies", params={"page": 1, "page_size": 2})
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["total_pages"] == 2


class TestMovieDetail:
    def test_get_movie_detail_by_id(self, client):
        """Test retrieving detailed movie info by internal database ID."""
        res_list = client.get("/api/movies")
        movie_id = res_list.json()["items"][0]["id"]

        res = client.get(f"/api/movies/{movie_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == movie_id
        assert "genres" in data and isinstance(data["genres"], list)
        assert "actors" in data and isinstance(data["actors"], list)
        assert "directors" in data and isinstance(data["directors"], list)
        assert "awards" in data and isinstance(data["awards"], list)
        assert "reviews" in data and isinstance(data["reviews"], list)
        assert "is_favorite" in data
        assert "in_watch_history" in data

    def test_get_movie_detail_by_kp_id(self, client):
        """Test retrieving movie detail by Kinopoisk ID string (e.g., '258687')."""
        res = client.get("/api/movies/258687")
        assert res.status_code == 200
        data = res.json()
        assert data["kp_id"] == "258687"
        assert data["title"] == "Интерстеллар"

    def test_get_movie_detail_not_found(self, client):
        """Test retrieving non-existent movie returns 404."""
        res = client.get("/api/movies/99999999")
        assert res.status_code == 404
        assert "не найден" in res.json()["detail"]


class TestMovieRandomizer:
    def test_random_movie_default(self, client):
        """Test random movie endpoint returns a valid movie and reason."""
        res = client.get("/api/movies/random")
        assert res.status_code == 200
        data = res.json()
        assert "movie" in data
        assert "title" in data["movie"]
        assert "reason" in data
        assert len(data["reason"]) > 5

    def test_random_movie_with_epic_mood(self, client):
        """Test random movie with mood='epic' selects sci-fi/adventure."""
        res = client.get("/api/movies/random", params={"mood": "epic"})
        assert res.status_code == 200
        data = res.json()
        assert data["match_mood"] == "epic"
        genre_names = [g["name"] for g in data["movie"]["genres"]]
        assert any(g in ["фантастика", "приключения"] for g in genre_names)

    def test_random_movie_with_drama_mood(self, client):
        """Test random movie with mood='drama' selects drama genre."""
        res = client.get("/api/movies/random", params={"mood": "drama"})
        assert res.status_code == 200
        data = res.json()
        genre_names = [g["name"] for g in data["movie"]["genres"]]
        assert "драма" in genre_names
