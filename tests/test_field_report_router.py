import uuid

import pytest

from ivhuRedu.models.user import UserType
from tests.helpers import create_image, create_report


def body(**overrides):
    data = {"worker_id": str(uuid.uuid4()), "description_type": "pest"}
    data.update(overrides)
    return data


async def test_worker_can_create_report(client, make_worker, auth_headers):
    user, worker = await make_worker()
    r = await client.post(
        "/field-reports/",
        headers=await auth_headers(user),
        json=body(issue_type="Pest Outbreak", report_details="Armyworm"),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["worker_id"] == str(worker.worker_id)
    assert data["issue_type"] == "Pest Outbreak"
    assert data["status"] == "PENDING"
    assert data["sync_status"] == "PENDING_SYNC"
    assert data["images"] == []


@pytest.mark.parametrize(
    "role", [UserType.ADMIN, UserType.SUPERVISOR, UserType.FARMER]
)
async def test_create_report_forbidden_for_non_workers(
    client, make_user, auth_headers, role
):
    user = await make_user(user_type=role)
    r = await client.post(
        "/field-reports/", headers=await auth_headers(user), json=body()
    )
    assert r.status_code == 403


async def test_create_report_requires_authentication(client):
    assert (await client.post("/field-reports/", json=body())).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"worker_id": str(uuid.uuid4())},
        {"description_type": "pest"},
        body(issue_type="Alien Invasion"),
        body(worker_id="not-a-uuid"),
        body(sync_status="whenever"),
    ],
)
async def test_create_report_validation_errors(
    client, make_worker, auth_headers, payload
):
    user, _ = await make_worker()
    r = await client.post(
        "/field-reports/", headers=await auth_headers(user), json=payload
    )
    assert r.status_code == 422


async def test_create_report_blank_description_type_is_422(
    client, make_worker, auth_headers
):
    user, _ = await make_worker()
    r = await client.post(
        "/field-reports/",
        headers=await auth_headers(user),
        json=body(description_type="   "),
    )
    assert r.status_code == 422


async def test_list_reports_worker_sees_only_own(
    client, session_factory, make_worker, auth_headers
):
    user, own = await make_worker()
    _, other = await make_worker()
    await create_report(session_factory, own.worker_id)
    await create_report(session_factory, other.worker_id)
    r = await client.get("/field-reports/", headers=await auth_headers(user))
    assert r.status_code == 200
    assert [x["worker_id"] for x in r.json()] == [str(own.worker_id)]


async def test_list_reports_admin_sees_all(
    client, session_factory, make_user, make_worker, auth_headers
):
    admin = await make_user()
    _, first = await make_worker()
    _, second = await make_worker()
    await create_report(session_factory, first.worker_id)
    await create_report(session_factory, second.worker_id)
    r = await client.get("/field-reports/", headers=await auth_headers(admin))
    assert r.status_code == 200 and len(r.json()) == 2


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.FARMER])
async def test_list_reports_forbidden_for_other_roles(
    client, make_user, auth_headers, role
):
    user = await make_user(user_type=role)
    r = await client.get("/field-reports/", headers=await auth_headers(user))
    assert r.status_code == 403


async def test_list_reports_requires_authentication(client):
    assert (await client.get("/field-reports/")).status_code == 401


async def test_reports_by_worker_self_allowed_other_forbidden(
    client, session_factory, make_worker, auth_headers
):
    user, own = await make_worker()
    _, other = await make_worker()
    await create_report(session_factory, own.worker_id)
    headers = await auth_headers(user)
    ok = await client.get(f"/field-reports/worker/{own.worker_id}", headers=headers)
    assert ok.status_code == 200 and len(ok.json()) == 1
    denied = await client.get(
        f"/field-reports/worker/{other.worker_id}", headers=headers
    )
    assert denied.status_code == 403


async def test_reports_by_worker_admin_allowed(
    client, session_factory, make_user, make_worker, auth_headers
):
    admin = await make_user()
    _, worker = await make_worker()
    await create_report(session_factory, worker.worker_id)
    r = await client.get(
        f"/field-reports/worker/{worker.worker_id}", headers=await auth_headers(admin)
    )
    assert r.status_code == 200 and len(r.json()) == 1


async def test_get_report_returns_images(
    client, session_factory, make_worker, auth_headers
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    await create_image(session_factory, report.report_id, "secure_storage/a.enc")
    r = await client.get(
        f"/field-reports/{report.report_id}", headers=await auth_headers(user)
    )
    assert r.status_code == 200
    data = r.json()
    assert data["report_id"] == str(report.report_id)
    assert [i["image_url"] for i in data["images"]] == ["secure_storage/a.enc"]


async def test_get_report_other_worker_forbidden(
    client, session_factory, make_worker, auth_headers
):
    _, worker = await make_worker()
    intruder, _ = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    r = await client.get(
        f"/field-reports/{report.report_id}", headers=await auth_headers(intruder)
    )
    assert r.status_code == 403


async def test_get_report_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.get(
        f"/field-reports/{uuid.uuid4()}", headers=await auth_headers(admin)
    )
    assert r.status_code == 404


async def test_get_report_invalid_uuid_is_422(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.get("/field-reports/nope", headers=await auth_headers(admin))
    assert r.status_code == 422


async def test_patch_report_updates_fields(
    client, session_factory, make_worker, auth_headers
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    r = await client.patch(
        f"/field-reports/{report.report_id}",
        headers=await auth_headers(user),
        json={"report_details": "Updated", "issue_type": "Crop Failure"},
    )
    assert r.status_code == 200
    assert r.json()["report_details"] == "Updated"
    assert r.json()["issue_type"] == "Crop Failure"


async def test_patch_report_to_synced_completes_it(
    client, session_factory, make_worker, auth_headers
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    r = await client.patch(
        f"/field-reports/{report.report_id}",
        headers=await auth_headers(user),
        json={"sync_status": "synced"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["timestamp_synced"] is not None


async def test_patch_report_other_worker_forbidden(
    client, session_factory, make_worker, auth_headers
):
    _, worker = await make_worker()
    intruder, _ = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    r = await client.patch(
        f"/field-reports/{report.report_id}",
        headers=await auth_headers(intruder),
        json={"report_details": "x"},
    )
    assert r.status_code == 403


async def test_patch_report_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.patch(
        f"/field-reports/{uuid.uuid4()}",
        headers=await auth_headers(admin),
        json={"report_details": "x"},
    )
    assert r.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{"issue_type": "Alien Invasion"}, {"sync_status": "whenever"}, {"description_type": ""}],
)
async def test_patch_report_validation_errors(
    client, session_factory, make_worker, auth_headers, payload
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    r = await client.patch(
        f"/field-reports/{report.report_id}",
        headers=await auth_headers(user),
        json=payload,
    )
    assert r.status_code == 422


async def test_delete_report_returns_204_then_404(
    client, session_factory, make_worker, auth_headers
):
    user, worker = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    headers = await auth_headers(user)
    deleted = await client.delete(f"/field-reports/{report.report_id}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    again = await client.get(f"/field-reports/{report.report_id}", headers=headers)
    assert again.status_code == 404


async def test_delete_report_other_worker_forbidden(
    client, session_factory, make_worker, auth_headers
):
    _, worker = await make_worker()
    intruder, _ = await make_worker()
    report = await create_report(session_factory, worker.worker_id)
    r = await client.delete(
        f"/field-reports/{report.report_id}", headers=await auth_headers(intruder)
    )
    assert r.status_code == 403


async def test_delete_report_requires_authentication(client):
    assert (await client.delete(f"/field-reports/{uuid.uuid4()}")).status_code == 401
