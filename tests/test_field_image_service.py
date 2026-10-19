import io
import os
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.datastructures import UploadFile

from ivhuRedu.schemas.field_image import ReportImageUpdate
from ivhuRedu.services import field_image as image_module
from ivhuRedu.services.field_image import FieldImageService
from tests.helpers import create_image, create_report
from utils.crypto import decrypt_file_data


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(image_module, "SECURE_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def service(session):
    return FieldImageService(session)


@pytest.fixture
def make_report_row(session_factory, make_worker):
    async def _make():
        _, worker = await make_worker()
        return await create_report(session_factory, worker.worker_id)

    return _make


def upload(content=b"fake-jpeg-bytes", name="photo.jpg"):
    return UploadFile(file=io.BytesIO(content), filename=name)


async def test_store_image_writes_encrypted_file_and_db_row(
    service, make_report_row, storage_dir
):
    report = await make_report_row()
    result = await service.encrypt_and_store_image(
        report.report_id, upload(b"secret-photo")
    )
    assert result.report_id == report.report_id
    assert result.file_url.startswith(str(storage_dir))
    assert result.file_url.endswith(".enc")
    assert os.path.exists(result.file_url)
    stored = open(result.file_url, "rb").read()
    assert b"secret-photo" not in stored
    assert decrypt_file_data(stored) == b"secret-photo"


async def test_store_image_uses_unique_filenames(service, make_report_row):
    report = await make_report_row()
    first = await service.encrypt_and_store_image(report.report_id, upload())
    second = await service.encrypt_and_store_image(report.report_id, upload())
    assert first.file_url != second.file_url
    assert first.image_id != second.image_id


async def test_store_empty_file_roundtrips(service, make_report_row):
    report = await make_report_row()
    result = await service.encrypt_and_store_image(report.report_id, upload(b""))
    assert await service.get_decrypted_image_bytes(result.image_id) == b""


async def test_store_image_for_unknown_report_raises_integrity_error(service):
    with pytest.raises(IntegrityError):
        await service.encrypt_and_store_image(uuid.uuid4(), upload())


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the encrypted file is written before the report is validated, "
    "so a failed upload leaves an orphan file on disk",
)
async def test_failed_store_leaves_no_orphan_file(service, storage_dir):
    with pytest.raises(IntegrityError):
        await service.encrypt_and_store_image(uuid.uuid4(), upload())
    assert list(storage_dir.iterdir()) == []


async def test_get_decrypted_bytes_roundtrip(service, make_report_row):
    report = await make_report_row()
    stored = await service.encrypt_and_store_image(
        report.report_id, upload(b"\x00\x01binary\xff" * 100)
    )
    assert (
        await service.get_decrypted_image_bytes(stored.image_id)
        == b"\x00\x01binary\xff" * 100
    )


async def test_get_decrypted_bytes_unknown_image_is_404(service):
    with pytest.raises(HTTPException) as exc:
        await service.get_decrypted_image_bytes(uuid.uuid4())
    assert exc.value.status_code == 404


async def test_get_decrypted_bytes_missing_file_is_404(
    service, session_factory, make_report_row, storage_dir
):
    report = await make_report_row()
    image = await create_image(
        session_factory, report.report_id, str(storage_dir / "gone.enc")
    )
    with pytest.raises(HTTPException) as exc:
        await service.get_decrypted_image_bytes(image.image_id)
    assert exc.value.status_code == 404
    assert "Physical encrypted file" in exc.value.detail


async def test_get_images_by_report_lists_only_that_report(
    service, make_report_row
):
    first = await make_report_row()
    second = await make_report_row()
    await service.encrypt_and_store_image(first.report_id, upload())
    await service.encrypt_and_store_image(first.report_id, upload())
    await service.encrypt_and_store_image(second.report_id, upload())
    assert len(await service.get_images_by_report(first.report_id)) == 2
    assert len(await service.get_images_by_report(second.report_id)) == 1
    assert await service.get_images_by_report(uuid.uuid4()) == []


async def test_get_image_found_and_missing(service, make_report_row):
    report = await make_report_row()
    stored = await service.encrypt_and_store_image(report.report_id, upload())
    found = await service.get_image(stored.image_id)
    assert found.image_id == stored.image_id
    assert found.file_url == stored.file_url
    with pytest.raises(HTTPException) as exc:
        await service.get_image(uuid.uuid4())
    assert exc.value.status_code == 404


async def test_update_image_changes_url(service, make_report_row):
    report = await make_report_row()
    stored = await service.encrypt_and_store_image(report.report_id, upload())
    updated = await service.update_image(
        stored.image_id, ReportImageUpdate(file_url="elsewhere.enc")
    )
    assert updated.file_url == "elsewhere.enc"


async def test_update_image_unknown_is_404(service):
    with pytest.raises(HTTPException) as exc:
        await service.update_image(uuid.uuid4(), ReportImageUpdate(file_url="x"))
    assert exc.value.status_code == 404


async def test_delete_image_removes_row_and_file(service, make_report_row):
    report = await make_report_row()
    stored = await service.encrypt_and_store_image(report.report_id, upload())
    assert await service.delete_image(stored.image_id) is None
    assert not os.path.exists(stored.file_url)
    with pytest.raises(HTTPException) as exc:
        await service.get_image(stored.image_id)
    assert exc.value.status_code == 404


async def test_delete_image_succeeds_when_file_already_gone(
    service, session_factory, make_report_row, storage_dir
):
    report = await make_report_row()
    image = await create_image(
        session_factory, report.report_id, str(storage_dir / "gone.enc")
    )
    await service.delete_image(image.image_id)
    with pytest.raises(HTTPException):
        await service.get_image(image.image_id)


async def test_delete_image_unknown_is_404(service):
    with pytest.raises(HTTPException) as exc:
        await service.delete_image(uuid.uuid4())
    assert exc.value.status_code == 404
