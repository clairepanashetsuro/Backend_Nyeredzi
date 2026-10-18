import uuid

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError, StatementError

from database import Base
from ivhuRedu.models.extension_worker import ExtensionWorker, WorkerAvailabilityStatus
from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.farmer_request import FarmerRequest, RequestStatus, RequestType
from ivhuRedu.models.field_image import FieldImage
from ivhuRedu.models.field_report import FieldReport, IssueType, StatusEnum, SyncStatus
from ivhuRedu.models.location import Location
from ivhuRedu.models.password_reset_otp import PasswordResetOTP
from ivhuRedu.models.user import User, UserType
from ivhuRedu.models.ussd import USSDSession


def test_expected_tables_are_registered():
    assert set(Base.metadata.tables) == {
        "users",
        "farmers",
        "extension_workers",
        "location",
        "farmer_requests",
        "field_reports",
        "field_images",
        "password_reset_otps",
        "ussd_sessions",
    }


async def test_foreign_keys_are_enforced_on_sqlite(session):
    assert (await session.execute(text("PRAGMA foreign_keys"))).scalar() == 1


async def test_user_defaults_are_applied(make_user, session):
    u = await make_user(must_change_password=True)
    row = (await session.execute(select(User).where(User.id == u.id))).scalar_one()
    assert (
        row.is_locked is False
        and row.created_at is not None
        and row.updated_at is not None
    )
    assert row.must_change_password is True and row.locked_until is None


async def test_user_model_default_for_must_change_password_is_true(session):
    u = User(
        first_name="A",
        last_name="B",
        phone_number="+263700000001",
        user_type=UserType.FARMER,
    )
    session.add(u)
    await session.commit()
    assert u.must_change_password is True


async def test_user_phone_number_must_be_unique(make_user):
    await make_user(phone="+263771111111")
    with pytest.raises(IntegrityError):
        await make_user(phone="+263771111111")


async def test_user_email_must_be_unique_but_multiple_nulls_allowed(make_user):
    await make_user(email=None)
    await make_user(email=None)
    await make_user(email="a@b.co")
    with pytest.raises(IntegrityError):
        await make_user(email="a@b.co")


@pytest.mark.parametrize(
    "missing", ["first_name", "last_name", "phone_number", "user_type"]
)
async def test_user_required_columns_reject_null(session, missing):
    data = dict(
        first_name="A",
        last_name="B",
        phone_number="+263700000002",
        user_type=UserType.ADMIN,
    )
    data[missing] = None
    session.add(User(**data))
    with pytest.raises((IntegrityError, StatementError)):
        await session.commit()


async def test_user_type_is_stored_as_lowercase_value(make_user, session):
    u = await make_user(user_type=UserType.EXTENSION_WORKER)
    raw = (
        await session.execute(
            text("SELECT user_type FROM users WHERE id = :i"), {"i": u.id.hex}
        )
    ).scalar()
    assert raw == "extension_worker"


async def test_unknown_user_type_cannot_be_read_back(session):
    session.add(
        User(
            first_name="A",
            last_name="B",
            phone_number="+263700000003",
            user_type="wizard",
        )
    )
    await session.commit()
    session.expunge_all()
    with pytest.raises(LookupError):
        await session.execute(select(User).where(User.phone_number == "+263700000003"))


async def test_user_unicode_and_sql_injection_like_names_stored_verbatim(session):
    name = "Robert'); DROP TABLE users;--"
    session.add(
        User(
            first_name=name,
            last_name="Ñandú 密码",
            phone_number="+263700000004",
            user_type=UserType.ADMIN,
        )
    )
    await session.commit()
    row = (
        await session.execute(select(User).where(User.phone_number == "+263700000004"))
    ).scalar_one()
    assert row.first_name == name and row.last_name == "Ñandú 密码"
    assert (await session.execute(select(User))).scalars().all()


