import uuid
from datetime import timedelta

import pytest

from ivhuRedu.models.user import UserType
from ivhuRedu.services import security
from ivhuRedu.services.security import hash_password_reset_otp

pytestmark = pytest.mark.asyncio


def form(phone, password):
    return {"username": phone, "password": password}


async def test_login_admin_success(client, make_user):
    u = await make_user(user_type=UserType.ADMIN)
    r = await client.post("/auth/login", data=form(u.phone_number, "Password123"))
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin" and body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["offline_token"] is None and body["must_change_password"] is False


async def test_login_extension_worker_returns_offline_token_and_worker_id(
    client, make_worker
):
    user, worker = await make_worker()
    body = (
        await client.post("/auth/login", data=form(user.phone_number, "Password123"))
    ).json()
    assert body["offline_token"] and body["worker_id"] == str(worker.worker_id)


async def test_login_unknown_phone_is_401(client):
    assert (
        await client.post("/auth/login", data=form("+263000000000", "Password123"))
    ).status_code == 401


async def test_login_missing_fields_is_422(client):
    assert (await client.post("/auth/login", data={})).status_code == 422


async def test_login_wrong_password_is_401(client, make_user):
    u = await make_user()
    r = await client.post("/auth/login", data=form(u.phone_number, "nope"))
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


async def test_login_farmer_and_locked_user_are_403(client, make_user):
    farmer = await make_user(user_type=UserType.FARMER)
    locked = await make_user(is_locked=True)
    assert (
        await client.post("/auth/login", data=form(farmer.phone_number, "Password123"))
    ).status_code == 403
    assert (
        await client.post("/auth/login", data=form(locked.phone_number, "Password123"))
    ).status_code == 403


async def test_login_requires_form_encoding_not_json(client, make_user):
    u = await make_user()
    r = await client.post("/auth/login", json=form(u.phone_number, "Password123"))
    assert r.status_code == 422


async def test_change_password_flow_then_login_with_new_password(
    client, make_user, auth_headers
):
    u = await make_user(must_change_password=True)
    r = await client.post(
        "/auth/change-password",
        headers=await auth_headers(u),
        json={"old_password": "Password123", "new_password": "BrandNew456"},
    )
    assert r.status_code == 200
    assert (
        await client.post("/auth/login", data=form(u.phone_number, "Password123"))
    ).status_code == 401
    ok = await client.post("/auth/login", data=form(u.phone_number, "BrandNew456"))
    assert ok.status_code == 200 and ok.json()["must_change_password"] is False


async def test_change_password_requires_authentication(client):
    r = await client.post(
        "/auth/change-password",
        json={"old_password": "a", "new_password": "BrandNew456"},
    )
    assert r.status_code == 401


@pytest.mark.parametrize(
    "payload, status",
    [
        ({"old_password": "wrong", "new_password": "BrandNew456"}, 400),
        ({"old_password": "Password123", "new_password": "Password123"}, 400),
        ({"old_password": "Password123", "new_password": "short"}, 422),
        ({"old_password": "Password123"}, 422),
        ({}, 422),
    ],
)
async def test_change_password_validation_and_errors(
    client, make_user, auth_headers, payload, status
):
    u = await make_user()
    assert (
        await client.post(
            "/auth/change-password", headers=await auth_headers(u), json=payload
        )
    ).status_code == status


async def test_change_password_rejects_refresh_token_as_bearer(client, make_user):
    u = await make_user()
    token = await security.create_refresh_token({"sub": str(u.id)})
    r = await client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "Password123", "new_password": "BrandNew456"},
    )
    assert r.status_code == 401


async def test_refresh_token_issues_new_tokens(client, make_user):
    u = await make_user(user_type=UserType.SUPERVISOR)
    refresh = await security.create_refresh_token({"sub": str(u.id)})
    r = await client.post("/auth/refresh-token", json={"refresh_token": refresh})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "supervisor" and body["offline_token"] is None
    assert (await security.decode_token(body["access_token"]))["token_type"] == "access"


async def test_refresh_token_for_worker_includes_offline_token(client, make_worker):
    user, _ = await make_worker()
    refresh = await security.create_refresh_token({"sub": str(user.id)})
    assert (
        await client.post("/auth/refresh-token", json={"refresh_token": refresh})
    ).json()["offline_token"]


@pytest.mark.parametrize("kind", ["access", "offline", "reset"])
async def test_refresh_token_rejects_other_token_types(client, make_user, kind):
    u = await make_user()
    token = {
        "access": await security.create_access_token({"sub": str(u.id)}),
        "offline": await security.create_offline_token({"sub": str(u.id)}),
        "reset": await security.create_password_reset_token(str(u.id)),
    }[kind]
    r = await client.post("/auth/refresh-token", json={"refresh_token": token})
    assert r.status_code == 401


async def test_refresh_token_garbage_expired_missing_sub_bad_sub(client):
    cases = [
        "garbage",
        await security.create_refresh_token(
            {"sub": str(uuid.uuid4())}, expires_delta=timedelta(seconds=-1)
        ),
        await security.create_refresh_token({}),
        await security.create_refresh_token({"sub": "not-a-uuid"}),
        await security.create_refresh_token({"sub": str(uuid.uuid4())}),
    ]
    for token in cases:
        assert (
            await client.post("/auth/refresh-token", json={"refresh_token": token})
        ).status_code == 401


