import uuid
import pytest
from fastapi import HTTPException

from ivhuRedu.models.field_report import IssueType, StatusEnum, SyncStatus
from ivhuRedu.models.user import UserType
from ivhuRedu.repositories.user import user_repository
from ivhuRedu.schemas.field_report import FieldReportCreate, FieldReportUpdate
from ivhuRedu.services.field_report import FieldReportService
from tests.helpers import create_report


async def loaded(session, user):
    return await user_repository.get(session, user.id)


@pytest.fixture
def service(session):
    return FieldReportService(session)


def new_report(worker_id=None, **overrides):
    data = dict(worker_id=worker_id or uuid.uuid4(), description_type="pest")
    data.update(overrides)
    return FieldReportCreate(**data)


async def test_worker_create_forces_own_worker_id_and_pending_status(
    service, session, make_worker
):
    user, worker = await make_worker()
    current = await loaded(session, user)
    report = await service.create(
        new_report(
            status=StatusEnum.COMPLETED, issue_type=IssueType.CROP_FAILURE
        ),
        current,
    )
    assert report.worker_id == worker.worker_id
    assert report.status is StatusEnum.PENDING
    assert report.timestamp_synced is None
    assert report.issue_type is IssueType.CROP_FAILURE


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
async def test_create_blank_description_type_is_422(
    service, session, make_worker, blank
):
    user, _ = await make_worker()
    with pytest.raises(HTTPException) as exc:
        await service.create(
            new_report(description_type=blank), await loaded(session, user)
        )
    assert exc.value.status_code == 422


async def test_create_by_worker_without_profile_is_403(
    service, session, make_user
):
    user = await make_user(user_type=UserType.EXTENSION_WORKER)
    with pytest.raises(HTTPException) as exc:
        await service.create(new_report(), await loaded(session, user))
    assert exc.value.status_code == 403


async def test_admin_create_keeps_supplied_worker_id(
    service, session, make_user, make_worker
):
    admin = await make_user()
    _, worker = await make_worker()
    report = await service.create(
        new_report(worker.worker_id), await loaded(session, admin)
    )
    assert report.worker_id == worker.worker_id


async def test_get_all_admin_sees_every_report(
    service, session, session_factory, make_user, make_worker
):
    admin = await make_user()
    _, first = await make_worker()
    _, second = await make_worker()
    await create_report(session_factory, first.worker_id)
    await create_report(session_factory, second.worker_id)
    assert len(await service.get_all(await loaded(session, admin))) == 2


async def test_get_all_worker_sees_only_own_reports(
    service, session, session_factory, make_worker
):
    user, own = await make_worker()
    _, other = await make_worker()
    await create_report(session_factory, own.worker_id)
    await create_report(session_factory, other.worker_id)
    reports = await service.get_all(await loaded(session, user))
    assert [r.worker_id for r in reports] == [own.worker_id]


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.FARMER])
async def test_get_all_forbidden_for_other_roles(service, session, make_user, role):
    user = await make_user(user_type=role)
    with pytest.raises(HTTPException) as exc:
        await service.get_all(await loaded(session, user))
    assert exc.value.status_code == 403


async def test_get_all_worker_without_profile_is_403(service, session, make_user):
    user = await make_user(user_type=UserType.EXTENSION_WORKER)
    with pytest.raises(HTTPException) as exc:
        await service.get_all(await loaded(session, user))
    assert exc.value.status_code == 403


async def test_get_by_id_owner_and_admin_allowed(
    service, session, session_factory, make_user, make_worker
):
    owner, worker = await make_worker()
    admin = await make_user()
    report = await create_report(session_factory, worker.worker_id)
    assert (
        await service.get_by_id(report.report_id, await loaded(session, owner))
    ).report_id == report.report_id
    assert (
        await service.get_by_id(report.report_id, await loaded(session, admin))
    ).report_id == report.report_id


async def test_get_by_id_other_worker_is_403(
    service, session, session_factory, make_worker
):
    _, worker = await make_worker()
    intruder, _ = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    with pytest.raises(HTTPException) as exc:
        await service.get_by_id(report.report_id, await loaded(session, intruder))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.FARMER])
async def test_get_by_id_forbidden_for_other_roles(
    service, session, session_factory, make_user, make_worker, role
):
    _, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    user = await make_user(user_type=role)
    with pytest.raises(HTTPException) as exc:
        await service.get_by_id(report.report_id, await loaded(session, user))
    assert exc.value.status_code == 403


async def test_get_by_id_unknown_is_404(service, session, make_user):
    admin = await make_user()
    with pytest.raises(HTTPException) as exc:
        await service.get_by_id(uuid.uuid4(), await loaded(session, admin))
    assert exc.value.status_code == 404


async def test_get_by_id_worker_without_profile_is_403(
    service, session, session_factory, make_user, make_worker
):
    _, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    profileless = await make_user(user_type=UserType.EXTENSION_WORKER)
    with pytest.raises(HTTPException) as exc:
        await service.get_by_id(report.report_id, await loaded(session, profileless))
    assert exc.value.status_code == 403


