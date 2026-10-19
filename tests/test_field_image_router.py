
import os
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from ivhuRedu.services import field_image as image_module
from tests.helpers import create_report


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(image_module, "SECURE_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def make_report_row(session_factory, make_worker):
    async def _make():
        _, worker = await make_worker()
        return await create_report(session_factory, worker.worker_id)

    return _make


def files(content=b"jpeg-bytes", name="photo.jpg"):
    return {"file": (name, content, "image/jpeg")}


async def upload(client, report_id, content=b"jpeg-bytes"):
    response = await client.post(
        f"/field-images/upload/{report_id}",
        files=files(content),
    )
    assert response.status_code == 201
    return response.json()


async def test_upload_stores_encrypted_file(client, make_report_row, storage_dir):
    report = await make_report_row()
    data = await upload(client, report.report_id, b"plain-bytes")

    assert data["report_id"] == str(report.report_id)
    assert data["file_url"].startswith(str(storage_dir))
    assert os.path.exists(data["file_url"])

    with open(data["file_url"], "rb") as stored_file:
        assert b"plain-bytes" not in stored_file.read()


async def test_upload_without_file_part_is_422(client, make_report_row):
    report = await make_report_row()
    response = await client.post(f"/field-images/upload/{report.report_id}")
    assert response.status_code == 422


async def test_upload_invalid_report_id_is_422(client):
    response = await client.post(
        "/field-images/upload/not-a-uuid",
        files=files(),
    )
    assert response.status_code == 422


@pytest.mark.xfail(
    strict=True,
    raises=IntegrityError,
    reason="uploading to a report that does not exist crashes with a 500 "
    "instead of returning 404",
)
async def test_upload_to_unknown_report_is_404(client):
    response = await client.post(
        f"/field-images/upload/{uuid.uuid4()}",
        files=files(),
    )
    assert response.status_code == 404


async def test_download_returns_original_bytes(client, make_report_row):
    report = await make_report_row()
    data = await upload(client, report.report_id, b"original-image-bytes")

    response = await client.get(
        f"/field-images/download/{data['image_id']}"
    )

    assert response.status_code == 200
    assert response.content == b"original-image-bytes"
    assert response.headers["content-type"] == "image/jpeg"


async def test_download_unknown_image_is_404(client):
    response = await client.get(
        f"/field-images/download/{uuid.uuid4()}"
    )
    assert response.status_code == 404


async def test_list_images_for_report(client, make_report_row):
    first = await make_report_row()
    second = await make_report_row()

    await upload(client, first.report_id)
    await upload(client, first.report_id)
    await upload(client, second.report_id)

    response = await client.get(
        f"/field-images/report/{first.report_id}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_images_for_report_without_images_is_empty(client):
    response = await client.get(
        f"/field-images/report/{uuid.uuid4()}"
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_get_image_metadata(client, make_report_row):
    report = await make_report_row()
    data = await upload(client, report.report_id)

    response = await client.get(f"/field-images/{data['image_id']}")

    assert response.status_code == 200
    assert response.json()["image_id"] == data["image_id"]
    assert "uploaded_at" in response.json()


async def test_get_image_unknown_is_404(client):
    response = await client.get(f"/field-images/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_update_image_url(client, make_report_row):
    report = await make_report_row()
    data = await upload(client, report.report_id)

    response = await client.put(
        f"/field-images/{data['image_id']}",
        json={"file_url": "moved.enc"},
    )

    assert response.status_code == 200
    assert response.json()["file_url"] == "moved.enc"


async def test_update_image_unknown_is_404(client):
    response = await client.put(
        f"/field-images/{uuid.uuid4()}",
        json={"file_url": "x"},
    )
    assert response.status_code == 404


async def test_delete_image_removes_record_and_file(
    client, make_report_row
):
    report = await make_report_row()
    data = await upload(client, report.report_id)

    response = await client.delete(
        f"/field-images/{data['image_id']}"
    )

    assert response.status_code == 204
    assert not os.path.exists(data["file_url"])

    response = await client.get(f"/field-images/{data['image_id']}")
    assert response.status_code == 404


async def test_delete_image_unknown_is_404(client):
    response = await client.delete(
        f"/field-images/{uuid.uuid4()}"
    )
    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="field image endpoints have no authentication",
)
async def test_upload_requires_authentication(client, make_report_row):
    report = await make_report_row()
    response = await client.post(
        f"/field-images/upload/{report.report_id}",
        files=files(),
    )
    assert response.status_code == 401


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="field image endpoints have no authentication",
)
async def test_download_requires_authentication(client, make_report_row):
    report = await make_report_row()
    data = await upload(client, report.report_id)

    response = await client.get(
        f"/field-images/download/{data['image_id']}"
    )
    assert response.status_code == 401


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="field image endpoints have no authentication",
)
async def test_delete_requires_authentication(client, make_report_row):
    report = await make_report_row()
    data = await upload(client, report.report_id)

    response = await client.delete(
        f"/field-images/{data['image_id']}"
    )
    assert response.status_code == 401
