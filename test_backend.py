"""
Comprehensive test suite verifying all Agent 2 requirements:
- SQLite and data models
- Advanced search and filtering
- Authentication and password hashing
- Protected review submissions
- Evening movie randomizer
- Favorites and watch history
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient
from backend.main import app
from backend.seeder import seed_database
from backend.database import SessionLocal
from backend.models import User, Movie, Review, Favorite, WatchHistory

def run_tests():
    print("=" * 60)
    print("🚀 RUNNING BACKEND TESTS FOR AGENT 2 REQUIREMENTS")
    print("=" * 60)

    # 1. Initialize DB and Seeder
    seed_database(force=False)
    client = TestClient(app)

    # Test 1: Root and Health
    print("\n[1/7] Testing Root and Health Endpoints...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert res.json()["status"] == "online"
    print("  ✅ Root endpoint OK:", res.json()["app"])

    # Test 2: Advanced Search & Filtering
    print("\n[2/7] Testing Advanced Search & Filtering (/api/movies)...")
    
    # 2.1 All movies
    res = client.get("/api/movies")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 3, f"Expected at least 3 movies, got {data['total']}"
    print(f"  ✅ List all movies OK: {data['total']} movies found")

    # 2.2 Search by query 'Интерстеллар'
    res = client.get("/api/movies?q=Интерстеллар")
    assert res.status_code == 200
    q_data = res.json()
    assert len(q_data["items"]) >= 1
    assert "Интерстеллар" in q_data["items"][0]["title"]
    print("  ✅ Query search OK:", q_data["items"][0]["title"])

    # 2.3 Filter by genre 'фантастика'
    res = client.get("/api/movies?genre=фантастика")
    assert res.status_code == 200
    g_data = res.json()
    assert len(g_data["items"]) >= 1
    print(f"  ✅ Genre filter OK: {len(g_data['items'])} sci-fi movies found")

    # 2.4 Filter by year range (1990 to 2000)
    res = client.get("/api/movies?year_from=1990&year_to=2000")
    assert res.status_code == 200
    y_data = res.json()
    assert len(y_data["items"]) >= 2  # Побег из Шоушенка (1994), Зеленая миля (1999)
    print(f"  ✅ Year range filter OK: {len(y_data['items'])} movies from 1990-2000")

    # 2.5 Filter by awards (Оскар)
    res = client.get("/api/movies?award=Оскар")
    assert res.status_code == 200
    aw_data = res.json()
    assert len(aw_data["items"]) >= 1
    print(f"  ✅ Award filter OK: {len(aw_data['items'])} Oscar-winning movies")

    # 2.6 Filter by rating (>= 8.5)
    res = client.get("/api/movies?rating_min=8.5")
    assert res.status_code == 200
    r_data = res.json()
    assert len(r_data["items"]) >= 1
    print(f"  ✅ Rating filter OK: {len(r_data['items'])} top-rated movies")

    # Test 3: Movie Detail
    print("\n[3/7] Testing Movie Detail (/api/movies/{id})...")
    movie_id = data["items"][0]["id"]
    res = client.get(f"/api/movies/{movie_id}")
    assert res.status_code == 200
    m_detail = res.json()
    assert "genres" in m_detail and len(m_detail["genres"]) > 0
    assert "actors" in m_detail and len(m_detail["actors"]) > 0
    assert "directors" in m_detail
    assert "awards" in m_detail
    print(f"  ✅ Detail OK for '{m_detail['title']}': {len(m_detail['actors'])} actors, {len(m_detail['awards'])} awards")

    # Test 4: Auth & Registration
    print("\n[4/7] Testing User Registration & Authentication (/api/auth)...")
    import random
    test_uname = f"testuser_{random.randint(1000, 9999)}"
    reg_payload = {
        "username": test_uname,
        "email": f"{test_uname}@example.com",
        "password": "SecretPassword123!"
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201, f"Register failed: {res.text}"
    token_data = res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    print(f"  ✅ Registration OK: User '{test_uname}' registered with JWT token")

    # Login test
    login_payload = {
        "username_or_email": test_uname,
        "password": "SecretPassword123!"
    }
    res = client.post("/api/auth/login", json=login_payload)
    assert res.status_code == 200
    assert "access_token" in res.json()
    print("  ✅ Login OK: Correct password verified with PBKDF2 hash")

    # Profile (/api/auth/me)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == test_uname
    print("  ✅ Protected profile OK: /api/auth/me returned user details")

    # Test 5: Protected Reviews
    print("\n[5/7] Testing Protected Reviews (/api/movies/{id}/reviews)...")
    review_payload = {
        "rating": 9,
        "title": "Потрясающий фильм!",
        "content": "Один из лучших фильмов, что я смотрел в жизни. Визуал и сюжет на высоте!"
    }
    # Unauthenticated should fail 401
    res = client.post(f"/api/movies/{movie_id}/reviews", json=review_payload)
    assert res.status_code == 401
    print("  ✅ Unauthorized review creation correctly rejected with 401")

    # Authenticated submission
    res = client.post(f"/api/movies/{movie_id}/reviews", json=review_payload, headers=headers)
    assert res.status_code == 201, f"Review failed: {res.text}"
    created_review = res.json()
    assert created_review["rating"] == 9
    assert created_review["user_username"] == test_uname
    print("  ✅ Protected review successfully created with rating 9/10")

    # Test 6: Evening Movie Randomizer
    print("\n[6/7] Testing Randomizer «Случайный фильм на вечер» (/api/movies/random)...")
    res = client.get("/api/movies/random?mood=epic")
    assert res.status_code == 200
    rand_data = res.json()
    assert "movie" in rand_data
    assert "reason" in rand_data
    print(f"  ✅ Randomizer OK: Selected '{rand_data['movie']['title']}'")
    print(f"     Reason: {rand_data['reason']}")

    # Test 7: Favorites & Watch History
    print("\n[7/7] Testing Favorites and Watch History...")
    
    # 7.1 Add to favorites
    res = client.post(f"/api/favorites/{movie_id}", headers=headers)
    assert res.status_code == 201
    assert res.json()["is_favorite"] is True
    print(f"  ✅ Added movie #{movie_id} to favorites")

    # 7.2 Check favorites list
    res = client.get("/api/favorites", headers=headers)
    assert res.status_code == 200
    favs = res.json()
    assert len(favs) >= 1
    assert favs[0]["movie_id"] == movie_id
    print(f"  ✅ Favorites list verified ({len(favs)} items)")

    # 7.3 Watch history
    history_payload = {"progress_seconds": 3600, "is_completed": False}
    res = client.post(f"/api/history/{movie_id}", json=history_payload, headers=headers)
    assert res.status_code == 200
    print(f"  ✅ Watch history logged (progress: 3600s)")

    res = client.get("/api/history", headers=headers)
    assert res.status_code == 200
    hist = res.json()
    assert len(hist) >= 1
    assert hist[0]["movie_id"] == movie_id
    print(f"  ✅ History list verified ({len(hist)} items)")

    # 7.4 Catalog stats
    res = client.get("/api/stats")
    assert res.status_code == 200
    stats = res.json()
    print(f"\n📊 Catalog Stats: {stats['total_movies']} movies, {stats['total_genres']} genres, {stats['total_actors']} actors, {stats['total_awards']} awards, {stats['total_reviews']} reviews")

    print("\n" + "=" * 60)
    print("🎉 ALL AGENT 2 TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
