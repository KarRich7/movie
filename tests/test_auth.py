"""
Automated pytest tests for Authentication & User Registration:
- POST /api/auth/register
- POST /api/auth/login (JSON & Form)
- GET /api/auth/me
- Password hashing & verification validation
- Token security & invalid token handling
"""
import pytest
from backend.security import hash_password, verify_password


class TestAuthRegistration:
    def test_register_user_success(self, client):
        """Test successful registration of a new user."""
        payload = {
            "username": "new_critic",
            "email": "critic@example.com",
            "password": "StrongPassword123!",
            "avatar_url": "https://example.com/avatar.png"
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "new_critic"
        assert data["user"]["email"] == "critic@example.com"
        assert data["user"]["is_admin"] is False

    def test_register_duplicate_username_fails(self, client):
        """Test that registering with existing username returns 400."""
        payload = {
            "username": "demo_user",  # Already in fixture
            "email": "another_email@example.com",
            "password": "Password123"
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 400
        assert "уже существует" in res.json()["detail"]

    def test_register_duplicate_email_fails(self, client):
        """Test that registering with existing email returns 400."""
        payload = {
            "username": "distinct_user",
            "email": "demo@kinoscore.ru",  # Already in fixture
            "password": "Password123"
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 400
        assert "уже зарегистрирован" in res.json()["detail"]

    def test_register_validation_short_password(self, client):
        """Test that registering with short password returns 422 Unprocessable Entity."""
        payload = {
            "username": "valid_user",
            "email": "valid@example.com",
            "password": "123"  # Less than 6 chars
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 422


class TestAuthLogin:
    def test_login_success_with_username_json(self, client):
        """Test login with username using JSON body."""
        payload = {
            "username_or_email": "demo_user",
            "password": "demo12345"
        }
        res = client.post("/api/auth/login", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["user"]["username"] == "demo_user"

    def test_login_success_with_email_json(self, client):
        """Test login with email using JSON body."""
        payload = {
            "username_or_email": "demo@kinoscore.ru",
            "password": "demo12345"
        }
        res = client.post("/api/auth/login", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["email"] == "demo@kinoscore.ru"

    def test_login_success_form_data(self, client):
        """Test login using Form Data (OAuth2 compatible for Swagger UI)."""
        form_data = {
            "username": "demo_user",
            "password": "demo12345"
        }
        res = client.post("/api/auth/login", data=form_data)
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_login_invalid_password(self, client):
        """Test login with incorrect password returns 401."""
        payload = {
            "username_or_email": "demo_user",
            "password": "WrongPassword999!"
        }
        res = client.post("/api/auth/login", json=payload)
        assert res.status_code == 401
        assert "Неверное имя пользователя" in res.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent username returns 401."""
        payload = {
            "username_or_email": "ghost_user",
            "password": "SomePassword"
        }
        res = client.post("/api/auth/login", json=payload)
        assert res.status_code == 401

    def test_login_empty_payload(self, client):
        """Test login with empty fields returns 400 or 422."""
        res = client.post("/api/auth/login", json={})
        assert res.status_code in [400, 422]


class TestAuthProfile:
    def test_get_me_authenticated(self, client, auth_headers):
        """Test GET /api/auth/me returns current user info."""
        res = client.get("/api/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "demo_user"
        assert data["email"] == "demo@kinoscore.ru"

    def test_get_me_unauthorized(self, client):
        """Test GET /api/auth/me without token returns 401."""
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Test GET /api/auth/me with invalid Bearer token returns 401."""
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
        assert res.status_code == 401


class TestPasswordHashingUnits:
    def test_pbkdf2_hash_and_verification(self):
        """Unit test for PBKDF2 salt generation and verification integrity."""
        raw_pass = "MySecretComplexPass!"
        h, salt = hash_password(raw_pass)
        assert len(h) == 64  # SHA-256 hex length
        assert len(salt) == 32  # 16 bytes hex length
        assert verify_password(raw_pass, h, salt) is True
        assert verify_password("WrongPass", h, salt) is False