async def test_farmer_requires_existing_user_and_location(session):
    session.add(Farmer(user_id=uuid.uuid4(), ward_name="W", location_id=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_farmer_user_id_is_unique(make_farmer, session):
    user, farmer = await make_farmer()
    session.add(Farmer(user_id=user.id, ward_name="W", location_id=farmer.location_id))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_location_delete_is_restricted_while_farmer_references_it(
    make_farmer, session
):
    _, farmer = await make_farmer()
    with pytest.raises(IntegrityError):
        await session.execute(
            delete(Location).where(Location.location_id == farmer.location_id)
        )
        await session.commit()


async def test_deleting_user_cascades_to_farmer_row(make_farmer, session):
    user, farmer = await make_farmer()
    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
    assert (
        await session.execute(
            select(Farmer).where(Farmer.farmer_id == farmer.farmer_id)
        )
    ).first() is None


async def test_farmer_primary_crop_is_optional(make_user, make_location, session):
    user = await make_user(user_type=UserType.FARMER)
    loc = await make_location()
    session.add(Farmer(user_id=user.id, ward_name="W", location_id=loc.location_id))
    await session.commit()


async def test_worker_default_availability_is_available(make_worker, session):
    _, worker = await make_worker()
    row = (
        await session.execute(
            select(ExtensionWorker).where(ExtensionWorker.worker_id == worker.worker_id)
        )
    ).scalar_one()
    assert row.availability_status is WorkerAvailabilityStatus.AVAILABLE


@pytest.mark.parametrize("status", list(WorkerAvailabilityStatus))
async def test_worker_accepts_all_availability_statuses(make_worker, session, status):
    _, worker = await make_worker()
    worker_row = await session.get(ExtensionWorker, worker.worker_id)
    worker_row.availability_status = status
    await session.commit()
    assert (
        await session.get(ExtensionWorker, worker.worker_id)
    ).availability_status is status


async def test_worker_requires_pincode_hash(make_user, make_location, session):
    user = await make_user(user_type=UserType.EXTENSION_WORKER)
    loc = await make_location()
    session.add(
        ExtensionWorker(
            user_id=user.id, assigned_ward_name="W", location_id=loc.location_id
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_farmer_request_defaults(session):
    req = FarmerRequest(
        phone_number="+263771234567", request_type=RequestType.VISIT_REQUEST
    )
    session.add(req)
    await session.commit()
    assert req.status is RequestStatus.PENDING
    assert req.sync_status == "PENDING_SYNC"
    assert req.created_at is not None


async def test_farmer_request_requires_phone_and_type(session):
    session.add(FarmerRequest(request_type=RequestType.VISIT_REQUEST))
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.parametrize("rtype", list(RequestType))
async def test_farmer_request_accepts_all_request_types(session, rtype):
    session.add(FarmerRequest(phone_number="+263771234567", request_type=rtype))
    await session.commit()


async def test_field_report_defaults_and_images_cascade(make_worker, session):
    _, worker = await make_worker()
    report = FieldReport(worker_id=worker.worker_id, issue_type=IssueType.PEST_OUTBREAK)
    session.add(report)
    await session.commit()
    assert (
        report.status is StatusEnum.PENDING
        and report.sync_status is SyncStatus.PENDING_SYNC
    )

    session.add(
        FieldImage(report_id=report.report_id, image_url="secure_storage/a.enc")
    )
    await session.commit()
    await session.execute(
        delete(FieldReport).where(FieldReport.report_id == report.report_id)
    )
    await session.commit()
    assert (await session.execute(select(FieldImage))).first() is None


async def test_field_report_requires_worker(session):
    session.add(FieldReport())
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_field_image_requires_existing_report(session):
    session.add(FieldImage(report_id=uuid.uuid4(), image_url="x"))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_deleting_user_cascades_to_password_reset_otps(
    make_user, make_otp, session
):
    user = await make_user()
    await make_otp(user.id)
    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
    assert (await session.execute(select(PasswordResetOTP))).first() is None


async def test_otp_requires_existing_user(session):
    from datetime import datetime, timezone

    session.add(
        PasswordResetOTP(
            user_id=uuid.uuid4(), code_hash="h", expires_at=datetime.now(timezone.utc)
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_otp_attempts_default_to_zero(make_user, session):
    from datetime import datetime, timezone

    user = await make_user()
    otp = PasswordResetOTP(
        user_id=user.id, code_hash="h", expires_at=datetime.now(timezone.utc)
    )
    session.add(otp)
    await session.commit()
    assert otp.attempts == 0


async def test_ussd_session_id_is_unique(session):
    session.add(USSDSession(session_id="s1", phone_number="+263771234567"))
    await session.commit()
    session.add(USSDSession(session_id="s1", phone_number="+263772222222"))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_location_requires_coordinates_and_address(session):
    session.add(Location(address="x"))
    with pytest.raises(IntegrityError):
        await session.commit()
