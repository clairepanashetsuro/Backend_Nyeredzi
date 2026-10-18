import uuid

import pytest

from ivhuRedu.models.extension_worker import ExtensionWorker
from ivhuRedu.models.user import UserType
from ivhuRedu.repositories.extension_worker import ExtensionWorkerRepository


@pytest.fixture
def repo(session):
    return ExtensionWorkerRepository(session)


async def test_create_extension_worker_persists_and_returns_it(
    repo, make_user, make_location
):
    user = await make_user(user_type=UserType.EXTENSION_WORKER)
    location = await make_location()
    worker = await repo.create_extension_worker(
        ExtensionWorker(
            user_id=user.id,
            hashed_ussd_pincode="hashed",
            assigned_ward_name="Ward 3",
            location_id=location.location_id,
        )
    )
    assert worker.worker_id is not None
    assert worker.assigned_ward_name == "Ward 3"


async def test_get_by_id_returns_worker(repo, make_worker):
    _, worker = await make_worker()
    assert (await repo.get_by_id(worker.worker_id)).worker_id == worker.worker_id


async def test_get_by_id_unknown_returns_none(repo):
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_get_by_user_id_finds_worker(repo, make_worker):
    user, worker = await make_worker()
    assert (await repo.get_by_user_id(user.id)).worker_id == worker.worker_id


async def test_get_by_user_id_unknown_returns_none(repo):
    assert await repo.get_by_user_id(uuid.uuid4()) is None


async def test_get_all_empty_and_populated(repo, make_worker):
    assert await repo.get_all() == []
    await make_worker()
    await make_worker()
    assert len(await repo.get_all()) == 2


async def test_exists_by_user_id(repo, make_worker, make_user):
    user, _ = await make_worker()
    other = await make_user(user_type=UserType.EXTENSION_WORKER)
    assert await repo.exists_by_user_id(user.id) is True
    assert await repo.exists_by_user_id(other.id) is False


async def test_update_extension_worker_changes_assigned_ward(repo, make_worker):
    _, worker = await make_worker()
    updated = await repo.update_extension_worker(
        worker.worker_id, ward_name="Ward 9"
    )
    assert updated.assigned_ward_name == "Ward 9"
    assert updated.location_id == worker.location_id


async def test_update_extension_worker_changes_location(
    repo, make_worker, make_location
):
    _, worker = await make_worker()
    new_location = await make_location(address="Gweru")
    updated = await repo.update_extension_worker(
        worker.worker_id, location_id=new_location.location_id
    )
    assert updated.location_id == new_location.location_id
    assert updated.assigned_ward_name == worker.assigned_ward_name


async def test_update_extension_worker_without_changes_keeps_values(
    repo, make_worker
):
    _, worker = await make_worker()
    updated = await repo.update_extension_worker(worker.worker_id)
    assert updated.assigned_ward_name == worker.assigned_ward_name


async def test_update_extension_worker_unknown_id_returns_none(repo):
    assert await repo.update_extension_worker(uuid.uuid4(), ward_name="x") is None
