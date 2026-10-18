import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.user import User, UserType
from ivhuRedu.schemas.user import UserCreate, UserUpdate
from ivhuRedu.services import user as user_service
from ivhuRedu.services.security import verify_password


def new_user(**overrides):
    data = dict(
        first_name="Tendai", last_name="Moyo", phone_number="+263771230000"
    )
    data.update(overrides)
    return UserCreate(**data)


async def test_get_user_returns_user(make_user, session):
    u = await make_user()
    assert (await user_service.get_user(session, u.id)).id == u.id


async def test_get_user_unknown_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await user_service.get_user(session, uuid.uuid4())
    assert exc.value.status_code == 404


async def test_list_users(make_user, session):
    assert await user_service.list_users(session) == []
    await make_user()
    await make_user()
    assert len(await user_service.list_users(session)) == 2


async def test_create_supervisor_with_password_hashes_and_flags_change(session):
    created = await user_service.create_user(
        session, new_user(password="Secret1234"), UserType.SUPERVISOR
    )
    assert created.user_type is UserType.SUPERVISOR
    assert created.hashed_password != "Secret1234"
    assert await verify_password("Secret1234", created.hashed_password)
    assert created.must_change_password is True


async def test_create_supervisor_without_password_is_400(session):
    with pytest.raises(HTTPException) as exc:
        await user_service.create_user(session, new_user(), UserType.SUPERVISOR)
    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "user_type", [UserType.FARMER, UserType.EXTENSION_WORKER, UserType.ADMIN]
)
async def test_create_user_without_password_has_no_hash(session, user_type):
    created = await user_service.create_user(session, new_user(), user_type)
    assert created.hashed_password is None
    assert created.must_change_password is False
    assert created.user_type is user_type


async def test_create_user_duplicate_phone_is_409(make_user, session):
    await make_user(phone="+263771230000")
    with pytest.raises(HTTPException) as exc:
        await user_service.create_user(session, new_user(), UserType.FARMER)
    assert exc.value.status_code == 409
    assert "phone number" in exc.value.detail


async def test_create_user_duplicate_email_is_409(make_user, session):
    await make_user(email="a@b.co")
    with pytest.raises(HTTPException) as exc:
        await user_service.create_user(
            session, new_user(email="a@b.co"), UserType.FARMER
        )
    assert exc.value.status_code == 409
    assert "email" in exc.value.detail


async def test_create_user_integrity_error_becomes_409(session, monkeypatch):
    async def boom(*args, **kwargs):
        raise IntegrityError("stmt", {}, Exception("race"))

    monkeypatch.setattr(user_service.user_repository, "create", boom)
    with pytest.raises(HTTPException) as exc:
        await user_service.create_user(session, new_user(), UserType.FARMER)
    assert exc.value.status_code == 409
    assert exc.value.detail == "User could not be created"


async def test_update_user_changes_only_given_fields(make_user, session):
    u = await make_user()
    updated = await user_service.update_user(
        session, u.id, UserUpdate(first_name="Changed")
    )
    assert updated.first_name == "Changed"
    assert updated.last_name == u.last_name
    assert updated.phone_number == u.phone_number


async def test_update_user_password_rehashes_and_forces_change(make_user, session):
    u = await make_user(must_change_password=False)
    updated = await user_service.update_user(
        session, u.id, UserUpdate(password="BrandNew456")
    )
    assert await verify_password("BrandNew456", updated.hashed_password)
    assert updated.must_change_password is True


async def test_update_user_unknown_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await user_service.update_user(
            session, uuid.uuid4(), UserUpdate(first_name="x")
        )
    assert exc.value.status_code == 404


async def test_update_user_to_taken_phone_is_409(make_user, session):
    await make_user(phone="+263770000001")
    other = await make_user(phone="+263770000002")
    with pytest.raises(HTTPException) as exc:
        await user_service.update_user(
            session, other.id, UserUpdate(phone_number="+263770000001")
        )
    assert exc.value.status_code == 409


async def test_delete_user_unknown_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await user_service.delete_user(session, uuid.uuid4())
    assert exc.value.status_code == 404


async def test_delete_user_removes_user(make_user, session):
    u = await make_user()
    result = await user_service.delete_user(session, u.id)
    assert result == {"message": "User deleted successfully"}
    remaining = await session.execute(select(User).where(User.id == u.id))
    assert remaining.first() is None


async def test_delete_farmer_user_cascades_to_farmer_profile(make_farmer, session):
    user, farmer = await make_farmer()
    await user_service.delete_user(session, user.id)
    rows = await session.execute(
        select(Farmer).where(Farmer.farmer_id == farmer.farmer_id)
    )
    assert rows.first() is None


async def test_delete_user_with_worker_profile_is_409(make_worker, session):
    user, _ = await make_worker()
    with pytest.raises(HTTPException) as exc:
        await user_service.delete_user(session, user.id)
    assert exc.value.status_code == 409
    remaining = await session.execute(select(User).where(User.id == user.id))
    assert remaining.first() is not None


async def test_delete_user_integrity_error_becomes_409(
    make_user, session, monkeypatch
):
    u = await make_user()

    async def boom(*args, **kwargs):
        raise IntegrityError("stmt", {}, Exception("fk"))

    monkeypatch.setattr(user_service.user_repository, "delete", boom)
    with pytest.raises(HTTPException) as exc:
        await user_service.delete_user(session, u.id)
    assert exc.value.status_code == 409
