import pytest
from sqlalchemy import select

import main
from ivhuRedu.models.user import User, UserType
from ivhuRedu.services.security import verify_password


async def test_root_endpoint(client):
    r = await client.get("/")
    assert r.status_code == 200 and r.json() == {
        "message": "Welcome to the IvhuRedu API",
        "status": "ok",
    }


async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_unknown_route_is_404_and_wrong_method_is_405(client):
    assert (await client.get("/does-not-exist")).status_code == 404
    assert (await client.post("/health")).status_code == 405


def test_expected_route_prefixes_are_registered():
    paths = set(main.app.openapi()["paths"])
    for prefix in (
        "/auth/login",
        "/auth/change-password",
        "/auth/refresh-token",
        "/auth/forgot-password",
        "/auth/verify-reset-otp",
        "/auth/reset-password",
        "/health",
        "/",
    ):
        assert prefix in paths
    for mount in (
        "/users",
        "/farmers",
        "/extension-workers",
        "/locations",
        "/farmer-requests",
        "/field-images",
        "/field-reports",
        "/sms",
    ):
        assert any(p.startswith(mount) for p in paths), mount


async def test_protected_endpoints_require_authentication(client):
    for path in ("/users/", "/farmers/", "/extension-workers/", "/field-reports/"):
        r = await client.get(path)
        assert r.status_code in (401, 403, 404, 405, 307), path
        assert r.status_code != 200, path


def _configured_origin():
    origins = [o.strip() for o in main.allowed_origins if o.strip()]
    return "http://example.com" if (not origins or "*" in origins) else origins[0]


async def test_cors_preflight_allows_configured_origin(client):
    origin = _configured_origin()
    r = await client.options(
        "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] in (origin, "*")


async def test_cors_preflight_rejects_unlisted_origin_when_origins_are_restricted(
    client,
):
    origins = [o.strip() for o in main.allowed_origins if o.strip()]
    if not origins or "*" in origins:
        pytest.skip("CORS is open to all origins in this environment")
    r = await client.options(
        "/health",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 400


async def test_onboard_admin_skipped_without_credentials(client, session, monkeypatch):
    monkeypatch.delenv("ADMIN_PHONE_NUMBER", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    await main.onboard_default_admin()
    assert (await session.execute(select(User))).scalars().all() == []


async def test_onboard_admin_creates_hashed_admin(client, session, monkeypatch):
    monkeypatch.setenv("ADMIN_PHONE_NUMBER", "+263770000999")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.delenv("ADMIN_FIRST_NAME", raising=False)
    monkeypatch.delenv("ADMIN_LAST_NAME", raising=False)
    await main.onboard_default_admin()
    admin = (await session.execute(select(User))).scalar_one()
    assert admin.user_type is UserType.ADMIN and admin.phone_number == "+263770000999"
    assert admin.first_name == "System" and admin.last_name == "Administrator"
    assert admin.hashed_password != "AdminPass123"
    assert await verify_password("AdminPass123", admin.hashed_password)
    assert admin.must_change_password is False


async def test_onboard_admin_is_idempotent(client, session, monkeypatch):
    monkeypatch.setenv("ADMIN_PHONE_NUMBER", "+263770000999")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123")
    await main.onboard_default_admin()
    await main.onboard_default_admin()
    assert len((await session.execute(select(User))).scalars().all()) == 1


async def test_onboard_admin_does_nothing_if_any_admin_exists(
    client, make_user, session, monkeypatch
):
    await make_user(user_type=UserType.ADMIN, phone="+263771111111")
    monkeypatch.setenv("ADMIN_PHONE_NUMBER", "+263770000999")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123")
    await main.onboard_default_admin()
    assert len((await session.execute(select(User))).scalars().all()) == 1


async def test_onboard_admin_custom_names_from_env(client, session, monkeypatch):
    monkeypatch.setenv("ADMIN_PHONE_NUMBER", "+263770000998")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123")
    monkeypatch.setenv("ADMIN_FIRST_NAME", "Chipo")
    monkeypatch.setenv("ADMIN_LAST_NAME", "Ncube")
    await main.onboard_default_admin()
    admin = (await session.execute(select(User))).scalar_one()
    assert (admin.first_name, admin.last_name) == ("Chipo", "Ncube")


def test_database_url_normalisation(monkeypatch):
    import importlib
    import database

    cases = {
        "postgres://u:p@h/db": "postgresql+asyncpg://u:p@h/db",
        "postgresql://u:p@h/db?sslmode=require&x=1": "postgresql+asyncpg://u:p@h/db?x=1",
        "postgresql+asyncpg://u:p@h/db?channel_binding=require": "postgresql+asyncpg://u:p@h/db",
    }
    try:
        for given, expected in cases.items():
            monkeypatch.setenv("DATABASE_URL", given)
            reloaded = importlib.reload(database)
            assert (
                str(reloaded.engine.url.render_as_string(hide_password=False))
                == expected
            )
    finally:
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
        importlib.reload(database)
