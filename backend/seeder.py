"""
Seeder script to populate:
1. movies.db from parsed_movies JSON files
2. users.db with demo users, initial reviews, favorites, and watch history.
"""
import glob
import json
import logging
import re
from pathlib import Path

from backend.config import BASE_DIR, PARSED_MOVIES_DIR
from backend.database import MoviesSessionLocal, UsersSessionLocal, ensure_database_schema
from backend.models import (
    Movie, Genre, Actor, Director, Award, User, Review, Favorite, WatchHistory
)
from backend.security import hash_password

logger = logging.getLogger("backend.seeder")


def slugify(text: str) -> str:
    """Converts a Russian or English text into an ASCII-compatible URL slug."""
    text = text.lower().strip()
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    result = []
    for char in text:
        if char in translit_map:
            result.append(translit_map[char])
        elif re.match(r'[a-z0-9]', char):
            result.append(char)
        elif char in [' ', '-', '_', ',']:
            result.append('-')
    slug = re.sub(r'-+', '-', ''.join(result)).strip('-')
    return slug or "genre"


def parse_duration_minutes(duration_str: str) -> int:
    """Extracts duration in minutes from string like '2 ч 49 мин' or '142 мин'."""
    if not duration_str:
        return 0
    hours = 0
    minutes = 0
    h_match = re.search(r'(\d+)\s*(?:ч|h|hours?)', duration_str, re.IGNORECASE)
    if h_match:
        hours = int(h_match.group(1))
    m_match = re.search(r'(\d+)\s*(?:мин|min|m)', duration_str, re.IGNORECASE)
    if m_match:
        minutes = int(m_match.group(1))
    
    if not hours and not minutes:
        d_match = re.search(r'(\d+)', duration_str)
        if d_match:
            minutes = int(d_match.group(1))
            
    return hours * 60 + minutes


