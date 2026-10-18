from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from ivhuRedu.repositories.password_reset_otp import (
    password_reset_otp_repository as otp_repo,
)
from ivhuRedu.services import password_reset_otp as svc
from ivhuRedu.services.security import (
    hash_password_reset_otp,
    verify_password_reset_otp,
)


def utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def fixed_otp(monkeypatch):
    monkeypatch.setattr(svc, "generate_password_reset_otp", lambda: "123456")


async def test_request_unknown_phone_returns_none_pair(session):
    assert await svc.request_password_reset(session, "+263000000000") == (None, None)


async def test_request_creates_hashed_otp_and_returns_plain_code(make_user, session):
    u = await make_user()
    otp, phone = await svc.request_password_reset(session, u.phone_number)
    assert (otp, phone) == ("123456", u.phone_number)
    record = await otp_repo.get_latest_by_user_id(session, u.id)
    assert record.code_hash != "123456"
    assert await verify_password_reset_otp("123456", record.code_hash)
    assert record.attempts == 0 and record.locked_until is None
    assert timedelta(minutes=4) < record.expires_at - utcnow() <= timedelta(minutes=5)


async def test_request_within_cooldown_is_silently_ignored(make_user, session):
    u = await make_user()
    await svc.request_password_reset(session, u.phone_number)
    assert await svc.request_password_reset(session, u.phone_number) == (None, None)
    assert await otp_repo.count_recent_by_user_id(session, u.id) == 1


async def test_request_after_cooldown_creates_new_otp(make_user, make_otp, session):
    u = await make_user()
    await make_otp(
        u.id,
        created_at=utcnow() - timedelta(seconds=svc.OTP_SEND_COOLDOWN_SECONDS + 30),
    )
    assert (await svc.request_password_reset(session, u.phone_number))[0] == "123456"


async def test_request_hourly_limit_blocks_fourth_otp(make_user, make_otp, session):
    u = await make_user()
    for minutes in (10, 20, 30):
        await make_otp(u.id, created_at=utcnow() - timedelta(minutes=minutes))
    assert await svc.request_password_reset(session, u.phone_number) == (None, None)


async def test_request_old_otps_do_not_count_toward_hourly_limit(
    make_user, make_otp, session
):
    u = await make_user()
    for minutes in (70, 80, 90):
        await make_otp(u.id, created_at=utcnow() - timedelta(minutes=minutes))
    assert (await svc.request_password_reset(session, u.phone_number))[0] == "123456"


async def test_request_blocked_while_latest_otp_is_locked(make_user, make_otp, session):
    u = await make_user()
    await make_otp(
        u.id,
        created_at=utcnow() - timedelta(minutes=5),
        locked_until=utcnow() + timedelta(minutes=10),
    )
    assert await svc.request_password_reset(session, u.phone_number) == (None, None)


async def test_request_blocked_for_locked_user_with_no_expiry(make_user, session):
    u = await make_user(is_locked=True)
    assert await svc.request_password_reset(session, u.phone_number) == (None, None)


async def test_request_blocked_for_user_locked_until_future(make_user, session):
    u = await make_user(is_locked=True, locked_until=utcnow() + timedelta(hours=1))
    assert await svc.request_password_reset(session, u.phone_number) == (None, None)


async def test_request_for_user_whose_lock_expired_is_allowed(make_user, session):
    u = await make_user(is_locked=True, locked_until=utcnow() - timedelta(hours=1))
    assert (await svc.request_password_reset(session, u.phone_number))[0] == "123456"


async def _seed_valid_otp(make_user, make_otp, code="123456", **otp_overrides):
    u = await make_user()
    await make_otp(u.id, code_hash=await hash_password_reset_otp(code), **otp_overrides)
    return u


async def test_verify_correct_code_returns_user_id_and_consumes_otp(
    make_user, make_otp, session
):
    u = await _seed_valid_otp(make_user, make_otp)
    assert (
        await svc.verify_password_reset_otp_code(session, u.phone_number, "123456")
        == u.id
    )
    assert await otp_repo.get_latest_by_user_id(session, u.id) is None


