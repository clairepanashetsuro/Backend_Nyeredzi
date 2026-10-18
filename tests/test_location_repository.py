import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from ivhuRedu.repositories.location import LocationRepository
from ivhuRedu.schemas.location import LocationCreate, LocationUpdate


@pytest.fixture
def repo(session):
    return LocationRepository(session)


def payload(**overrides):
    data = dict(latitude=-17.8, longitude=31.0, address="Harare")
    data.update(overrides)
    return LocationCreate(**data)


async def test_create_persists_location(repo):
    location = await repo.create(payload(display_name="Capital"))
    assert location.location_id is not None
    assert location.address == "Harare"
    assert location.display_name == "Capital"
    assert location.created_at is not None


async def test_get_all_empty_and_populated(repo):
    assert await repo.get_all() == []
    await repo.create(payload())
    await repo.create(payload(address="Bulawayo"))
    assert {loc.address for loc in await repo.get_all()} == {"Harare", "Bulawayo"}


async def test_get_by_id_found_and_missing(repo):
    location = await repo.create(payload())
    assert (await repo.get_by_id(location.location_id)).address == "Harare"
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_update_changes_only_provided_fields(repo):
    location = await repo.create(payload(display_name="Keep me"))
    updated = await repo.update(
        location.location_id, LocationUpdate(address="Mutare")
    )
    assert updated.address == "Mutare"
    assert updated.display_name == "Keep me"
    assert updated.latitude == -17.8


async def test_update_explicit_none_clears_optional_field(repo):
    location = await repo.create(payload(display_name="Clear me"))
    updated = await repo.update(
        location.location_id, LocationUpdate(display_name=None)
    )
    assert updated.display_name is None


async def test_update_coordinates(repo):
    location = await repo.create(payload())
    updated = await repo.update(
        location.location_id, LocationUpdate(latitude=1.5, longitude=2.5)
    )
    assert (updated.latitude, updated.longitude) == (1.5, 2.5)


async def test_update_unknown_id_returns_none(repo):
    assert await repo.update(uuid.uuid4(), LocationUpdate(address="x")) is None


async def test_delete_removes_location(repo):
    location = await repo.create(payload())
    assert await repo.delete(location.location_id) is True
    assert await repo.get_by_id(location.location_id) is None


async def test_delete_unknown_id_returns_false(repo):
    assert await repo.delete(uuid.uuid4()) is False


async def test_delete_location_in_use_by_farmer_raises(repo, make_farmer):
    _, farmer = await make_farmer()
    with pytest.raises(IntegrityError):
        await repo.delete(farmer.location_id)