async def test_get_by_worker_admin_can_view_any_worker(
    service, session, session_factory, make_user, make_worker
):
    admin = await make_user()
    _, worker = await make_worker()
    await create_report(session_factory, worker.worker_id)
    reports = await service.get_by_worker(
        worker.worker_id, await loaded(session, admin)
    )
    assert len(reports) == 1


async def test_get_by_worker_worker_can_view_self_but_not_others(
    service, session, session_factory, make_worker
):
    user, own = await make_worker()
    _, other = await make_worker()
    await create_report(session_factory, own.worker_id)
    current = await loaded(session, user)
    assert len(await service.get_by_worker(own.worker_id, current)) == 1
    with pytest.raises(HTTPException) as exc:
        await service.get_by_worker(other.worker_id, current)
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.FARMER])
async def test_get_by_worker_forbidden_for_other_roles(
    service, session, make_user, role
):
    user = await make_user(user_type=role)
    with pytest.raises(HTTPException) as exc:
        await service.get_by_worker(uuid.uuid4(), await loaded(session, user))
    assert exc.value.status_code == 403


async def test_get_by_worker_without_profile_is_403(service, session, make_user):
    user = await make_user(user_type=UserType.EXTENSION_WORKER)
    with pytest.raises(HTTPException) as exc:
        await service.get_by_worker(uuid.uuid4(), await loaded(session, user))
    assert exc.value.status_code == 403


async def test_update_by_owner_changes_fields(
    service, session, session_factory, make_worker
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    updated = await service.update(
        report.report_id,
        FieldReportUpdate(report_details="More detail"),
        await loaded(session, user),
    )
    assert updated.report_details == "More detail"
    assert updated.worker_id == worker.worker_id


@pytest.mark.parametrize("blank", ["", "   "])
async def test_update_blank_description_type_is_422(
    service, session, session_factory, make_worker, blank
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    with pytest.raises(HTTPException) as exc:
        await service.update(
            report.report_id,
            FieldReportUpdate(description_type=blank),
            await loaded(session, user),
        )
    assert exc.value.status_code == 422


async def test_update_to_synced_stamps_time_and_completes(
    service, session, session_factory, make_worker
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    updated = await service.update(
        report.report_id,
        FieldReportUpdate(sync_status=SyncStatus.SYNCED),
        await loaded(session, user),
    )
    assert updated.sync_status is SyncStatus.SYNCED
    assert updated.status is StatusEnum.COMPLETED
    assert updated.timestamp_synced is not None
    assert updated.timestamp_synced.tzinfo is not None


async def test_update_back_to_pending_sync_clears_timestamp(
    service, session, session_factory, make_worker
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    current = await loaded(session, user)
    await service.update(
        report.report_id, FieldReportUpdate(sync_status=SyncStatus.SYNCED), current
    )
    updated = await service.update(
        report.report_id,
        FieldReportUpdate(sync_status=SyncStatus.PENDING_SYNC),
        current,
    )
    assert updated.timestamp_synced is None


async def test_update_by_other_worker_is_403(
    service, session, session_factory, make_worker
):
    _, worker = await make_worker()
    intruder, _ = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    with pytest.raises(HTTPException) as exc:
        await service.update(
            report.report_id,
            FieldReportUpdate(report_details="x"),
            await loaded(session, intruder),
        )
    assert exc.value.status_code == 403


async def test_update_by_admin_allowed(
    service, session, session_factory, make_user, make_worker
):
    admin = await make_user()
    _, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    updated = await service.update(
        report.report_id,
        FieldReportUpdate(status=StatusEnum.ERROR),
        await loaded(session, admin),
    )
    assert updated.status is StatusEnum.ERROR


async def test_update_unknown_report_is_404(service, session, make_user):
    admin = await make_user()
    with pytest.raises(HTTPException) as exc:
        await service.update(
            uuid.uuid4(),
            FieldReportUpdate(report_details="x"),
            await loaded(session, admin),
        )
    assert exc.value.status_code == 404


async def test_delete_by_owner_removes_report(
    service, session, session_factory, make_worker
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    assert await service.delete(report.report_id, await loaded(session, user)) is None
    with pytest.raises(HTTPException) as exc:
        await service.get_by_id(report.report_id, await loaded(session, user))
    assert exc.value.status_code == 404


async def test_delete_by_admin_allowed(
    service, session, session_factory, make_user, make_worker
):
    admin = await make_user()
    _, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    await service.delete(report.report_id, await loaded(session, admin))


async def test_delete_by_other_worker_is_403_and_keeps_report(
    service, session, session_factory, make_user, make_worker
):
    admin = await make_user()
    _, worker = await make_worker()
    intruder, _ = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    with pytest.raises(HTTPException) as exc:
        await service.delete(report.report_id, await loaded(session, intruder))
    assert exc.value.status_code == 403
    assert (
        await service.get_by_id(report.report_id, await loaded(session, admin))
    ).report_id == report.report_id


async def test_delete_unknown_report_is_404(service, session, make_user):
    admin = await make_user()
    with pytest.raises(HTTPException) as exc:
        await service.delete(uuid.uuid4(), await loaded(session, admin))
    assert exc.value.status_code == 404
