import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from ivhuRedu.models.extension_worker import ExtensionWorker, WorkerAvailabilityStatus
from ivhuRedu.models.field_report import FieldReport
from ivhuRedu.models.user import User, UserType
from ivhuRedu.schemas.extension_worker import ExtensionWorkerCreate
from ivhuRedu.services import extension_worker as svc
from ivhuRedu.services.security import verify_password


def payload(location_id, **overrides):
    data = dict(
        first_name="Farai",
        last_name="Dube",
        phone_number="+263775550000",
        email="farai@example.com",
        password="Password123",
        ussd_pincode="1234",
        assigned_ward_name="Ward 5",
        location_id=location_id,
    )
    data.update(overrides)
    return ExtensionWorkerCreate(**data)


async def test_create_extension_worker_creates_user_and_profile(
    session, make_location
):
    loc = await make_location()
    worker = await svc.create_extension_worker(session, payload(loc.location_id))
    assert worker.assigned_ward_name == "Ward 5"
    assert worker.availability_status is WorkerAvailabilityStatus.AVAILABLE
    assert worker.user.user_type is UserType.EXTENSION_WORKER
    assert worker.user.must_change_password is True
    assert await verify_password("Password123", worker.user.hashed_password)
    assert await verify_password("1234", worker.hashed_ussd_pincode)
    assert worker.hashed_ussd_pincode != "1234"


async def test_create_extension_worker_email_is_optional(session, make_location):
    loc = await make_location()
    worker = await svc.create_extension_worker(
        session, payload(loc.location_id, email=None)
    )
    assert worker.user.email is None


async def test_create_extension_worker_duplicate_phone_is_409(
    session, make_user, make_location
):
    loc = await make_location()
    await make_user(phone="+263775550000")
    with pytest.raises(HTTPException) as exc:
        await svc.create_extension_worker(session, payload(loc.location_id))
    assert exc.value.status_code == 409
    assert "phone number" in exc.value.detail


async def test_create_extension_worker_duplicate_email_is_409(
    session, make_user, make_location
):
    loc = await make_location()
    await make_user(email="farai@example.com")
    with pytest.raises(HTTPException) as exc:
        await svc.create_extension_worker(session, payload(loc.location_id))
    assert exc.value.status_code == 409
    assert "email" in exc.value.detail


async def test_create_extension_worker_unknown_location_is_409_and_leaves_no_user(
    session,
):
    with pytest.raises(HTTPException) as exc:
        await svc.create_extension_worker(session, payload(uuid.uuid4()))
    assert exc.value.status_code == 409
    assert (await session.execute(select(User))).first() is None


@pytest.mark.parametrize("status", list(WorkerAvailabilityStatus))
async def test_update_worker_status_sets_each_status(session, make_worker, status):
    _, worker = await make_worker()
    updated = await svc.update_worker_status(session, worker.worker_id, status)
    assert updated.availability_status is status


async def test_update_worker_status_unknown_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await svc.update_worker_status(
            session, uuid.uuid4(), WorkerAvailabilityStatus.AVAILABLE
        )
    assert exc.value.status_code == 404


async def test_get_extension_worker_loads_user(session, make_worker):
    user, worker = await make_worker()
    found = await svc.get_extension_worker(session, worker.worker_id)
    assert found.user.id == user.id


async def test_get_extension_worker_unknown_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await svc.get_extension_worker(session, uuid.uuid4())
    assert exc.value.status_code == 404


async def test_worker_can_update_own_personal_details(session, make_worker):
    user, worker = await make_worker()
    updated = await svc.update_extension_worker(
        session, worker.worker_id, {"first_name": "Self", "last_name": "Edited"}, user
    )
    assert updated.user.first_name == "Self"
    assert updated.user.last_name == "Edited"


async def test_worker_cannot_update_another_worker(session, make_worker):
    _, target = await make_worker()
    other_user, _ = await make_worker()
    with pytest.raises(HTTPException) as exc:
        await svc.update_extension_worker(
            session, target.worker_id, {"first_name": "Hacked"}, other_user
        )
    assert exc.value.status_code == 403


