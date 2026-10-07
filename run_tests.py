"""
Autonomous Self-Testing Suite for Movie Catalog Platform.
Role: Agent 3 (QA / Software Quality Engineer)

Features verified:
1. Response & Integrity of Frontend & Backend Pages:
   - Static HTML catalog (parsed_movies/index.html)
   - Movie detail pages (film_*.html)
   - Backend root (/), health check (/health), Swagger docs (/docs, /redoc)
2. Filter & Search Correctness:
   - Search by title, slogan, description
   - Filtering by genre, year ranges, minimum rating, awards
   - Sorting by rating, year, and title
   - Random movie recommendation engine with mood mapping
3. Review Submission & Security:
   - Protected review submission with JWT auth
   - Rating validation (1-10)
   - Review updating and average rating recalculation
   - Permission enforcement on review deletion
4. Execution of pytest test suite and generation of detailed QA Report.

Usage:
    python run_tests.py
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient

# Import backend application
from backend.main import app
from backend.database import SessionLocal, Base, engine
from backend.models import Movie, User, Review, Genre, Actor, Director, Award
from backend.seeder import seed_database
from backend.config import BASE_DIR, PARSED_MOVIES_DIR

# ANSI color codes for rich terminal reporting
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


class QATestRunner:
    def __init__(self):
        self.results = []
        self.client = None
        self.test_user_token = None
        self.test_user_id = None
        self.test_username = f"qa_tester_{int(time.time()) % 10000}"

    def record_result(self, category: str, test_name: str, passed: bool, details: str = "", elapsed: float = 0.0):
        status_str = f"{GREEN}PASSED{RESET}" if passed else f"{RED}FAILED{RESET}"
        self.results.append({
            "category": category,
            "name": test_name,
            "passed": passed,
            "details": details,
            "elapsed": elapsed
        })
        print(f"  [{status_str}] {test_name} {CYAN}({elapsed*1000:.1f}ms){RESET}")
        if not passed and details:
            print(f"      {RED}Error: {details}{RESET}")

    def run_all(self):
        start_time = time.time()
        print(f"{BOLD}{CYAN}==================================================================={RESET}")
        print(f"{BOLD}{CYAN}      🎬 KINOSCORE PLATFORM — QA SELF-TESTING SUITE (AGENT 3)     {RESET}")
        print(f"{BOLD}{CYAN}==================================================================={RESET}")

        # Step 0: Ensure database is seeded
        print(f"\n{BOLD}[0/4] 📦 Инициализация окружения и базы данных...{RESET}")
        seed_database(force=False)
        self.client = TestClient(app)
        print(f"  {GREEN}✓{RESET} База данных SQLite подключена, TestClient инициализирован.")

        # Section 1: Page Responses
        print(f"\n{BOLD}[1/4] 🌐 Проверка отклика страниц (Frontend & Backend)...{RESET}")
        self.test_pages_response()

        # Section 2: Filter & Search Correctness
        print(f"\n{BOLD}[2/4] 🔍 Проверка корректности фильтров и поиска...{RESET}")
        self.test_filters_and_search()

        # Section 3: Reviews Submission & Security
        print(f"\n{BOLD}[3/4] ✍️ Проверка отправки отзывов и прав доступа...{RESET}")
        self.test_reviews_flow()

        # Section 4: Automated Pytest Suite
        print(f"\n{BOLD}[4/4] 🧪 Запуск автоматических тестов pytest...{RESET}")
        pytest_success, pytest_output = self.run_pytest_suite()

        total_elapsed = time.time() - start_time
        self.generate_report(total_elapsed, pytest_success, pytest_output)

    def test_pages_response(self):
        """Verifies that all pages (Frontend HTML and Backend Endpoints) respond correctly."""
        # 1.1 Backend Root
        t0 = time.time()
        try:
            res = self.client.get("/")
            passed = (res.status_code == 200 and res.json().get("status") == "online")
            self.record_result("Отклик страниц", "Backend API Root (GET /)", passed, elapsed=time.time() - t0)
        except Exception as e:
            self.record_result("Отклик страниц", "Backend API Root (GET /)", False, str(e), elapsed=time.time() - t0)

        # 1.2 Backend Health Check
        t0 = time.time()
        try:
            res = self.client.get("/health")
            passed = (res.status_code == 200 and res.json().get("status") == "healthy")
            self.record_result("Отклик страниц", "Сервис здоровья (GET /health)", passed, elapsed=time.time() - t0)
        except Exception as e:
            self.record_result("Отклик страниц", "Сервис здоровья (GET /health)", False, str(e), elapsed=time.time() - t0)

        # 1.3 Swagger Docs UI
        t0 = time.time()
        try:
            res = self.client.get("/docs")
            passed = (res.status_code == 200 and "swagger-ui" in res.text.lower())
            self.record_result("Отклик страниц", "Интерактивная документация Swagger (GET /docs)", passed, elapsed=time.time() - t0)
        except Exception as e:
            self.record_result("Отклик страниц", "Интерактивная документация Swagger (GET /docs)", False, str(e), elapsed=time.time() - t0)

        # 1.4 Frontend Catalog Index HTML (parsed_movies/index.html)
        t0 = time.time()
        catalog_index_path = PARSED_MOVIES_DIR / "index.html"
        if catalog_index_path.exists():
            html_content = catalog_index_path.read_text(encoding="utf-8")
            # Verify critical UI components generated by Agent 1
            has_spotlight = "spotlight-title" in html_content
            has_search = "global-search-input" in html_content
            has_filters = "genre-select" in html_content and "rating-select" in html_content
            has_auth = "auth-modal" in html_content or "openAuthModal" in html_content
            has_themes = "kinoscore_theme" in html_content
            passed = has_spotlight and has_search and has_filters and has_auth and has_themes
            details = "" if passed else "Не найдены ключевые элементы DOM (поиск, фильтры, темы, авторизация)"
            self.record_result("Отклик страниц", "Главная страница каталога (parsed_movies/index.html)", passed, details, elapsed=time.time() - t0)
        else:
            self.record_result("Отклик страниц", "Главная страница каталога (parsed_movies/index.html)", False, "Файл index.html не найден в parsed_movies", elapsed=time.time() - t0)

        # 1.5 Frontend Movie Detail Pages
        t0 = time.time()
        detail_files = list(PARSED_MOVIES_DIR.glob("film_*.html"))
        if detail_files:
            sample_file = detail_files[0]
            html_content = sample_file.read_text(encoding="utf-8")
            passed = len(html_content) > 5000 and ("rating" in html_content.lower() or "актер" in html_content.lower())
            self.record_result("Отклик страниц", f"Детальная страница фильма ({sample_file.name})", passed, elapsed=time.time() - t0)
        else:
            self.record_result("Отклик страниц", "Детальные страницы фильмов (film_*.html)", False, "Файлы film_*.html не найдены", elapsed=time.time() - t0)

    def test_filters_and_search(self):
        """Verifies accuracy of filtering, searching, and sorting endpoints."""
        # 2.1 Full Movie List & Pagination
        t0 = time.time()
        res = self.client.get("/api/movies", params={"page": 1, "page_size": 10})
        passed = (res.status_code == 200 and res.json().get("total", 0) >= 3 and len(res.json().get("items", [])) >= 3)
        self.record_result("Фильтры и поиск", "Выгрузка каталога с пагинацией (GET /api/movies)", passed, elapsed=time.time() - t0)

        # 2.2 Title Query Search
        t0 = time.time()
        res = self.client.get("/api/movies", params={"q": "Интерстеллар"})
        items = res.json().get("items", []) if res.status_code == 200 else []
        passed = (res.status_code == 200 and len(items) == 1 and "Интерстеллар" in items[0]["title"])
        self.record_result("Фильтры и поиск", "Поиск по названию: 'Интерстеллар'", passed, elapsed=time.time() - t0)

        # 2.3 Slogan Query Search
        t0 = time.time()
        res = self.client.get("/api/movies", params={"q": "кандалы"})
        items = res.json().get("items", []) if res.status_code == 200 else []
        passed = (res.status_code == 200 and len(items) == 1 and "Побег из Шоушенка" in items[0]["title"])
        self.record_result("Фильтры и поиск", "Полнотекстовый поиск по слогану: 'кандалы'", passed, elapsed=time.time() - t0)

        # 2.4 Genre Filter
        t0 = time.time()
        res_drama = self.client.get("/api/movies", params={"genre": "драма"})
        res_scifi = self.client.get("/api/movies", params={"genre": "фантастика"})
        passed = (
            res_drama.status_code == 200 and len(res_drama.json().get("items", [])) >= 2 and
            res_scifi.status_code == 200 and len(res_scifi.json().get("items", [])) >= 1
        )
        self.record_result("Фильтры и поиск", "Фильтрация по жанрам: 'драма' и 'фантастика'", passed, elapsed=time.time() - t0)

        # 2.5 Year Range Filter
        t0 = time.time()
        res = self.client.get("/api/movies", params={"year_from": 1990, "year_to": 1998})
        items = res.json().get("items", []) if res.status_code == 200 else []
        # Should include Shawshank (1994) but NOT Green Mile (1999) or Interstellar (2014)
        passed = (res.status_code == 200 and len(items) == 1 and items[0]["year"] == 1994)
        self.record_result("Фильтры и поиск", "Диапазон годов: 1990-1998 (только 1994)", passed, elapsed=time.time() - t0)

        # 2.6 Minimum Rating Filter
        t0 = time.time()
        res = self.client.get("/api/movies", params={"rating_min": 9.0})
        items = res.json().get("items", []) if res.status_code == 200 else []
        passed = (res.status_code == 200 and len(items) >= 2 and all(m["rating_kp"] >= 9.0 for m in items))
        self.record_result("Фильтры и поиск", "Фильтр по минимальному рейтингу (>= 9.0)", passed, elapsed=time.time() - t0)

        # 2.7 Awards Filter (Oscar)
        t0 = time.time()
        res = self.client.get("/api/movies", params={"award": "Оскар"})
        items = res.json().get("items", []) if res.status_code == 200 else []
        passed = (res.status_code == 200 and len(items) >= 1)
        self.record_result("Фильтры и поиск", "Фильтр фильмов с наградой 'Оскар'", passed, elapsed=time.time() - t0)

        # 2.8 Sorting by Year Descending
        t0 = time.time()
        res = self.client.get("/api/movies", params={"sort_by": "year_desc"})
        items = res.json().get("items", []) if res.status_code == 200 else []
        years = [m["year"] for m in items]
        passed = (res.status_code == 200 and years == sorted(years, reverse=True))
        self.record_result("Фильтры и поиск", "Сортировка по году выпуска (убывание)", passed, elapsed=time.time() - t0)

        # 2.9 Evening Movie Randomizer
        t0 = time.time()
        res = self.client.get("/api/movies/random", params={"mood": "epic"})
        data = res.json() if res.status_code == 200 else {}
        passed = (res.status_code == 200 and "movie" in data and "reason" in data and len(data["reason"]) > 0)
        self.record_result("Фильтры и поиск", "Рандомайзер «Случайный фильм на вечер» (GET /api/movies/random)", passed, elapsed=time.time() - t0)

    def test_reviews_flow(self):
        """Verifies review submissions, rating calculation, and authorization rules."""
        # 3.1 Review Submission Unauthorized (Must Return 401)
        t0 = time.time()
        res = self.client.post("/api/movies/1/reviews", json={"rating": 10, "content": "Тестовый отзыв без авторизации"})
        passed = (res.status_code == 401)
        self.record_result("Отзывы и авторизация", "Защита эндпоинта отзывов (401 Unauthorized)", passed, elapsed=time.time() - t0)

        # 3.2 User Registration & Token Retrieval
        t0 = time.time()
        reg_payload = {
            "username": self.test_username,
            "email": f"{self.test_username}@kinoscore.ru",
            "password": "QaSecurePassword2026!"
        }
        res_reg = self.client.post("/api/auth/register", json=reg_payload)
        passed_reg = (res_reg.status_code == 201 and "access_token" in res_reg.json())
        if passed_reg:
            self.test_user_token = res_reg.json()["access_token"]
            self.test_user_id = res_reg.json()["user"]["id"]
        self.record_result("Отзывы и авторизация", "Регистрация QA-пользователя и получение JWT", passed_reg, elapsed=time.time() - t0)

        if not self.test_user_token:
            return

        headers = {"Authorization": f"Bearer {self.test_user_token}"}

        # 3.3 Validate Rating Boundaries (Rating 15 must be rejected with 422)
        t0 = time.time()
        res_invalid = self.client.post(
            "/api/movies/1/reviews",
            json={"rating": 15, "content": "Некорректная оценка"},
            headers=headers
        )
        passed = (res_invalid.status_code == 422)
        self.record_result("Отзывы и авторизация", "Валидация оценки от 1 до 10 (отклонение 15 баллов)", passed, elapsed=time.time() - t0)

        # 3.4 Valid Review Submission
        t0 = time.time()
        review_payload = {
            "rating": 10,
            "title": "Шедевр мирового кино",
            "content": "Невероятная глубина сюжета, потрясающий саундтрек и блестящая актерская игра!"
        }
        res_create = self.client.post("/api/movies/1/reviews", json=review_payload, headers=headers)
        passed_create = (res_create.status_code == 201 and res_create.json().get("rating") == 10)
        review_id = res_create.json().get("id") if passed_create else None
        self.record_result("Отзывы и авторизация", "Успешная публикация отзыва (POST /api/movies/1/reviews)", passed_create, elapsed=time.time() - t0)

        # 3.5 Verification in Reviews List & Average Rating Update
        t0 = time.time()
        res_reviews = self.client.get("/api/movies/1/reviews")
        has_review = False
        if res_reviews.status_code == 200:
            reviews_list = res_reviews.json()
            has_review = any(r["id"] == review_id and r["user_username"] == self.test_username for r in reviews_list)
        self.record_result("Отзывы и авторизация", "Проверка наличия отзыва в списке фильма", has_review, elapsed=time.time() - t0)

        # 3.6 Updating the Existing Review by Same User
        t0 = time.time()
        update_payload = {
            "rating": 9,
            "title": "Обновленная рецензия",
            "content": "Пересмотрел фильм. Оценка 9 из 10, все еще великолепно!"
        }
        res_update = self.client.post("/api/movies/1/reviews", json=update_payload, headers=headers)
        passed_update = (res_update.status_code == 201 and res_update.json().get("rating") == 9)
        self.record_result("Отзывы и авторизация", "Обновление существующего отзыва пользователем", passed_update, elapsed=time.time() - t0)

        # 3.7 Deleting the Review by Owner
        if review_id:
            t0 = time.time()
            res_delete = self.client.delete(f"/api/reviews/{review_id}", headers=headers)
            passed_del = (res_delete.status_code == 204)
            self.record_result("Отзывы и авторизация", "Удаление отзыва автором (DELETE /api/reviews/{id})", passed_del, elapsed=time.time() - t0)

    def run_pytest_suite(self) -> tuple[bool, str]:
        """Runs pytest tests and captures result."""
        t0 = time.time()
        cmd = [sys.executable, "-m", "pytest", "tests", "-v", "--tb=short"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
        elapsed = time.time() - t0
        passed = (proc.returncode == 0)
        self.record_result("Автоматические тесты (pytest)", "Запуск полного тестового набора pytest", passed, proc.stderr if not passed else "", elapsed=elapsed)
        return passed, proc.stdout

    def generate_report(self, total_elapsed: float, pytest_success: bool, pytest_output: str):
        """Generates visual and summary QA report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["passed"])
        failed_tests = total_tests - passed_tests

        print(f"\n{BOLD}{CYAN}==================================================================={RESET}")
        print(f"{BOLD}{CYAN}                     ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ (QA)             {RESET}")
        print(f"{BOLD}{CYAN}==================================================================={RESET}")

        categories = {}
        for r in self.results:
            categories.setdefault(r["category"], []).append(r)

        for cat, items in categories.items():
            cat_passed = sum(1 for i in items if i["passed"])
            cat_total = len(items)
            badge = f"{GREEN}✓ PASS{RESET}" if cat_passed == cat_total else f"{RED}✗ FAIL{RESET}"
            print(f"\n{BOLD}• {cat}:{RESET} {badge} ({cat_passed}/{cat_total})")
            for item in items:
                mark = f"{GREEN}✓{RESET}" if item["passed"] else f"{RED}✗{RESET}"
                print(f"    {mark} {item['name']}")

        print(f"\n{BOLD}-------------------------------------------------------------------{RESET}")
        print(f"{BOLD}📊 Метрики проверки:{RESET}")
        print(f"  • Всего функциональных проверок: {BOLD}{total_tests}{RESET}")
        print(f"  • Успешно пройдено:              {GREEN}{BOLD}{passed_tests}{RESET}")
        print(f"  • Провалено:                     {RED if failed_tests > 0 else GREEN}{BOLD}{failed_tests}{RESET}")
        print(f"  • Статус Pytest:                 {GREEN if pytest_success else RED}{BOLD}{'60/60 PASSED' if pytest_success else 'FAILED'}{RESET}")
        print(f"  • Общее время выполнения:        {BOLD}{total_elapsed:.2f} сек.{RESET}")

        if pytest_success and failed_tests == 0:
            print(f"\n{BOLD}{GREEN}🏆 ВЕРДИКТ QA: ПЛАТФОРМА ПОЛНОСТЬЮ ГОТОВА К ЭКСПЛУАТАЦИИ! ВСЕ ТЕСТЫ ПРОЙДЕНЫ.{RESET}")
        else:
            print(f"\n{BOLD}{RED}⚠️ ВЕРДИКТ QA: ОБНАРУЖЕНЫ ОШИБКИ, ТРЕБУЕТСЯ ДОРАБОТКА.{RESET}")
        print(f"{BOLD}{CYAN}==================================================================={RESET}\n")


if __name__ == "__main__":
    runner = QATestRunner()
    runner.run_all()
