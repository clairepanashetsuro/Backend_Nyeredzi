import uuid

import pytest

from ivhuRedu.models.user import UserType

NEW = {
    "first_name": "Tendai",
    "last_name": "Moyo",
    "phone_number": "+263771230000",
}


async def test_create_supervisor_as_admin(client, make_user, auth_headers):
    admin = await make_user(user_type=UserType.ADMIN)
    r = await client.post(
        "/users/",
        headers=await auth_headers(admin),
        json={**NEW, "password": "Secret1234"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user_type"] == "supervisor"
    assert body["phone_number"] == NEW["phone_number"]
    assert "hashed_password" not in body and "password" not in body


async def test_create_supervisor_without_password_is_400(
    client, make_user, auth_headers
):
    admin = await make_user()
    r = await client.post("/users/", headers=await auth_headers(admin), json=NEW)
    assert r.status_code == 400


async def test_create_other_user_type_via_query_param(
    client, make_user, auth_headers
):
    admin = await make_user()
    r = await client.post(
        "/users/?user_type=extension_worker",
        headers=await auth_headers(admin),
        json=NEW,
    )
    assert r.status_code == 201
    assert r.json()["user_type"] == "extension_worker"


async def test_create_user_invalid_user_type_query_is_422(
    client, make_user, auth_headers
):
    admin = await make_user()
    r = await client.post(
        "/users/?user_type=wizard", headers=await auth_headers(admin), json=NEW
    )
    assert r.status_code == 422


@pytest.mark.parametrize(
    "role", [UserType.SUPERVISOR, UserType.EXTENSION_WORKER, UserType.FARMER]
)
async def test_create_user_forbidden_for_non_admins(
    client, make_user, auth_headers, role
):
    user = await make_user(user_type=role)
    r = await client.post(
        "/users/",
        headers=await auth_headers(user),
        json={**NEW, "password": "Secret1234"},
    )
    assert r.status_code == 403


async def test_create_user_requires_authentication(client):
    r = await client.post("/users/", json={**NEW, "password": "Secret1234"})
    assert r.status_code == 401


async def test_create_user_blocked_until_admin_changes_password(
    client, make_user, auth_headers
):
    admin = await make_user(must_change_password=True)
    r = await client.post(
        "/users/",
        headers=await auth_headers(admin),
        json={**NEW, "password": "Secret1234"},
    )
    assert r.status_code == 403


async def test_create_user_duplicate_phone_is_409(client, make_user, auth_headers):
    admin = await make_user()
    await make_user(phone=NEW["phone_number"])
    r = await client.post(
        "/users/",
        headers=await auth_headers(admin),
        json={**NEW, "password": "Secret1234"},
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {**NEW, "phone_number": "abc"},
        {**NEW, "first_name": "   "},
        {**NEW, "password": "short"},
        {**NEW, "email": "not-an-email"},
        {"first_name": "x"},
    ],
)
async def test_create_user_validation_errors(
    client, make_user, auth_headers, payload
):
    admin = await make_user()
    r = await client.post(
        "/users/", headers=await auth_headers(admin), json=payload
    )
    assert r.status_code == 422


@pytest.mark.parametrize("role", [UserType.ADMIN, UserType.SUPERVISOR])
async def test_list_users_allowed_for_admin_and_supervisor(
    client, make_user, auth_headers, role
):
    caller = await make_user(user_type=role)
    await make_user(user_type=UserType.FARMER)
    r = await client.get("/users/", headers=await auth_headers(caller))
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert all("hashed_password" not in item for item in r.json())


@pytest.mark.parametrize("role", [UserType.EXTENSION_WORKER, UserType.FARMER])
async def test_list_users_forbidden_for_others(
    client, make_user, auth_headers, role
):
    caller = await make_user(user_type=role)
    r = await client.get("/users/", headers=await auth_headers(caller))
    assert r.status_code == 403


async def test_list_users_requires_authentication(client):
    assert (await client.get("/users/")).status_code == 401


async def test_get_own_user(client, make_user, auth_headers):
    u = await make_user(user_type=UserType.EXTENSION_WORKER)
    r = await client.get(f"/users/{u.id}", headers=await auth_headers(u))
    assert r.status_code == 200
    assert r.json()["id"] == str(u.id)


async def test_get_other_user_forbidden_for_non_privileged(
    client, make_user, auth_headers
):
    worker = await make_user(user_type=UserType.EXTENSION_WORKER)
    other = await make_user(user_type=UserType.FARMER)
    r = await client.get(f"/users/{other.id}", headers=await auth_headers(worker))
    assert r.status_code == 403


async def test_admin_can_get_any_user(client, make_user, auth_headers):
    admin = await make_user()
    other = await make_user(user_type=UserType.FARMER)
    r = await client.get(f"/users/{other.id}", headers=await auth_headers(admin))
    assert r.status_code == 200


async def test_get_unknown_user_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.get(f"/users/{uuid.uuid4()}", headers=await auth_headers(admin))
    assert r.status_code == 404


async def test_get_user_invalid_uuid_is_422(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.get("/users/not-a-uuid", headers=await auth_headers(admin))
    assert r.status_code == 422


async def test_get_user_blocked_until_password_changed(
    client, make_user, auth_headers
):
    u = await make_user(must_change_password=True)
    r = await client.get(f"/users/{u.id}", headers=await auth_headers(u))
    assert r.status_code == 403


async def test_update_own_profile(client, make_user, auth_headers):
    u = await make_user(user_type=UserType.EXTENSION_WORKER)
    r = await client.put(
        f"/users/{u.id}",
        headers=await auth_headers(u),
        json={"first_name": "Renamed"},
    )
    assert r.status_code == 200
    assert r.json()["first_name"] == "Renamed"


async def test_update_other_user_forbidden_for_non_privileged(
    client, make_user, auth_headers
):
    worker = await make_user(user_type=UserType.EXTENSION_WORKER)
    other = await make_user(user_type=UserType.FARMER)
    r = await client.put(
        f"/users/{other.id}",
        headers=await auth_headers(worker),
        json={"first_name": "Hacked"},
    )
    assert r.status_code == 403


async def test_admin_can_update_other_user(client, make_user, auth_headers):
    admin = await make_user()
    other = await make_user(user_type=UserType.FARMER)
    r = await client.put(
        f"/users/{other.id}",
        headers=await auth_headers(admin),
        json={"last_name": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["last_name"] == "Updated"


async def test_update_to_taken_phone_is_409(client, make_user, auth_headers):
    admin = await make_user()
    taken = await make_user(phone="+263770000555")
    other = await make_user()
    r = await client.put(
        f"/users/{other.id}",
        headers=await auth_headers(admin),
        json={"phone_number": taken.phone_number},
    )
    assert r.status_code == 409


async def test_update_unknown_user_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.put(
        f"/users/{uuid.uuid4()}",
        headers=await auth_headers(admin),
        json={"first_name": "x"},
    )
    assert r.status_code == 404


async def test_update_password_forces_change_on_next_login(
    client, make_user, auth_headers
):
    admin = await make_user()
    target = await make_user(user_type=UserType.SUPERVISOR)
    r = await client.put(
        f"/users/{target.id}",
        headers=await auth_headers(admin),
        json={"password": "ResetByAdmin1"},
    )
    assert r.status_code == 200
    login = await client.post(
        "/auth/login",
        data={"username": target.phone_number, "password": "ResetByAdmin1"},
    )
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True


@pytest.mark.parametrize(
    "payload", [{"phone_number": "bad"}, {"password": "short"}, {"email": "x"}]
)
async def test_update_validation_errors(client, make_user, auth_headers, payload):
    u = await make_user()
    r = await client.put(
        f"/users/{u.id}", headers=await auth_headers(u), json=payload
    )
    assert r.status_code == 422


@pytest.mark.parametrize(
    "role", [UserType.SUPERVISOR, UserType.EXTENSION_WORKER, UserType.FARMER]
)
async def test_delete_forbidden_for_non_admins(
    client, make_user, auth_headers, role
):
    caller = await make_user(user_type=role)
    target = await make_user(user_type=UserType.FARMER)
    r = await client.delete(f"/users/{target.id}", headers=await auth_headers(caller))
    assert r.status_code == 403


async def test_delete_requires_authentication(client, make_user):
    target = await make_user()
    assert (await client.delete(f"/users/{target.id}")).status_code == 401


async def test_delete_unknown_user_is_404(client, make_user, auth_headers):
    admin = await make_user()
    r = await client.delete(
        f"/users/{uuid.uuid4()}", headers=await auth_headers(admin)
    )
    assert r.status_code == 404


async def test_admin_can_delete_user(client, make_user, auth_headers):
    admin = await make_user()
    target = await make_user(user_type=UserType.FARMER)
    r = await client.delete(
        f"/users/{target.id}", headers=await auth_headers(admin)
    )
    assert r.status_code == 200
    assert r.json() == {"message": "User deleted successfully"}
    again = await client.get(
        f"/users/{target.id}", headers=await auth_headers(admin)
    )
    assert again.status_code == 404


async def test_delete_user_with_worker_profile_is_409(
    client, make_user, make_worker, auth_headers
):
    admin = await make_user()
    worker_user, _ = await make_worker()
    r = await client.delete(
        f"/users/{worker_user.id}", headers=await auth_headers(admin)
    )
    assert r.status_code == 409
