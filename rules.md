# Архитектура бэкенда и базы данных (Агент 2)

## 📌 Обзор
Автономный высокопроизводительный бэкенд на **FastAPI** с файловой базой данных **SQLite** (без Docker), разработанный для работы с каталогом спарсенных фильмов.

---

## 🚀 Быстрый запуск

```bash
# Запуск бэкенда (хост: http://127.0.0.1:8000)
python run_backend.py
# или
uvicorn backend.main:app --reload --port 8000
```

- **Swagger UI (Интерактивная документация)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Автотесты**: `python test_backend.py`

---

## 🗄️ База данных SQLite (`movies.db`)

Автоматически создается в корне проекта при первом запуске и наполняется спарсенными данными из `parsed_movies/`.

### Сущности и связи (ORM SQLAlchemy):
1. **Фильмы (`Movie`)**:
   - `id`, `kp_id`, `title`, `original_title`, `year`, `slogan`, `description`
   - `poster`, `posters_json`, `duration`, `duration_minutes`, `age`, `country`
   - `budget`, `boxoffice`, `rating_kp`, `rating_site`, `trailer`
   - `watch_kp`, `watch_rutube`, `watch_vk`, `gallery_json`, `created_at`
2. **Жанры (`Genre`)**: `id`, `name`, `slug` (связь Many-to-Many через `movie_genres`).
3. **Актеры (`Actor`)**: `id`, `kp_id`, `name`, `photo_url` (связь Many-to-Many через `movie_actors`).
4. **Режиссеры (`Director`)**: `id`, `kp_id`, `name`, `photo_url` (связь Many-to-Many через `movie_directors`).
5. **Награды (`Award`)**: `id`, `movie_id`, `name` (Оскар, Сатурн и др.), `year`, `nomination`, `is_winner`.
6. **Пользователи (`User`)**: `id`, `username`, `email`, `hashed_password`, `salt`, `avatar_url`, `is_active`, `is_admin`.
7. **Отзывы (`Review`)**: `id`, `user_id`, `movie_id`, `rating` (1-10), `title`, `content`, `created_at`, `updated_at`.
8. **Избранное (`Favorite`)**: `id`, `user_id`, `movie_id`, `created_at` (уникальная пара user_id + movie_id).
9. **История просмотров (`WatchHistory`)**: `id`, `user_id`, `movie_id`, `watched_at`, `progress_seconds`, `is_completed`.

---

## 🔑 Авторизация и безопасность (`/api/auth`)

- **Хэширование паролей**: `PBKDF2-HMAC-SHA256` со 100,000 итерациями и индивидуальной солью (salt) для каждого пользователя. Устойчиво к rainbow tables и timing attacks.
- **Токены**: JWT Bearer токены с временем жизни и HS256-подписью.
- **Эндпоинты**:
  - `POST /api/auth/register` — регистрация нового аккаунта.
  - `POST /api/auth/login` — вход по логину/email и паролю (поддерживает JSON и OAuth2 form).
  - `GET /api/auth/me` — профиль авторизованного пользователя.

> **Тестовые аккаунты (создаются сидером):**
> - Пользователь: `demo_user` / пароль: `demo12345`
> - Администратор: `admin` / пароль: `admin12345`
> - Критик: `critic_anna` / пароль: `critic12345`

---

## 🔍 Фильтрация и поиск (`/api/movies`)

- `GET /api/movies`:
  - `q`: полнотекстовый поиск по названию, оригинальному названию, слогану и описанию.
  - `genre`: фильтр по названию или слагу жанра (регистронезависимый поиск).
  - `year_from` / `year_to`: диапазон годов выпуска.
  - `rating_min` / `rating_max`: диапазон рейтинга Кинопоиска.
  - `award`: фильтрация по кинопремии (например: `award=Оскар`).
  - `has_awards`: только фильмы с наградами (`true`/`false`).
  - `actor`: поиск по имени актера.
  - `director`: поиск по имени режиссера.
  - `sort_by`: `rating_desc`, `rating_asc`, `year_desc`, `year_asc`, `title_asc`, `title_desc`.
  - `page`, `page_size`: пагинация со счетчиком `total_pages`.

- `GET /api/movies/{id}`:
  - Полная детальная карточка фильма со всеми актерами, наградами, кадрами галереи, трейлерами, отзывами, средним баллом и персональными флагами `is_favorite` / `in_watch_history`.

---

## 🎲 Рандомайзер: «Случайный фильм на вечер»

- `GET /api/movies/random`:
  - Параметры: `mood` (`epic`, `drama`, `mindfuck`, `uplifting`, `chill`), `genre`, `min_rating`, `year_from`.
  - Возвращает фильм с индивидуальной формулировкой причины выбора под заданный запрос.

---

## ⭐ Избранное и История просмотров

- **Избранное**:
  - `GET /api/favorites` — список избранных фильмов.
  - `POST /api/favorites/{movie_id}` — добавить фильм.
  - `DELETE /api/favorites/{movie_id}` — удалить фильм.
  - `GET /api/favorites/check/{movie_id}` — проверка наличия.

- **История просмотров**:
  - `GET /api/history` — история просмотров от недавних к старым.
  - `POST /api/history/{movie_id}` — зафиксировать просмотр с сохранением прогресса в секундах.
  - `DELETE /api/history/{movie_id}` — удалить из истории.
  - `DELETE /api/history` — полная очистка истории.

---

## 💬 Отзывы и Рецензии (`/api/movies/{id}/reviews`)

- `GET /api/movies/{movie_id}/reviews` — открытый список отзывов к фильму.
- `POST /api/movies/{movie_id}/reviews` — защищенная публикация отзыва с оценкой 1-10.
- `DELETE /api/reviews/{review_id}` — удаление отзыва автором или администратором.
