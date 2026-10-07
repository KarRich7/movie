"""
FastAPI Main Application for Movie Catalog Backend.
Author: Agent 2 (Backend Architect & Database)
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_DIR, PARSED_MOVIES_DIR
from backend.seeder import seed_database
from backend.routers import auth, movies, reviews, user_features, meta


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context: automatically initializes SQLite database and runs seeder on startup."""
    print("🚀 Initializing Movie Catalog Database...")
    seed_database(force=False)
    print("✨ Database ready and seeded.")
    yield
    print("🛑 Movie Catalog API shutdown.")


app = FastAPI(
    title="Movie Catalog & Recommendations API",
    description="""
## 🎬 КиноКаталог — Высокопроизводительный бэкенд на FastAPI и SQLite

### 📌 Основные возможности:
- **База данных**: Автономная файловая SQLite база данных с нормализованными связями.
- **Продвинутый поиск**: Фильтрация по жанрам, годам, рейтингу Кинопоиска, наградам (Оскар и др.), актерам и режиссерам.
- **Безопасность и Auth**: Регистрация и авторизация на JWT токенах, хэширование PBKDF2-HMAC-SHA256 с солью.
- **Интерактивные отзывы**: Защищенная публикация и модерация рецензий с оценками 1-10.
- **Умный рандомайзер**: «Случайный фильм на вечер» с подбором под настроение.
- **Личный кабинет**: Система избранного и история просмотров с сохранением прогресса.
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for seamless integration with any Frontend (React / Vite / HTML)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts for parsed trailers, posters, and assets
if (PARSED_MOVIES_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(PARSED_MOVIES_DIR / "assets")), name="parsed_assets")
elif (BASE_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "assets")), name="root_assets")

trailers_dir = PARSED_MOVIES_DIR / "trailers"
if trailers_dir.exists():
    app.mount("/trailers", StaticFiles(directory=str(trailers_dir)), name="trailers")
    app.mount("/static/trailers", StaticFiles(directory=str(trailers_dir)), name="static_trailers")

if PARSED_MOVIES_DIR.exists():
    app.mount("/static/parsed_movies", StaticFiles(directory=str(PARSED_MOVIES_DIR)), name="parsed_movies")

# Include Routers
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(reviews.router)
app.include_router(user_features.router)
app.include_router(meta.router)


@app.get("/", tags=["Общая информация"], summary="Витрина каталога или статус API")
def root(request: Request):
    """
    При переходе из браузера отображает красивую HTML-витрину каталога (parsed_movies/index.html).
    При запросе от API-клиентов (Accept: application/json) возвращает статус и ссылки.
    """
    index_file = PARSED_MOVIES_DIR / "index.html"
    accept = request.headers.get("accept", "")
    if "text/html" in accept and index_file.exists():
        return FileResponse(index_file)

    return {
        "status": "online",
        "app": "Movie Catalog API",
        "version": "2.0.0",
        "web_catalog": "http://127.0.0.1:8000/",
        "swagger_docs": "http://127.0.0.1:8000/docs",
        "redoc_docs": "http://127.0.0.1:8000/redoc",
        "endpoints": {
            "movies": "/api/movies",
            "random_movie": "/api/movies/random",
            "auth": "/api/auth/login",
            "favorites": "/api/favorites",
            "history": "/api/history",
            "stats": "/api/stats",
            "genres": "/api/genres"
        }
    }


@app.get("/film_{movie_id}.html", include_in_schema=False)
def serve_film_html(movie_id: str):
    """Отдает сгенерированную страницу фильма."""
    film_file = PARSED_MOVIES_DIR / f"film_{movie_id}.html"
    if film_file.exists():
        return FileResponse(film_file)
    index_file = PARSED_MOVIES_DIR / "index.html"
    return FileResponse(index_file)


@app.get("/health", tags=["Общая информация"], summary="Проверка здоровья сервиса")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