async def test_refresh_token_locked_user_is_403(client, make_user):
    u = await make_user(is_locked=True)
    refresh = await security.create_refresh_token({"sub": str(u.id)})
    assert (
        await client.post("/auth/refresh-token", json={"refresh_token": refresh})
    ).status_code == 403


GENERIC = "If the account exists, a password reset code has been sent."


async def test_forgot_password_unknown_number_returns_same_generic_message_and_sends_nothing(
    client, fake_sms
):
    r = await client.post(
        "/auth/forgot-password", json={"phone_number": "+263000000000"}
    )
    assert r.status_code == 200 and r.json()["message"] == GENERIC
    assert fake_sms.sent == []


async def test_forgot_password_known_number_sends_sms_with_code(
    client, make_user, fake_sms
):
    u = await make_user()
    r = await client.post(
        "/auth/forgot-password", json={"phone_number": u.phone_number}
    )
    assert r.status_code == 200 and r.json()["message"] == GENERIC
    assert len(fake_sms.sent) == 1
    sms = fake_sms.sent[0]
    assert sms.phone_number == u.phone_number and sms.alert_type == "password_reset"
    assert any(
        part.isdigit() and len(part) == 6
        for part in sms.message.replace(".", " ").split()
    )


async def test_forgot_password_second_request_within_cooldown_sends_no_second_sms(
    client, make_user, fake_sms
):
    u = await make_user()
    for _ in range(2):
        assert (
            await client.post(
                "/auth/forgot-password", json={"phone_number": u.phone_number}
            )
        ).status_code == 200
    assert len(fake_sms.sent) == 1


@pytest.mark.parametrize(
    "payload", [{}, {"phone_number": "123"}, {"phone_number": "1" * 21}]
)
async def test_forgot_password_validation(client, payload):
    assert (await client.post("/auth/forgot-password", json=payload)).status_code == 422


async def _request_code(client, user, fake_sms):
    await client.post("/auth/forgot-password", json={"phone_number": user.phone_number})
    return [
        p
        for p in fake_sms.sent[-1].message.replace(".", " ").split()
        if p.isdigit() and len(p) == 6
    ][0]


async def test_full_password_reset_flow(client, make_user, fake_sms):
    u = await make_user(must_change_password=True)
    code = await _request_code(client, u, fake_sms)

    v = await client.post(
        "/auth/verify-reset-otp",
        json={"phone_number": u.phone_number, "otp_code": code},
    )
    assert v.status_code == 200 and v.json()["token_type"] == "password_reset"
    reset_token = v.json()["reset_token"]

    r = await client.post(
        "/auth/reset-password",
        headers={"Authorization": f"Bearer {reset_token}"},
        json={"reset_token": reset_token, "new_password": "ResetPass789"},
    )
    assert r.status_code == 200

    login = await client.post("/auth/login", data=form(u.phone_number, "ResetPass789"))
    assert login.status_code == 200 and login.json()["must_change_password"] is False
    assert (
        await client.post("/auth/login", data=form(u.phone_number, "Password123"))
    ).status_code == 401


async def test_verify_reset_otp_wrong_code_is_400(client, make_user, make_otp):
    u = await make_user()
    await make_otp(u.id, code_hash=await hash_password_reset_otp("123456"))
    r = await client.post(
        "/auth/verify-reset-otp",
        json={"phone_number": u.phone_number, "otp_code": "654321"},
    )
    assert r.status_code == 400


async def test_verify_reset_otp_locks_after_three_wrong_codes(
    client, make_user, make_otp
):
    u = await make_user()
    await make_otp(u.id, code_hash=await hash_password_reset_otp("123456"))
    statuses = [
        (
            await client.post(
                "/auth/verify-reset-otp",
                json={"phone_number": u.phone_number, "otp_code": "000000"},
            )
        ).status_code
        for _ in range(3)
    ]
    assert statuses == [400, 400, 429]
    right = await client.post(
        "/auth/verify-reset-otp",
        json={"phone_number": u.phone_number, "otp_code": "123456"},
    )
    assert right.status_code == 429


@pytest.mark.parametrize("code", ["12345", "1234567", "abcdef"])
async def test_verify_reset_otp_format_validation(client, code):
    r = await client.post(
        "/auth/verify-reset-otp",
        json={"phone_number": "+263771234567", "otp_code": code},
    )
    assert r.status_code == 422


async def test_reset_password_rejects_access_token(client, make_user, auth_headers):
    u = await make_user()
    r = await client.post(
        "/auth/reset-password",
        headers=await auth_headers(u),
        json={"reset_token": "x", "new_password": "ResetPass789"},
    )
    assert r.status_code == 401


async def test_reset_password_without_bearer_is_rejected(client):
    r = await client.post(
        "/auth/reset-password",
        json={"reset_token": "x", "new_password": "ResetPass789"},
    )
    assert r.status_code in (401, 403)


async def test_reset_password_weak_password_is_422(client, make_user):
    u = await make_user()
    token = await security.create_password_reset_token(str(u.id))
    r = await client.post(
        "/auth/reset-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"reset_token": token, "new_password": "short"},
    )
    assert r.status_code == 422
