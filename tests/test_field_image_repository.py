import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from ivhuRedu.repositories.field_image import FieldImageRepository
from ivhuRedu.schemas.field_image import ReportImageCreate, ReportImageUpdate
from tests.helpers import create_image, create_report


@pytest.fixture
def repo(session):
    return FieldImageRepository(session)


@pytest.fixture
def make_report_row(session_factory, make_worker):
    async def _make():
        _, worker = await make_worker()
        return await create_report(session_factory, worker.worker_id)

    return _make


async def test_create_stores_url_in_image_url_column(repo, make_report_row):
    report = await make_report_row()
    image = await repo.create(
        ReportImageCreate(report_id=report.report_id, file_url="secure_storage/a.enc")
    )
    assert image.image_id is not None
    assert image.image_url == "secure_storage/a.enc"
    assert image.report_id == report.report_id
    assert image.uploaded_at is not None


async def test_create_for_unknown_report_raises(repo):
    with pytest.raises(IntegrityError):
        await repo.create(
            ReportImageCreate(report_id=uuid.uuid4(), file_url="x.enc")
        )


async def test_get_by_id_found_and_missing(repo, session_factory, make_report_row):
    report = await make_report_row()
    image = await create_image(session_factory, report.report_id)
    assert (await repo.get_by_id(image.image_id)).image_id == image.image_id
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_get_by_report_id_filters_by_report(
    repo, session_factory, make_report_row
):
    first = await make_report_row()
    second = await make_report_row()
    await create_image(session_factory, first.report_id, "a.enc")
    await create_image(session_factory, first.report_id, "b.enc")
    await create_image(session_factory, second.report_id, "c.enc")
    first_images = await repo.get_by_report_id(first.report_id)
    assert isinstance(first_images, list)
    assert {i.image_url for i in first_images} == {"a.enc", "b.enc"}
    assert await repo.get_by_report_id(uuid.uuid4()) == []


async def test_update_maps_file_url_to_image_url(
    repo, session_factory, make_report_row
):
    report = await make_report_row()
    image = await create_image(session_factory, report.report_id, "old.enc")
    updated = await repo.update(
        image.image_id, ReportImageUpdate(file_url="new.enc")
    )
    assert updated.image_url == "new.enc"


async def test_update_without_changes_keeps_url(
    repo, session_factory, make_report_row
):
    report = await make_report_row()
    image = await create_image(session_factory, report.report_id, "same.enc")
    updated = await repo.update(image.image_id, ReportImageUpdate())
    assert updated.image_url == "same.enc"


async def test_update_unknown_id_returns_none(repo):
    assert (
        await repo.update(uuid.uuid4(), ReportImageUpdate(file_url="x")) is None
    )


async def test_delete_removes_image(repo, session_factory, make_report_row):
    report = await make_report_row()
    image = await create_image(session_factory, report.report_id)
    assert await repo.delete(image.image_id) is True
    assert await repo.get_by_id(image.image_id) is None


async def test_delete_unknown_id_returns_false(repo):
    assert await repo.delete(uuid.uuid4()) is False
