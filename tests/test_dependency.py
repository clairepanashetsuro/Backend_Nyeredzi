import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import dependency
from ivhuRedu.models.user import UserType
from ivhuRedu.services import security


async def _token(kind, user_id, **extra):
    data = {"sub": str(user_id), **extra}
    return await {
        "access": security.create_access_token,
        "refresh": security.create_refresh_token,
        "offline": security.create_offline_token,
    }[kind](data)


async def test_get_current_user_with_valid_access_token(make_user, session):
    u = await make_user()
    user = await dependency.get_current_user(await _token("access", u.id), session)
    assert user.id == u.id


async def test_get_current_user_rejects_garbage_token(session):
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user("garbage", session)
    assert exc.value.status_code == 401 and exc.value.headers == {
        "WWW-Authenticate": "Bearer"
    }


async def test_get_current_user_rejects_refresh_token(make_user, session):
    u = await make_user()
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(await _token("refresh", u.id), session)
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_password_reset_token(make_user, session):
    u = await make_user()
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(
            await security.create_password_reset_token(str(u.id)), session
        )
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_expired_token(make_user, session):
    u = await make_user()
    token = await security.create_access_token(
        {"sub": str(u.id)}, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(token, session)
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_token_without_subject(session):
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(
            await security.create_access_token({}), session
        )
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_non_uuid_subject(session):
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(
            await security.create_access_token({"sub": "not-a-uuid"}), session
        )
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_unknown_user(session):
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(await _token("access", uuid.uuid4()), session)
    assert exc.value.status_code == 401


async def test_get_current_user_locked_account_is_403(make_user, session):
    u = await make_user(is_locked=True)
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(await _token("access", u.id), session)
    assert exc.value.status_code == 403


async def test_offline_token_accepted_for_extension_worker(make_worker, session):
    user, _ = await make_worker()
    assert (
        await dependency.get_current_user(await _token("offline", user.id), session)
    ).id == user.id


@pytest.mark.parametrize("role", [UserType.ADMIN, UserType.SUPERVISOR, UserType.FARMER])
async def test_offline_token_rejected_for_non_workers(make_user, session, role):
    u = await make_user(user_type=role)
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_user(await _token("offline", u.id), session)
    assert exc.value.status_code == 401


async def test_reset_user_accepts_reset_token(make_user, session):
    u = await make_user()
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=await security.create_password_reset_token(str(u.id)),
    )
    assert (await dependency.get_current_password_reset_user(creds, session)).id == u.id


@pytest.mark.parametrize("kind", ["access", "refresh", "offline"])
async def test_reset_user_rejects_other_token_types(make_user, session, kind):
    u = await make_user()
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=await _token(kind, u.id)
    )
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_password_reset_user(creds, session)
    assert exc.value.status_code == 401


async def test_reset_user_locked_account_is_403(make_user, session):
    u = await make_user(is_locked=True)
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=await security.create_password_reset_token(str(u.id)),
    )
    with pytest.raises(HTTPException) as exc:
        await dependency.get_current_password_reset_user(creds, session)
    assert exc.value.status_code == 403


async def test_reset_user_unknown_user_and_garbage_are_401(session):
    for token in (
        "garbage",
        await security.create_password_reset_token(str(uuid.uuid4())),
        await security.create_password_reset_token("not-a-uuid"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependency.get_current_password_reset_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                session,
            )
        assert exc.value.status_code == 401


async def test_require_password_changed_blocks_flagged_user(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    u = await user_repository.get(
        session, (await make_user(must_change_password=True)).id
    )
    with pytest.raises(HTTPException) as exc:
        dependency.require_password_changed(u)
    assert exc.value.status_code == 403 and "change your password" in exc.value.detail


async def test_require_password_changed_allows_normal_user(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    u = await user_repository.get(session, (await make_user()).id)
    assert dependency.require_password_changed(u) is u


@pytest.mark.parametrize(
    "role, allowed",
    [
        (UserType.ADMIN, True),
        (UserType.SUPERVISOR, True),
        (UserType.EXTENSION_WORKER, False),
        (UserType.FARMER, False),
    ],
)
async def test_require_roles_checks_membership(make_user, session, role, allowed):
    from ivhuRedu.repositories.user import user_repository

    u = await user_repository.get(session, (await make_user(user_type=role)).id)
    checker = dependency.require_roles(UserType.ADMIN, UserType.SUPERVISOR)
    if allowed:
        assert checker(u) is u
    else:
        with pytest.raises(HTTPException) as exc:
            checker(u)
        assert exc.value.status_code == 403


async def test_require_roles_with_no_roles_denies_everyone(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    u = await user_repository.get(session, (await make_user()).id)
    with pytest.raises(HTTPException):
        dependency.require_roles()(u)


@pytest.mark.parametrize(
    "role, same_user, allowed",
    [
        (UserType.FARMER, True, True),
        (UserType.FARMER, False, False),
        (UserType.EXTENSION_WORKER, False, False),
        (UserType.ADMIN, False, True),
        (UserType.SUPERVISOR, False, True),
    ],
)
async def test_ensure_self_or_privileged(make_user, session, role, same_user, allowed):
    from ivhuRedu.repositories.user import user_repository

    u = await user_repository.get(session, (await make_user(user_type=role)).id)
    target = u.id if same_user else uuid.uuid4()
    if allowed:
        assert dependency.ensure_self_or_privileged(target, u) is None
    else:
        with pytest.raises(HTTPException) as exc:
            dependency.ensure_self_or_privileged(target, u)
        assert exc.value.status_code == 403


async def test_ensure_self_or_privileged_custom_privileged_roles(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    u = await user_repository.get(
        session, (await make_user(user_type=UserType.ADMIN)).id
    )
    with pytest.raises(HTTPException):
        dependency.ensure_self_or_privileged(
            uuid.uuid4(), u, privileged_roles=(UserType.SUPERVISOR,)
        )
