import uuid

import pytest

from ivhuRedu.models.extension_worker import WorkerAvailabilityStatus
from ivhuRedu.models.user import UserType


def body(location_id, **overrides):
    data = {
        "first_name": "Farai",
        "last_name": "Dube",
        "phone_number": "+263775550000",
        "email": "farai@example.com",
        "password": "Password123",
        "ussd_pincode": "1234",
        "assigned_ward_name": "Ward 5",
        "location_id": str(location_id),
    }
    data.update(overrides)
    return data


async def test_supervisor_can_create_worker(
    client, make_user, make_location, auth_headers
):
    sup = await make_user(user_type=UserType.SUPERVISOR)
    loc = await make_location()
    r = await client.post(
        "/extension-workers/",
        headers=await auth_headers(sup),
        json=body(loc.location_id),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["assigned_ward_name"] == "Ward 5"
    assert data["availability_status"] == WorkerAvailabilityStatus.AVAILABLE.value
    assert "hashed_ussd_pincode" not in data and "ussd_pincode" not in data


@pytest.mark.parametrize(
    "role", [UserType.ADMIN, UserType.EXTENSION_WORKER, UserType.FARMER]
)
async def test_create_worker_forbidden_for_other_roles(
    client, make_user, make_location, auth_headers, role
):
    caller = await make_user(user_type=role)
    loc = await make_location()
    r = await client.post(
        "/extension-workers/",
        headers=await auth_headers(caller),
        json=body(loc.location_id),
    )
    assert r.status_code == 403


async def test_create_worker_requires_authentication(client, make_location):
    loc = await make_location()
    r = await client.post("/extension-workers/", json=body(loc.location_id))
    assert r.status_code == 401


async def test_created_worker_can_log_in_and_must_change_password(
    client, make_user, make_location, auth_headers
):
    sup = await make_user(user_type=UserType.SUPERVISOR)
    loc = await make_location()
    await client.post(
        "/extension-workers/",
        headers=await auth_headers(sup),
        json=body(loc.location_id),
    )
    login = await client.post(
        "/auth/login",
        data={"username": "+263775550000", "password": "Password123"},
    )
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True
    assert login.json()["offline_token"]


async def test_create_worker_duplicate_phone_is_409(
    client, make_user, make_location, auth_headers
):
    sup = await make_user(user_type=UserType.SUPERVISOR)
    await make_user(phone="+263775550000")
    loc = await make_location()
    r = await client.post(
        "/extension-workers/",
        headers=await auth_headers(sup),
        json=body(loc.location_id),
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "override",
    [
        {"ussd_pincode": "12a4"},
        {"ussd_pincode": "123"},
        {"ussd_pincode": "12345"},
        {"password": "short"},
        {"email": "not-an-email"},
        {"phone_number": "abc"},
        {"first_name": "F"},
        {"location_id": "nope"},
    ],
)
async def test_create_worker_validation_errors(
    client, make_user, make_location, auth_headers, override
):
    sup = await make_user(user_type=UserType.SUPERVISOR)
    loc = await make_location()
    r = await client.post(
        "/extension-workers/",
        headers=await auth_headers(sup),
        json=body(loc.location_id, **override),
    )
    assert r.status_code == 422


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.ADMIN])
async def test_list_workers_allowed_roles(
    client, make_user, make_worker, auth_headers, role
):
    await make_worker()
    await make_worker()
    caller = await make_user(user_type=role)
    r = await client.get("/extension-workers/", headers=await auth_headers(caller))
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert all("hashed_password" not in item["user"] for item in r.json())


async def test_list_workers_forbidden_for_worker(client, make_worker, auth_headers):
    user, _ = await make_worker()
    r = await client.get("/extension-workers/", headers=await auth_headers(user))
    assert r.status_code == 403


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.ADMIN])
async def test_get_worker_allowed_roles(
    client, make_user, make_worker, auth_headers, role
):
    user, worker = await make_worker()
    caller = await make_user(user_type=role)
    r = await client.get(
        f"/extension-workers/{worker.worker_id}", headers=await auth_headers(caller)
    )
    assert r.status_code == 200
    assert r.json()["user"]["id"] == str(user.id)


async def test_get_worker_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.get(
        f"/extension-workers/{uuid.uuid4()}", headers=await auth_headers(admin)
    )
    assert r.status_code == 404


async def test_get_worker_forbidden_for_worker(client, make_worker, auth_headers):
    user, worker = await make_worker()
    r = await client.get(
        f"/extension-workers/{worker.worker_id}", headers=await auth_headers(user)
    )
    assert r.status_code == 403


