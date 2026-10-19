import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ivhuRedu.models.field_image import FieldImage
from ivhuRedu.models.field_report import (
    IssueType,
    StatusEnum,
    SyncStatus,
)
from ivhuRedu.repositories.field_report import FieldReportRepository
from ivhuRedu.schemas.field_report import FieldReportCreate, FieldReportUpdate
from tests.helpers import create_image, create_report


@pytest.fixture
def repo(session):
    return FieldReportRepository(session)


async def test_create_persists_report_with_defaults(repo, make_worker):
    _, worker = await make_worker()
    report = await repo.create(
        FieldReportCreate(
            worker_id=worker.worker_id,
            description_type="pest",
            issue_type=IssueType.PEST_OUTBREAK,
            report_details="Armyworm in field 3",
        )
    )
    assert report.report_id is not None
    assert report.issue_type is IssueType.PEST_OUTBREAK
    assert report.report_details == "Armyworm in field 3"
    assert report.status is StatusEnum.PENDING
    assert report.sync_status is SyncStatus.PENDING_SYNC
    assert report.timestamp_captured is not None
    assert report.images == []


async def test_create_with_unknown_worker_raises(repo):
    with pytest.raises(IntegrityError):
        await repo.create(
            FieldReportCreate(worker_id=uuid.uuid4(), description_type="pest")
        )


async def test_create_with_unknown_farmer_raises(repo, make_worker):
    _, worker = await make_worker()
    with pytest.raises(IntegrityError):
        await repo.create(
            FieldReportCreate(
                worker_id=worker.worker_id,
                description_type="pest",
                farmer_id=uuid.uuid4(),
            )
        )


async def test_create_links_farmer(repo, make_worker, make_farmer):
    _, worker = await make_worker()
    _, farmer = await make_farmer()
    report = await repo.create(
        FieldReportCreate(
            worker_id=worker.worker_id,
            description_type="visit",
            farmer_id=farmer.farmer_id,
        )
    )
    assert report.farmer_id == farmer.farmer_id


async def test_get_all_empty_and_populated(repo, session_factory, make_worker):
    assert await repo.get_all() == []
    _, worker = await make_worker()
    await create_report(session_factory, worker.worker_id)
    await create_report(session_factory, worker.worker_id)
    assert len(await repo.get_all()) == 2


async def test_get_by_id_found_with_images_and_missing(
    repo, session_factory, make_worker
):
    _, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    await create_image(session_factory, report.report_id)
    found = await repo.get_by_id(report.report_id)
    assert found.report_id == report.report_id
    assert len(found.images) == 1
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_get_by_worker_only_returns_that_workers_reports(
    repo, session_factory, make_worker
):
    _, first = await make_worker()
    _, second = await make_worker()
    await create_report(session_factory, first.worker_id)
    await create_report(session_factory, first.worker_id)
    await create_report(session_factory, second.worker_id)
    assert len(await repo.get_by_worker(first.worker_id)) == 2
    assert len(await repo.get_by_worker(second.worker_id)) == 1
    assert await repo.get_by_worker(uuid.uuid4()) == []


async def test_update_changes_only_provided_fields(
    repo, session_factory, make_worker
):
    _, worker = await make_worker()
    report = await create_report(
        session_factory, worker.worker_id, report_details="original"
    )
    updated = await repo.update(
        report.report_id, FieldReportUpdate(issue_type=IssueType.CROP_FAILURE)
    )
    assert updated.issue_type is IssueType.CROP_FAILURE
    assert updated.report_details == "original"
    assert updated.description_type == "pest"


async def test_update_explicit_none_clears_optional_field(
    repo, session_factory, make_worker
):
    _, worker = await make_worker()
    report = await create_report(
        session_factory, worker.worker_id, report_details="to clear"
    )
    updated = await repo.update(
        report.report_id, FieldReportUpdate(report_details=None)
    )
    assert updated.report_details is None


async def test_update_status_and_sync_status(repo, session_factory, make_worker):
    _, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    updated = await repo.update(
        report.report_id,
        FieldReportUpdate(status=StatusEnum.ERROR, sync_status=SyncStatus.SYNCED),
    )
    assert updated.status is StatusEnum.ERROR
    assert updated.sync_status is SyncStatus.SYNCED


async def test_update_unknown_id_returns_none(repo):
    assert (
        await repo.update(uuid.uuid4(), FieldReportUpdate(report_details="x"))
        is None
    )


async def test_delete_removes_report_and_its_images(
    repo, session, session_factory, make_worker
):
    _, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    await create_image(session_factory, report.report_id)
    await create_image(session_factory, report.report_id)
    assert await repo.delete(report.report_id) is True
    assert await repo.get_by_id(report.report_id) is None
    assert (await session.execute(select(FieldImage))).first() is None


async def test_delete_unknown_id_returns_false(repo):
    assert await repo.delete(uuid.uuid4()) is False