async def test_verify_code_cannot_be_reused(make_user, make_otp, session):
    u = await _seed_valid_otp(make_user, make_otp)
    await svc.verify_password_reset_otp_code(session, u.phone_number, "123456")
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, u.phone_number, "123456")
    assert exc.value.status_code == 400


async def test_verify_unknown_phone_is_400(session):
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, "+263000000000", "123456")
    assert exc.value.status_code == 400


async def test_verify_user_without_otp_is_400(make_user, session):
    u = await make_user()
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, u.phone_number, "123456")
    assert exc.value.status_code == 400


async def test_verify_expired_otp_is_400_and_deleted(make_user, make_otp, session):
    u = await _seed_valid_otp(
        make_user, make_otp, expires_at=utcnow() - timedelta(seconds=1)
    )
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, u.phone_number, "123456")
    assert exc.value.status_code == 400
    assert await otp_repo.get_latest_by_user_id(session, u.id) is None


async def test_verify_wrong_code_increments_attempts(make_user, make_otp, session):
    u = await _seed_valid_otp(make_user, make_otp)
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, u.phone_number, "000000")
    assert exc.value.status_code == 400
    assert (await otp_repo.get_latest_by_user_id(session, u.id)).attempts == 1


async def test_verify_third_wrong_code_locks_for_15_minutes(
    make_user, make_otp, session
):
    u = await _seed_valid_otp(make_user, make_otp, attempts=svc.OTP_MAX_ATTEMPTS - 1)
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, u.phone_number, "000000")
    assert exc.value.status_code == 429
    record = await otp_repo.get_latest_by_user_id(session, u.id)
    assert record.attempts == svc.OTP_MAX_ATTEMPTS
    assert (
        timedelta(minutes=14) < record.locked_until - utcnow() <= timedelta(minutes=15)
    )


async def test_verify_locked_otp_rejects_even_correct_code(
    make_user, make_otp, session
):
    u = await _seed_valid_otp(
        make_user, make_otp, locked_until=utcnow() + timedelta(minutes=10)
    )
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, u.phone_number, "123456")
    assert exc.value.status_code == 429


async def test_verify_locked_user_is_403(make_user, make_otp, session):
    u = await make_user(is_locked=True)
    await make_otp(u.id, code_hash=await hash_password_reset_otp("123456"))
    with pytest.raises(HTTPException) as exc:
        await svc.verify_password_reset_otp_code(session, u.phone_number, "123456")
    assert exc.value.status_code == 403


async def test_otp_repo_latest_returns_newest(make_user, make_otp, session):
    u = await make_user()
    await make_otp(u.id, code_hash="old", created_at=utcnow() - timedelta(minutes=30))
    await make_otp(u.id, code_hash="new", created_at=utcnow() - timedelta(minutes=1))
    assert (await otp_repo.get_latest_by_user_id(session, u.id)).code_hash == "new"


async def test_otp_repo_active_excludes_expired(make_user, make_otp, session):
    u = await make_user()
    await make_otp(u.id, expires_at=utcnow() - timedelta(minutes=1))
    assert await otp_repo.get_active_by_user_id(session, u.id) is None
    await make_otp(u.id, expires_at=utcnow() + timedelta(minutes=1))
    assert await otp_repo.get_active_by_user_id(session, u.id) is not None


async def test_otp_repo_delete_by_user_id_only_removes_that_users_otps(
    make_user, make_otp, session
):
    a, b = await make_user(), await make_user()
    await make_otp(a.id)
    await make_otp(b.id)
    await otp_repo.delete_by_user_id(session, a.id)
    assert await otp_repo.get_latest_by_user_id(session, a.id) is None
    assert await otp_repo.get_latest_by_user_id(session, b.id) is not None


async def test_otp_repo_get_by_id_and_missing(make_user, make_otp, session):
    import uuid

    otp = await make_otp((await make_user()).id)
    assert (await otp_repo.get(session, otp.id)).id == otp.id
    assert await otp_repo.get(session, uuid.uuid4()) is None