@pytest.mark.parametrize("status", [s.value for s in WorkerAvailabilityStatus])
async def test_supervisor_can_set_status(
    client, make_user, make_worker, auth_headers, status
):
    _, worker = await make_worker()
    sup = await make_user(user_type=UserType.SUPERVISOR)
    r = await client.patch(
        f"/extension-workers/{worker.worker_id}/status",
        headers=await auth_headers(sup),
        json={"availability_status": status},
    )
    assert r.status_code == 200
    assert r.json()["availability_status"] == status


async def test_set_status_invalid_value_is_422(
    client, make_user, make_worker, auth_headers
):
    _, worker = await make_worker()
    sup = await make_user(user_type=UserType.SUPERVISOR)
    r = await client.patch(
        f"/extension-workers/{worker.worker_id}/status",
        headers=await auth_headers(sup),
        json={"availability_status": "nonsense"},
    )
    assert r.status_code == 422


async def test_set_status_unknown_worker_is_404(client, make_user, auth_headers):
    sup = await make_user(user_type=UserType.SUPERVISOR)
    r = await client.patch(
        f"/extension-workers/{uuid.uuid4()}/status",
        headers=await auth_headers(sup),
        json={"availability_status": WorkerAvailabilityStatus.AVAILABLE.value},
    )
    assert r.status_code == 404


@pytest.mark.parametrize("role", [UserType.ADMIN, UserType.EXTENSION_WORKER])
async def test_set_status_forbidden_for_other_roles(
    client, make_user, make_worker, auth_headers, role
):
    _, worker = await make_worker()
    caller = await make_user(user_type=role)
    r = await client.patch(
        f"/extension-workers/{worker.worker_id}/status",
        headers=await auth_headers(caller),
        json={"availability_status": WorkerAvailabilityStatus.AVAILABLE.value},
    )
    assert r.status_code == 403


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.ADMIN])
async def test_update_worker_allowed_roles(
    client, make_user, make_worker, auth_headers, role
):
    _, worker = await make_worker()
    caller = await make_user(user_type=role)
    r = await client.put(
        f"/extension-workers/{worker.worker_id}",
        headers=await auth_headers(caller),
        json={"assigned_ward_name": "Ward 42", "first_name": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["assigned_ward_name"] == "Ward 42"
    assert r.json()["user"]["first_name"] == "Updated"


async def test_worker_cannot_update_themselves_through_the_api(
    client, make_worker, auth_headers
):
    user, worker = await make_worker()
    r = await client.put(
        f"/extension-workers/{worker.worker_id}",
        headers=await auth_headers(user),
        json={"first_name": "Self"},
    )
    assert r.status_code == 403


async def test_update_worker_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.put(
        f"/extension-workers/{uuid.uuid4()}",
        headers=await auth_headers(admin),
        json={"first_name": "Updated"},
    )
    assert r.status_code == 404


async def test_update_worker_taken_phone_is_409(
    client, make_user, make_worker, auth_headers
):
    admin = await make_user()
    await make_user(phone="+263777770000")
    _, worker = await make_worker()
    r = await client.put(
        f"/extension-workers/{worker.worker_id}",
        headers=await auth_headers(admin),
        json={"phone_number": "+263777770000"},
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [{"ussd_pincode": "abcd"}, {"password": "short"}, {"email": "bad"}],
)
async def test_update_worker_validation_errors(
    client, make_user, make_worker, auth_headers, payload
):
    admin = await make_user()
    _, worker = await make_worker()
    r = await client.put(
        f"/extension-workers/{worker.worker_id}",
        headers=await auth_headers(admin),
        json=payload,
    )
    assert r.status_code == 422


async def test_admin_can_delete_worker(client, make_user, make_worker, auth_headers):
    admin = await make_user()
    user, worker = await make_worker()
    r = await client.delete(
        f"/extension-workers/{worker.worker_id}", headers=await auth_headers(admin)
    )
    assert r.status_code == 200
    again = await client.get(
        f"/extension-workers/{worker.worker_id}", headers=await auth_headers(admin)
    )
    assert again.status_code == 404


@pytest.mark.parametrize("role", [UserType.SUPERVISOR, UserType.EXTENSION_WORKER])
async def test_delete_worker_forbidden_for_other_roles(
    client, make_user, make_worker, auth_headers, role
):
    _, worker = await make_worker()
    caller = await make_user(user_type=role)
    r = await client.delete(
        f"/extension-workers/{worker.worker_id}", headers=await auth_headers(caller)
    )
    assert r.status_code == 403


async def test_delete_worker_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.delete(
        f"/extension-workers/{uuid.uuid4()}", headers=await auth_headers(admin)
    )
    assert r.status_code == 404
