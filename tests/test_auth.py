"""
Unit & Integration tests for JWT Authentication System (core/security.py, router/auth.py).
"""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.security import create_access_token, decode_access_token, hash_password, verify_password
from database import get_db
from main import app
from models import Base


def test_password_hashing():
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_encoding_decoding():
    payload = {"sub": "user@example.com"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user@example.com"
    assert "exp" in decoded


@pytest.mark.asyncio
async def test_auth_flow_endpoints():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register User
        register_payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePassword123",
        }
        res_reg = await client.post("/auth/register", json=register_payload)
        assert res_reg.status_code == 201
        data_reg = res_reg.json()
        assert data_reg["email"] == "jane@example.com"
        assert "password" not in data_reg

        # 2. Login User
        login_data = {
            "username": "jane@example.com",
            "password": "SecurePassword123",
        }
        res_login = await client.post("/auth/login", data=login_data)
        assert res_login.status_code == 200
        token_data = res_login.json()
        assert "access_token" in token_data
        token = token_data["access_token"]

        # 3. Access Protected Route /auth/me with Bearer Token
        headers = {"Authorization": f"Bearer {token}"}
        res_me = await client.get("/auth/me", headers=headers)
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == "jane@example.com"
        assert me_data["name"] == "Jane Doe"

        # 4. Access Protected Route without token should fail (401)
        res_unauth = await client.get("/auth/me")
        assert res_unauth.status_code == 401

    app.dependency_overrides.clear()
    await engine.dispose()