async def test_farmer_cannot_update_worker(session, make_worker, make_user):
    _, worker = await make_worker()
    farmer = await make_user(user_type=UserType.FARMER)
    with pytest.raises(HTTPException) as exc:
        await svc.update_extension_worker(
            session, worker.worker_id, {"first_name": "x"}, farmer
        )
    assert exc.value.status_code == 403


@pytest.mark.parametrize("field", ["assigned_ward_name", "location_id"])
async def test_worker_cannot_change_own_restricted_fields(
    session, make_worker, make_location, field
):
    user, worker = await make_worker()
    loc = await make_location()
    value = "New Ward" if field == "assigned_ward_name" else loc.location_id
    with pytest.raises(HTTPException) as exc:
        await svc.update_extension_worker(
            session, worker.worker_id, {field: value}, user
        )
    assert exc.value.status_code == 403
    assert field in exc.value.detail


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.ADMIN])
async def test_privileged_user_can_change_ward_and_location(
    session, make_worker, make_user, make_location, role
):
    _, worker = await make_worker()
    caller = await make_user(user_type=role)
    loc = await make_location(address="Kwekwe")
    updated = await svc.update_extension_worker(
        session,
        worker.worker_id,
        {"assigned_ward_name": "Ward 12", "location_id": loc.location_id},
        caller,
    )
    assert updated.assigned_ward_name == "Ward 12"
    assert updated.location_id == loc.location_id


async def test_update_password_is_hashed_and_clears_change_flag(
    session, make_worker
):
    user, worker = await make_worker(must_change_password=True)
    updated = await svc.update_extension_worker(
        session, worker.worker_id, {"password": "BrandNew456"}, user
    )
    assert await verify_password("BrandNew456", updated.user.hashed_password)
    assert updated.user.must_change_password is False


async def test_update_ussd_pincode_is_hashed(session, make_worker):
    user, worker = await make_worker()
    updated = await svc.update_extension_worker(
        session, worker.worker_id, {"ussd_pincode": "9876"}, user
    )
    assert await verify_password("9876", updated.hashed_ussd_pincode)


async def test_update_availability_status_is_rejected(session, make_worker):
    user, worker = await make_worker()
    with pytest.raises(HTTPException) as exc:
        await svc.update_extension_worker(
            session, worker.worker_id, {"availability_status": "busy"}, user
        )
    assert exc.value.status_code == 403
    assert "status endpoint" in exc.value.detail


async def test_update_unknown_keys_are_ignored(session, make_worker):
    user, worker = await make_worker()
    updated = await svc.update_extension_worker(
        session, worker.worker_id, {"user_type": "admin", "is_locked": True}, user
    )
    assert updated.user.user_type is UserType.EXTENSION_WORKER
    assert updated.user.is_locked is False


async def test_update_to_taken_phone_is_409(session, make_worker, make_user):
    await make_user(phone="+263776660000")
    user, worker = await make_worker()
    with pytest.raises(HTTPException) as exc:
        await svc.update_extension_worker(
            session, worker.worker_id, {"phone_number": "+263776660000"}, user
        )
    assert exc.value.status_code == 409


async def test_update_unknown_worker_is_404(session, make_user):
    admin = await make_user()
    with pytest.raises(HTTPException) as exc:
        await svc.update_extension_worker(
            session, uuid.uuid4(), {"first_name": "x"}, admin
        )
    assert exc.value.status_code == 404


async def test_delete_extension_worker_removes_profile_and_user(
    session, make_worker
):
    user, worker = await make_worker()
    result = await svc.delete_extension_worker(session, worker.worker_id)
    assert result == {"message": "Extension worker deleted successfully."}
    assert (
        await session.execute(
            select(ExtensionWorker).where(ExtensionWorker.worker_id == worker.worker_id)
        )
    ).first() is None
    assert (await session.execute(select(User).where(User.id == user.id))).first() is None


async def test_delete_extension_worker_unknown_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await svc.delete_extension_worker(session, uuid.uuid4())
    assert exc.value.status_code == 404


async def test_delete_worker_with_field_reports_is_409(
    session, session_factory, make_worker
):
    _, worker = await make_worker()
    async with session_factory() as s:
        s.add(FieldReport(worker_id=worker.worker_id))
        await s.commit()
    with pytest.raises(HTTPException) as exc:
        await svc.delete_extension_worker(session, worker.worker_id)
    assert exc.value.status_code == 409
