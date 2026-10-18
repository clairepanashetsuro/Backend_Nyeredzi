import pytest
from fastapi import HTTPException

from ivhuRedu.models.user import UserType
from ivhuRedu.services import auth as auth_service
from ivhuRedu.services.security import decode_token, verify_password


async def test_authenticate_user_success(make_user, session):
    u = await make_user(password="Password123")
    assert (
        await auth_service.authenticate_user(session, u.phone_number, "Password123")
    ).id == u.id


@pytest.mark.parametrize(
    "phone, password",
    [("+263000000000", "Password123"), ("", ""), ("' OR 1=1 --", "x")],
)
async def test_authenticate_user_unknown_phone_is_401(session, phone, password):
    with pytest.raises(HTTPException) as exc:
        await auth_service.authenticate_user(session, phone, password)
    assert exc.value.status_code == 401


async def test_authenticate_user_wrong_password_is_401_with_generic_message(
    make_user, session
):
    u = await make_user()
    with pytest.raises(HTTPException) as exc:
        await auth_service.authenticate_user(session, u.phone_number, "WrongPassword")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Incorrect phone number or password"
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


async def test_authenticate_user_without_password_is_401(make_user, session):
    u = await make_user(password=None)
    with pytest.raises(HTTPException) as exc:
        await auth_service.authenticate_user(session, u.phone_number, "anything")
    assert exc.value.status_code == 401


async def test_unknown_and_wrong_password_errors_are_indistinguishable(
    make_user, session
):
    u = await make_user()
    with pytest.raises(HTTPException) as e1:
        await auth_service.authenticate_user(session, "+263999999999", "x")
    with pytest.raises(HTTPException) as e2:
        await auth_service.authenticate_user(session, u.phone_number, "x")
    assert e1.value.detail == e2.value.detail


@pytest.mark.parametrize("role", [UserType.ADMIN, UserType.SUPERVISOR])
async def test_login_admin_and_supervisor_get_access_and_refresh_but_no_offline(
    make_user, session, role
):
    u = await make_user(user_type=role, must_change_password=True)
    result = await auth_service.login(session, u.phone_number, "Password123")
    assert result["role"] == role.value and result["token_type"] == "bearer"
    assert result["offline_token"] is None and result["worker_id"] is None
    assert result["must_change_password"] is True
    assert (await decode_token(result["access_token"]))["sub"] == str(u.id)
    assert (await decode_token(result["refresh_token"]))["token_type"] == "refresh"


async def test_login_extension_worker_gets_offline_token_and_worker_id(
    make_worker, session
):
    user, worker = await make_worker()
    result = await auth_service.login(session, user.phone_number, "Password123")
    assert result["worker_id"] == str(worker.worker_id)
    assert (await decode_token(result["offline_token"]))["token_type"] == "offline"


async def test_login_extension_worker_without_profile_is_403(make_user, session):
    u = await make_user(user_type=UserType.EXTENSION_WORKER)
    with pytest.raises(HTTPException) as exc:
        await auth_service.login(session, u.phone_number, "Password123")
    assert exc.value.status_code == 403
    assert "profile not found" in exc.value.detail


async def test_login_farmer_is_forbidden_and_pointed_to_ussd(make_user, session):
    u = await make_user(user_type=UserType.FARMER)
    with pytest.raises(HTTPException) as exc:
        await auth_service.login(session, u.phone_number, "Password123")
    assert exc.value.status_code == 403 and "USSD" in exc.value.detail


async def test_login_locked_account_is_forbidden(make_user, session):
    u = await make_user(is_locked=True)
    with pytest.raises(HTTPException) as exc:
        await auth_service.login(session, u.phone_number, "Password123")
    assert exc.value.status_code == 403 and exc.value.detail == "Account locked."


async def test_login_locked_account_with_wrong_password_reports_401_not_locked(
    make_user, session
):
    u = await make_user(is_locked=True)
    with pytest.raises(HTTPException) as exc:
        await auth_service.login(session, u.phone_number, "bad")
    assert exc.value.status_code == 401


async def test_login_token_claims_contain_role(make_user, session):
    u = await make_user(user_type=UserType.SUPERVISOR)
    result = await auth_service.login(session, u.phone_number, "Password123")
    assert (await decode_token(result["access_token"]))["role"] == "supervisor"


async def test_change_password_success_updates_hash_and_clears_flag(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    u = await make_user(must_change_password=True)
    user = await user_repository.get(session, u.id)
    result = await auth_service.change_password(
        session, user, "Password123", "NewPassword456"
    )
    assert result == {"message": "Password changed successfully."}
    assert user.must_change_password is False
    assert await verify_password("NewPassword456", user.hashed_password)
    assert not await verify_password("Password123", user.hashed_password)


async def test_change_password_wrong_old_password_is_400(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    user = await user_repository.get(session, (await make_user()).id)
    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(session, user, "wrong", "NewPassword456")
    assert (
        exc.value.status_code == 400
        and "Incorrect current password" in exc.value.detail
    )


async def test_change_password_same_as_old_is_400(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    user = await user_repository.get(session, (await make_user()).id)
    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(session, user, "Password123", "Password123")
    assert exc.value.status_code == 400 and "same" in exc.value.detail


async def test_change_password_account_without_password_is_400(make_user, session):
    from ivhuRedu.repositories.user import user_repository

    user = await user_repository.get(session, (await make_user(password=None)).id)
    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(session, user, "x", "NewPassword456")
    assert exc.value.status_code == 400
