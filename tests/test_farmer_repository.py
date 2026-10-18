import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.user import UserType
from ivhuRedu.repositories.farmer import FarmerRepository


@pytest.fixture
def repo(session):
    return FarmerRepository(session)


async def test_create_farmer_persists_and_returns_it(
    repo, make_user, make_location
):
    user = await make_user(user_type=UserType.FARMER)
    location = await make_location()
    farmer = await repo.create_farmer(
        Farmer(
            user_id=user.id,
            ward_name="Ward 7",
            primary_crop="beans",
            location_id=location.location_id,
        )
    )
    assert farmer.farmer_id is not None
    assert farmer.created_at is not None
    assert (await repo.get_by_id(farmer.farmer_id)).ward_name == "Ward 7"


async def test_create_farmer_twice_for_same_user_raises(repo, make_farmer):
    user, farmer = await make_farmer()
    with pytest.raises(IntegrityError):
        await repo.create_farmer(
            Farmer(
                user_id=user.id,
                ward_name="Other",
                location_id=farmer.location_id,
            )
        )


async def test_get_by_id_unknown_returns_none(repo):
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_get_by_user_id_finds_farmer(repo, make_farmer):
    user, farmer = await make_farmer()
    assert (await repo.get_by_user_id(user.id)).farmer_id == farmer.farmer_id


async def test_get_by_user_id_unknown_returns_none(repo):
    assert await repo.get_by_user_id(uuid.uuid4()) is None


async def test_get_all_empty_and_populated(repo, make_farmer):
    assert await repo.get_all() == []
    await make_farmer()
    await make_farmer()
    assert len(await repo.get_all()) == 2


async def test_exists_by_user_id(repo, make_farmer, make_user):
    user, _ = await make_farmer()
    other = await make_user(user_type=UserType.FARMER)
    assert await repo.exists_by_user_id(user.id) is True
    assert await repo.exists_by_user_id(other.id) is False


async def test_update_farmer_changes_ward_name(repo, make_farmer):
    _, farmer = await make_farmer()
    updated = await repo.update_farmer(farmer.farmer_id, ward_name="New Ward")
    assert updated.ward_name == "New Ward"
    assert updated.location_id == farmer.location_id


async def test_update_farmer_changes_location(repo, make_farmer, make_location):
    _, farmer = await make_farmer()
    new_location = await make_location(address="Bulawayo")
    updated = await repo.update_farmer(
        farmer.farmer_id, location_id=new_location.location_id
    )
    assert updated.location_id == new_location.location_id
    assert updated.ward_name == farmer.ward_name


async def test_update_farmer_with_no_changes_keeps_values(repo, make_farmer):
    _, farmer = await make_farmer()
    updated = await repo.update_farmer(farmer.farmer_id)
    assert updated.ward_name == farmer.ward_name
    assert updated.location_id == farmer.location_id


async def test_update_farmer_unknown_id_returns_none(repo):
    assert await repo.update_farmer(uuid.uuid4(), ward_name="x") is None


async def test_update_farmer_to_missing_location_raises(repo, make_farmer):
    _, farmer = await make_farmer()
    with pytest.raises(IntegrityError):
        await repo.update_farmer(farmer.farmer_id, location_id=uuid.uuid4())
