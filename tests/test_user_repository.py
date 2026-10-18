import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from ivhuRedu.models.user import UserType
from ivhuRedu.repositories.user import user_repository as repo


async def test_get_returns_user_by_id(make_user, session):
    u = await make_user()
    found = await repo.get(session, u.id)
    assert found.id == u.id and found.phone_number == u.phone_number


async def test_get_unknown_id_returns_none(session):
    assert await repo.get(session, uuid.uuid4()) is None


async def test_get_eager_loads_worker_profile(make_worker, session):
    user, worker = await make_worker()
    found = await repo.get(session, user.id)
    assert found.extension_worker.worker_id == worker.worker_id
    assert found.farmer is None


async def test_get_eager_loads_farmer_profile(make_farmer, session):
    user, farmer = await make_farmer()
    found = await repo.get(session, user.id)
    assert found.farmer.farmer_id == farmer.farmer_id


async def test_get_all_empty_database_returns_empty_list(session):
    assert await repo.get_all(session) == []


async def test_get_all_returns_every_user(make_user, session):
    for _ in range(5):
        await make_user()
    assert len(await repo.get_all(session)) == 5


async def test_get_by_phone_number_exact_match_only(make_user, session):
    u = await make_user(phone="+263771234567")
    assert (await repo.get_by_phone_number(session, "+263771234567")).id == u.id
    assert await repo.get_by_phone_number(session, "263771234567") is None
    assert await repo.get_by_phone_number(session, "") is None


async def test_get_by_phone_number_is_safe_against_injection_input(make_user, session):
    await make_user()
    assert await repo.get_by_phone_number(session, "' OR '1'='1") is None


async def test_get_by_email(make_user, session):
    u = await make_user(email="a@b.co")
    assert (await repo.get_by_email(session, "a@b.co")).id == u.id
    assert await repo.get_by_email(session, "missing@b.co") is None


async def test_get_by_user_type_filters(make_user, session):
    await make_user(user_type=UserType.ADMIN)
    await make_user(user_type=UserType.SUPERVISOR)
    await make_user(user_type=UserType.SUPERVISOR)
    assert len(await repo.get_by_user_type(session, UserType.SUPERVISOR)) == 2
    assert len(await repo.get_by_user_type(session, UserType.FARMER)) == 0


async def test_get_all_extension_workers_loads_users(make_worker, session):
    user, _ = await make_worker()
    workers = await repo.get_all_extension_workers(session)
    assert [w.user.id for w in workers] == [user.id]


async def test_get_all_farmers_loads_user_and_location(make_farmer, session):
    user, farmer = await make_farmer()
    farmers = await repo.get_all_farmers(session)
    assert farmers[0].user.id == user.id
    assert farmers[0].location.location_id == farmer.location_id


async def test_create_persists_and_returns_user(session):
    created = await repo.create(
        session,
        dict(
            first_name="A",
            last_name="B",
            phone_number="+263770000001",
            user_type=UserType.ADMIN,
            hashed_password="h",
        ),
    )
    assert created.id is not None
    assert (await repo.get(session, created.id)).phone_number == "+263770000001"


async def test_create_duplicate_phone_raises_integrity_error(make_user, session):
    await make_user(phone="+263770000002")
    with pytest.raises(IntegrityError):
        await repo.create(
            session,
            dict(
                first_name="A",
                last_name="B",
                phone_number="+263770000002",
                user_type=UserType.ADMIN,
            ),
        )


async def test_create_rolls_back_so_session_is_reusable_after_failure(
    make_user, session
):
    await make_user(phone="+263770000003")
    with pytest.raises(IntegrityError):
        await repo.create(
            session,
            dict(
                first_name="A",
                last_name="B",
                phone_number="+263770000003",
                user_type=UserType.ADMIN,
            ),
        )
    await session.rollback()
    assert len(await repo.get_all(session)) == 1


async def test_update_changes_only_given_fields(make_user, session):
    u = await make_user()
    obj = await repo.get(session, u.id)
    updated = await repo.update(
        session, obj, {"first_name": "Changed", "is_locked": True}
    )
    assert updated.first_name == "Changed" and updated.is_locked is True
    assert updated.last_name == u.last_name


async def test_update_to_existing_phone_number_raises(make_user, session):
    a = await make_user(phone="+263770000004")
    await make_user(phone="+263770000005")
    obj = await repo.get(session, a.id)
    with pytest.raises(IntegrityError):
        await repo.update(session, obj, {"phone_number": "+263770000005"})