def seed_database(force: bool = False):
    """Initializes tables in both databases and seeds data."""
    ensure_database_schema()
    db_movies = MoviesSessionLocal()
    db_users = UsersSessionLocal()

    try:
        # ================= 1. SEED MOVIES (movies.db) =================
        movie_count = db_movies.query(Movie).count()
        if movie_count == 0 or force:
            logger.info("Starting movies.db seeding...")

            raw_movies_dict = {}

            # Look in parsed_movies/film_*.json
            json_pattern = str(PARSED_MOVIES_DIR / "film_*.json")
            for filepath in glob.glob(json_pattern):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        movie_data = json.load(f)
                        movie_id = str(movie_data.get("id"))
                        raw_movies_dict[movie_id] = movie_data
                except Exception as e:
                    logger.error("Error reading %s: %s", filepath, e)

            # Check parsed_movies/movies.json
            catalog_path = PARSED_MOVIES_DIR / "movies.json"
            if catalog_path.exists():
                try:
                    with open(catalog_path, "r", encoding="utf-8") as f:
                        catalog_list = json.load(f)
                        for item in catalog_list:
                            m_id = str(item.get("id"))
                            if m_id not in raw_movies_dict:
                                raw_movies_dict[m_id] = item
                except Exception as e:
                    logger.error("Error reading %s: %s", catalog_path, e)

            genres_cache = {g.name: g for g in db_movies.query(Genre).all()}
            actors_cache = {a.name: a for a in db_movies.query(Actor).all()}
            directors_cache = {d.name: d for d in db_movies.query(Director).all()}

            for m_id, item in raw_movies_dict.items():
                existing = db_movies.query(Movie).filter(Movie.kp_id == m_id).first()
                if existing:
                    continue

                raw_title = item.get("title", "")
                title_clean = re.sub(r'\s*\(\d{4}\)$', '', raw_title).strip()
                
                raw_year = item.get("year")
                year_int = None
                if raw_year:
                    try:
                        year_int = int(str(raw_year).strip())
                    except ValueError:
                        pass

                def parse_float_rating(val):
                    if not val:
                        return 0.0
                    try:
                        return float(str(val).replace(",", ".").strip())
                    except ValueError:
                        return 0.0

                gallery = item.get("gallery", [])
                posters = item.get("posters", [])
                poster = item.get("poster") or (posters[0] if posters else None)

                movie = Movie(
                    kp_id=m_id,
                    title=title_clean,
                    original_title=item.get("original_title"),
                    year=year_int,
                    slogan=item.get("slogan"),
                    description=item.get("description"),
                    poster=poster,
                    posters_json=json.dumps(posters, ensure_ascii=False),
                    duration=item.get("duration"),
                    duration_minutes=parse_duration_minutes(item.get("duration", "")),
                    age=item.get("age"),
                    country=item.get("country"),
                    budget=item.get("budget"),
                    boxoffice=item.get("boxoffice"),
                    rating_kp=parse_float_rating(item.get("ratingKP")),
                    rating_site=parse_float_rating(item.get("ratingSite")),
                    trailer=item.get("trailer"),
                    watch_kp=item.get("watch_kp"),
                    watch_rutube=item.get("watch_rutube"),
                    watch_vk=item.get("watch_vk"),
                    gallery_json=json.dumps(gallery, ensure_ascii=False)
                )
                db_movies.add(movie)

                # Genres
                raw_genre_str = item.get("genre", "")
                if raw_genre_str:
                    genre_names = [g.strip().capitalize() for g in raw_genre_str.split(",") if g.strip()]
                    for g_name in genre_names:
                        if g_name not in genres_cache:
                            new_genre = Genre(name=g_name, slug=slugify(g_name))
                            db_movies.add(new_genre)
                            db_movies.flush()
                            genres_cache[g_name] = new_genre
                        movie.genres.append(genres_cache[g_name])

                # Directors
                director_str = item.get("director", "")
                if director_str:
                    director_names = [d.strip() for d in director_str.split(",") if d.strip()]
                    for d_name in director_names:
                        if d_name not in directors_cache:
                            new_director = Director(name=d_name)
                            db_movies.add(new_director)
                            db_movies.flush()
                            directors_cache[d_name] = new_director
                        movie.directors.append(directors_cache[d_name])

                # Actors
                raw_actors = item.get("actors", [])
                for a_item in raw_actors:
                    if isinstance(a_item, list) and len(a_item) >= 1:
                        actor_name = str(a_item[0]).strip()
                        actor_kp_id = str(a_item[1]).strip() if len(a_item) > 1 else None
                    elif isinstance(a_item, str):
                        actor_name = a_item.strip()
                        actor_kp_id = None
                    else:
                        continue

                    if not actor_name:
                        continue

                    if actor_name not in actors_cache:
                        new_actor = Actor(name=actor_name, kp_id=actor_kp_id)
                        db_movies.add(new_actor)
                        db_movies.flush()
                        actors_cache[actor_name] = new_actor
                    
                    if actors_cache[actor_name] not in movie.actors:
                        movie.actors.append(actors_cache[actor_name])

                # Awards
                raw_awards = item.get("awards", [])
                for aw in raw_awards:
                    aw_name = aw.get("name")
                    if not aw_name:
                        continue
                    raw_aw_year = aw.get("year")
                    aw_year = int(raw_aw_year) if raw_aw_year and str(raw_aw_year).isdigit() else None
                    award_obj = Award(
                        name=aw_name,
                        year=aw_year,
                        nomination=aw.get("nomination"),
                        is_winner=True
                    )
                    movie.awards.append(award_obj)

            db_movies.commit()
            logger.info("movies.db seeded successfully.")

        # ================= 2. SEED USERS (users.db) =================
        user_count = db_users.query(User).count()
        if user_count == 0 or force:
            logger.info("Starting users.db seeding...")

            demo_user = db_users.query(User).filter(User.username == "demo_user").first()
            if not demo_user:
                h_pass, salt = hash_password("demo12345")
                demo_user = User(
                    username="demo_user",
                    email="demo@kinocatalog.ru",
                    phone="+79991112233",
                    phone_verified=True,
                    email_verified=True,
                    auth_provider="email",
                    hashed_password=h_pass,
                    salt=salt,
                    first_name="Демо",
                    last_name="Пользователь",
                    avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop",
                    is_admin=False
                )
                db_users.add(demo_user)

            admin_user = db_users.query(User).filter(User.username == "admin").first()
            if not admin_user:
                h_pass, salt = hash_password("admin12345")
                admin_user = User(
                    username="admin",
                    email="admin@kinocatalog.ru",
                    auth_provider="email",
                    hashed_password=h_pass,
                    salt=salt,
                    first_name="Администратор",
                    avatar_url="https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=150&auto=format&fit=crop",
                    is_admin=True
                )
                db_users.add(admin_user)

            critic_user = db_users.query(User).filter(User.username == "critic_anna").first()
            if not critic_user:
                h_pass, salt = hash_password("critic12345")
                critic_user = User(
                    username="critic_anna",
                    email="anna@kinocritic.com",
                    auth_provider="gmail",
                    hashed_password=h_pass,
                    salt=salt,
                    first_name="Анна",
                    last_name="Кинокритик",
                    avatar_url="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop",
                    is_admin=False
                )
                db_users.add(critic_user)

            db_users.commit()

            # Seed initial reviews & favorites in users.db
            interstellar = db_movies.query(Movie).filter(Movie.title.ilike("%Интерстеллар%")).first()
            shawshank = db_movies.query(Movie).filter(Movie.title.ilike("%Шоушенк%")).first()
            green_mile = db_movies.query(Movie).filter(Movie.title.ilike("%Зеленая миля%")).first()

            if interstellar and not db_users.query(Review).filter(Review.movie_id == interstellar.id, Review.user_id == critic_user.id).first():
                r1 = Review(
                    movie_id=interstellar.id,
                    user_id=critic_user.id,
                    rating=10,
                    title="Безупречный триумф научной фантастики",
                    content="Кристофер Нолан создал не просто фильм о космосе, а глубочайшую драму о человеческой любви, преодолевающей время и гравитацию. Саундтрек Ханса Циммера пробирает до мурашек, а визуальные эффекты и звук заслуженно взяли 'Оскар'."
                )
                db_users.add(r1)

            if shawshank and not db_users.query(Review).filter(Review.movie_id == shawshank.id, Review.user_id == demo_user.id).first():
                r2 = Review(
                    movie_id=shawshank.id,
                    user_id=demo_user.id,
                    rating=10,
                    title="Фильм, который дает надежду",
                    content="Великолепная история о силе человеческого духа, дружбе и вере в свободу. Фильм по праву занимает первое место во всех мировых рейтингах."
                )
                db_users.add(r2)

            if green_mile and not db_users.query(Review).filter(Review.movie_id == green_mile.id, Review.user_id == critic_user.id).first():
                r3 = Review(
                    movie_id=green_mile.id,
                    user_id=critic_user.id,
                    rating=10,
                    title="Эмоциональное потрясение",
                    content="Экранизация Стивена Кинга в исполнении Фрэнка Дарабонта трогает до глубины души. Том Хэнкс и Майкл Кларк Дункан сыграли свои лучшие роли."
                )
                db_users.add(r3)

            # Favorites for demo_user
            if interstellar and not db_users.query(Favorite).filter(Favorite.user_id == demo_user.id, Favorite.movie_id == interstellar.id).first():
                db_users.add(Favorite(user_id=demo_user.id, movie_id=interstellar.id))

            if shawshank and not db_users.query(Favorite).filter(Favorite.user_id == demo_user.id, Favorite.movie_id == shawshank.id).first():
                db_users.add(Favorite(user_id=demo_user.id, movie_id=shawshank.id))

            # Watch History for demo_user
            if green_mile and not db_users.query(WatchHistory).filter(WatchHistory.user_id == demo_user.id, WatchHistory.movie_id == green_mile.id).first():
                db_users.add(WatchHistory(user_id=demo_user.id, movie_id=green_mile.id, progress_seconds=11340, is_completed=True))

            db_users.commit()
            logger.info("users.db seeded successfully.")

    except Exception as e:
        db_movies.rollback()
        db_users.rollback()
        logger.error("Database seeding failed: %s", e)
        raise e
    finally:
        db_movies.close()
        db_users.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_database(force=True)
    print("Database seeding completed.")
