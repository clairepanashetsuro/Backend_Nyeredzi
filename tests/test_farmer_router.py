
import uuid

import pytest
from fastapi.exceptions import ResponseValidationError

from ivhuRedu.models.user import UserType


def body(default_location_id, **overrides):
    data = {
        "first_name": "Chipo",
        "last_name": "Ncube",
        "phone_number": "+263772220000",
        "primary_crop": "maize",
        "ward_name": "Ward 4",
        "location_id": str(default_location_id),
    }
    data.update(overrides)
    return data


async def test_extension_worker_can_register_farmer(
    client, make_worker, make_location, auth_headers
):
    worker_user, _ = await make_worker()
    loc = await make_location()
    r = await client.post(
        "/farmers/",
        headers=await auth_headers(worker_user),
        json=body(loc.location_id),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["ward_name"] == "Ward 4"
    assert data["user"]["user_type"] == "farmer"
    assert data["location"]["location_id"] == str(loc.location_id)


@pytest.mark.parametrize(
    "role", [UserType.ADMIN, UserType.SUPERVISOR, UserType.FARMER]
)
async def test_register_farmer_forbidden_for_other_roles(
    client, make_user, make_location, auth_headers, role
):
    caller = await make_user(user_type=role)
    loc = await make_location()
    r = await client.post(
        "/farmers/",
        headers=await auth_headers(caller),
        json=body(loc.location_id),
    )
    assert r.status_code == 403


async def test_register_farmer_requires_authentication(client, make_location):
    loc = await make_location()
    r = await client.post("/farmers/", json=body(loc.location_id))
    assert r.status_code == 401


async def test_register_farmer_duplicate_phone_is_409(
    client, make_worker, make_user, make_location, auth_headers
):
    worker_user, _ = await make_worker()
    await make_user(phone="+263772220000")
    loc = await make_location()
    r = await client.post(
        "/farmers/",
        headers=await auth_headers(worker_user),
        json=body(loc.location_id),
    )
    assert r.status_code == 409


async def test_register_farmer_unknown_location_is_409(
    client, make_worker, auth_headers
):
    worker_user, _ = await make_worker()
    r = await client.post(
        "/farmers/",
        headers=await auth_headers(worker_user),
        json=body(uuid.uuid4()),
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "override",
    [
        {"first_name": "A"},
        {"last_name": ""},
        {"phone_number": "abc"},
        {"ward_name": "x"},
        {"location_id": "not-a-uuid"},
        {"primary_crop": "x" * 51},
    ],
)
async def test_register_farmer_validation_errors(
    client, make_worker, make_location, auth_headers, override
):
    worker_user, _ = await make_worker()
    loc = await make_location()
    r = await client.post(
        "/farmers/",
        headers=await auth_headers(worker_user),
        json=body(loc.location_id, **override),
    )
    assert r.status_code == 422


@pytest.mark.parametrize(
    "role", [UserType.ADMIN, UserType.SUPERVISOR, UserType.EXTENSION_WORKER]
)
async def test_list_farmers_allowed_roles(
    client, make_user, make_farmer, auth_headers, role
):
    await make_farmer()
    await make_farmer()
    caller = await make_user(user_type=role)
    r = await client.get("/farmers/", headers=await auth_headers(caller))
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert all("hashed_password" not in item["user"] for item in r.json())


async def test_list_farmers_forbidden_for_farmer(client, make_farmer, auth_headers):
    user, _ = await make_farmer()
    r = await client.get("/farmers/", headers=await auth_headers(user))
    assert r.status_code == 403


async def test_list_farmers_requires_authentication(client):
    r = await client.get("/farmers/")
    assert r.status_code == 401


@pytest.mark.xfail(
    strict=True,
    raises=ResponseValidationError,
    reason="GET /farmers/{id} declares response_model=list[FarmerRead] "
    "but returns a single farmer",
)
async def test_get_single_farmer_returns_the_farmer(
    client, make_user, make_farmer, auth_headers
):
    admin = await make_user()
    _, farmer = await make_farmer()
    r = await client.get(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(admin),
    )
    assert r.status_code == 200
    assert r.json()["farmer_id"] == str(farmer.farmer_id)


async def test_get_single_farmer_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.get(
        f"/farmers/{uuid.uuid4()}",
        headers=await auth_headers(admin),
    )
    assert r.status_code == 404


async def test_get_single_farmer_forbidden_for_farmer(
    client, make_farmer, auth_headers
):
    user, farmer = await make_farmer()
    r = await client.get(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(user),
    )
    assert r.status_code == 403


@pytest.mark.parametrize(
    "role", [UserType.ADMIN, UserType.SUPERVISOR, UserType.EXTENSION_WORKER]
)
async def test_update_farmer_allowed_roles(
    client, make_user, make_farmer, auth_headers, role
):
    _, farmer = await make_farmer()
    caller = await make_user(user_type=role)
    r = await client.put(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(caller),
        json={"ward_name": "Ward 77"},
    )
    assert r.status_code == 200
    assert r.json()["ward_name"] == "Ward 77"


async def test_update_farmer_forbidden_for_farmer(
    client, make_farmer, auth_headers
):
    user, farmer = await make_farmer()
    r = await client.put(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(user),
        json={"ward_name": "Ward 77"},
    )
    assert r.status_code == 403


async def test_update_farmer_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.put(
        f"/farmers/{uuid.uuid4()}",
        headers=await auth_headers(admin),
        json={"ward_name": "Ward 77"},
    )
    assert r.status_code == 404


async def test_update_farmer_taken_phone_is_409(
    client, make_user, make_farmer, auth_headers
):
    admin = await make_user()
    await make_user(phone="+263774440000")
    _, farmer = await make_farmer()
    r = await client.put(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(admin),
        json={"phone_number": "+263774440000"},
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "payload", [{"phone_number": "bad"}, {"ward_name": "x"}, {"first_name": "A"}]
)
async def test_update_farmer_validation_errors(
    client, make_user, make_farmer, auth_headers, payload
):
    admin = await make_user()
    _, farmer = await make_farmer()
    r = await client.put(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(admin),
        json=payload,
    )
    assert r.status_code == 422


@pytest.mark.parametrize("role", [UserType.ADMIN, UserType.EXTENSION_WORKER])
async def test_delete_farmer_allowed_roles(
    client, make_user, make_farmer, auth_headers, role
):
    _, farmer = await make_farmer()
    caller = await make_user(user_type=role)
    r = await client.delete(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(caller),
    )
    assert r.status_code == 200
    assert r.json() == {"message": "Farmer deleted successfully."}


async def test_delete_farmer_forbidden_for_supervisor(
    client, make_user, make_farmer, auth_headers
):
    _, farmer = await make_farmer()
    caller = await make_user(user_type=UserType.SUPERVISOR)
    r = await client.delete(
        f"/farmers/{farmer.farmer_id}",
        headers=await auth_headers(caller),
    )
    assert r.status_code == 403


async def test_delete_farmer_unknown_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.delete(
        f"/farmers/{uuid.uuid4()}",
        headers=await auth_headers(admin),
    )
    assert r.status_code == 404