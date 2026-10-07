"""
Pytest configuration and shared fixtures for Movie Catalog API tests.
Uses an in-memory SQLite database with StaticPool to ensure persistence across threads in TestClient.
"""
import pytest
import os
import json
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models import User, Movie, Genre, Actor, Director, Award, Review, Favorite, WatchHistory
from backend.security import hash_password, create_access_token

# Test SQLite in-memory database with StaticPool for thread-safe test isolation
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
    dbapi_connection.create_function("lower", 1, lambda s: s.lower() if s is not None else None)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def init_db():
    """Initializes tables in the in-memory database once per test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh, clean database state for each test function."""
    session = TestingSessionLocal()

    # Clear all existing tables before test
    session.query(WatchHistory).delete()
    session.query(Favorite).delete()
    session.query(Review).delete()
    session.query(Award).delete()
    session.execute(Base.metadata.tables["movie_genres"].delete())
    session.execute(Base.metadata.tables["movie_actors"].delete())
    session.execute(Base.metadata.tables["movie_directors"].delete())
    session.query(Movie).delete()
    session.query(Actor).delete()
    session.query(Director).delete()
    session.query(Genre).delete()
    session.query(User).delete()
    session.commit()

    # 1. Genres
    g_sci_fi = Genre(name="фантастика", slug="fantastika")
    g_drama = Genre(name="драма", slug="drama")
    g_adventure = Genre(name="приключения", slug="priklyucheniya")
    session.add_all([g_sci_fi, g_drama, g_adventure])

    # 2. Actors & Directors
    actor1 = Actor(name="Мэттью Макконахи", kp_id="7987")
    actor2 = Actor(name="Тим Роббинс", kp_id="7836")
    actor3 = Actor(name="Том Хэнкс", kp_id="9144")
    director1 = Director(name="Кристофер Нолан", kp_id="41477")
    director2 = Director(name="Фрэнк Дарабонт", kp_id="24262")
    session.add_all([actor1, actor2, actor3, director1, director2])
    session.commit()

    # 3. Movies
    movie1 = Movie(
        kp_id="258687",
        title="Интерстеллар",
        original_title="Interstellar",
        year=2014,
        slogan="Следующий шаг человечества станет величайшим",
        description="Когда засуха, пыльные бури и вымирание растений приводят человечество к продовольственному кризису...",
        poster="https://avatars.mds.yandex.net/get-kinopoisk-image/1600647/430042eb-ee69-4818-aed0-a312400a26bf/orig",
        posters_json=json.dumps(["https://avatars.mds.yandex.net/get-kinopoisk-image/1600647/430042eb-ee69-4818-aed0-a312400a26bf/orig"]),
        duration="169 мин. / 02:49",
        duration_minutes=169,
        age="18+",
        country="США, Великобритания",
        budget="$165 000 000",
        boxoffice="$773 874 412",
        rating_kp=8.6,
        rating_site=8.6,
        trailer="trailers/trailer_258687.mp4",
        watch_kp="https://www.kinopoisk.ru/film/258687/",
        watch_rutube="https://rutube.ru/video/interstellar",
        watch_vk="https://vk.com/video/interstellar",
        gallery_json=json.dumps(["https://avatars.mds.yandex.net/get-kinopoisk-image/1600647/interstellar_still_1/orig"])
    )
    movie1.genres.extend([g_sci_fi, g_drama, g_adventure])
    movie1.actors.append(actor1)
    movie1.directors.append(director1)

    movie2 = Movie(
        kp_id="326",
        title="Побег из Шоушенка",
        original_title="The Shawshank Redemption",
        year=1994,
        slogan="Страх - это кандалы. Надежда - это свобода",
        description="Бухгалтер Энди Дюфрейн обвинён в убийстве собственной жены...",
        poster="https://avatars.mds.yandex.net/get-kinopoisk-image/1572049/2a1a8c9b-3e5f-4d3a-b8e7-1b0a9b8f2c3d/orig",
        posters_json=json.dumps(["https://avatars.mds.yandex.net/get-kinopoisk-image/1572049/2a1a8c9b-3e5f-4d3a-b8e7-1b0a9b8f2c3d/orig"]),
        duration="142 мин. / 02:22",
        duration_minutes=142,
        age="18+",
        country="США",
        budget="$25 000 000",
        boxoffice="$28 884 716",
        rating_kp=9.1,
        rating_site=9.1,
        trailer="trailers/trailer_326.mp4",
        watch_kp="https://www.kinopoisk.ru/film/326/",
        gallery_json=json.dumps([])
    )
    movie2.genres.append(g_drama)
    movie2.actors.append(actor2)
    movie2.directors.append(director2)

    movie3 = Movie(
        kp_id="435",
        title="Зеленая миля",
        original_title="The Green Mile",
        year=1999,
        slogan="Пол Эджкомб не верил в чудеса. Пока не столкнулся с одним из них",
        description="Пол Эджкомб — начальник блока смертников в тюрьме «Холодная гора»...",
        poster="https://avatars.mds.yandex.net/get-kinopoisk-image/1898899/443e111e-f714-4954-83d0-3e0acca2a561/orig",
        duration="189 мин. / 03:09",
        duration_minutes=189,
        age="18+",
        country="США",
        budget="$60 000 000",
        boxoffice="$286 800 000",
        rating_kp=9.1,
        rating_site=9.1,
        trailer="trailers/trailer_435.mp4"
    )
    movie3.genres.extend([g_drama, g_sci_fi])
    movie3.actors.append(actor3)
    movie3.directors.append(director2)

    session.add_all([movie1, movie2, movie3])
    session.commit()

    # 4. Awards attached to movie1
    award_oscar = Award(movie_id=movie1.id, name="Оскар", year=2015, nomination="Лучшие визуальные эффекты", is_winner=True)
    award_saturn = Award(movie_id=movie1.id, name="Сатурн", year=2015, nomination="Лучший научно-фантастический фильм", is_winner=True)
    session.add_all([award_oscar, award_saturn])

    # 5. Users
    pwd_hash1, salt1 = hash_password("demo12345")
    user_regular = User(
        username="demo_user",
        email="demo@kinoscore.ru",
        hashed_password=pwd_hash1,
        salt=salt1,
        avatar_url="https://api.dicebear.com/7.x/bottts/svg?seed=demo",
        is_admin=False
    )

    pwd_hash2, salt2 = hash_password("admin_pass123")
    user_admin = User(
        username="admin_user",
        email="admin@kinoscore.ru",
        hashed_password=pwd_hash2,
        salt=salt2,
        avatar_url="https://api.dicebear.com/7.x/bottts/svg?seed=admin",
        is_admin=True
    )
    session.add_all([user_regular, user_admin])
    session.commit()

    # 6. Sample Review
    sample_review = Review(
        movie_id=movie1.id,
        user_id=user_regular.id,
        rating=10,
        title="Шедевр научной фантастики!",
        content="Музыка Ханса Циммера и визуальный ряд просто поражают воображение."
    )
    session.add(sample_review)
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Provides FastAPI TestClient overriding the get_db dependency with test db_session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def regular_user_token(db_session):
    """Generates a valid JWT token for regular demo_user."""
    user = db_session.query(User).filter(User.username == "demo_user").first()
    return create_access_token({"sub": user.username, "user_id": user.id, "is_admin": False})


@pytest.fixture
def admin_user_token(db_session):
    """Generates a valid JWT token for admin_user."""
    user = db_session.query(User).filter(User.username == "admin_user").first()
    return create_access_token({"sub": user.username, "user_id": user.id, "is_admin": True})


@pytest.fixture
def auth_headers(regular_user_token):
    """Headers dict containing Bearer token for regular user."""
    return {"Authorization": f"Bearer {regular_user_token}"}


@pytest.fixture
def admin_headers(admin_user_token):
    """Headers dict containing Bearer token for admin user."""
    return {"Authorization": f"Bearer {admin_user_token}"}
