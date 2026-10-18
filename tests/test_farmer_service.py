import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.user import User, UserType
from ivhuRedu.schemas.farmer import FarmerCreate
from ivhuRedu.services import farmer as farmer_service


def payload(location_id, **overrides):
    data = dict(
        first_name="Chipo",
        last_name="Ncube",
        phone_number="+263772220000",
        primary_crop="maize",
        ward_name="Ward 4",
        location_id=location_id,
    )
    data.update(overrides)
    return FarmerCreate(**data)


async def test_create_farmer_creates_user_and_profile(session, make_location):
    loc = await make_location()
    farmer = await farmer_service.create_farmer(session, payload(loc.location_id))
    assert farmer.ward_name == "Ward 4" and farmer.primary_crop == "maize"
    assert farmer.location.location_id == loc.location_id
    assert farmer.user.user_type is UserType.FARMER
    assert farmer.user.hashed_password is None
    assert farmer.user.must_change_password is False
    assert farmer.user.phone_number == "+263772220000"


async def test_create_farmer_primary_crop_is_optional(session, make_location):
    loc = await make_location()
    farmer = await farmer_service.create_farmer(
        session, payload(loc.location_id, primary_crop=None)
    )
    assert farmer.primary_crop is None


async def test_create_farmer_duplicate_phone_is_409(
    session, make_user, make_location
):
    loc = await make_location()
    await make_user(phone="+263772220000")
    with pytest.raises(HTTPException) as exc:
        await farmer_service.create_farmer(session, payload(loc.location_id))
    assert exc.value.status_code == 409


async def test_create_farmer_unknown_location_is_409_and_leaves_no_user(session):
    with pytest.raises(HTTPException) as exc:
        await farmer_service.create_farmer(session, payload(uuid.uuid4()))
    assert exc.value.status_code == 409
    assert exc.value.detail == "Farmer could not be created."
    users = await session.execute(select(User))
    assert users.first() is None


async def test_get_farmer_returns_user_and_location(session, make_farmer):
    user, farmer = await make_farmer()
    found = await farmer_service.get_farmer(session, farmer.farmer_id)
    assert found.user.id == user.id
    assert found.location.location_id == farmer.location_id


async def test_get_farmer_unknown_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await farmer_service.get_farmer(session, uuid.uuid4())
    assert exc.value.status_code == 404


async def test_update_farmer_changes_user_and_profile_fields(session, make_farmer):
    _, farmer = await make_farmer()
    updated = await farmer_service.update_farmer(
        session,
        farmer.farmer_id,
        {"first_name": "Renamed", "ward_name": "Ward 99", "primary_crop": "wheat"},
    )
    assert updated.ward_name == "Ward 99" and updated.primary_crop == "wheat"
    refreshed = await farmer_service.get_farmer(session, farmer.farmer_id)
    assert refreshed.user.first_name == "Renamed"


async def test_update_farmer_changes_location(session, make_farmer, make_location):
    _, farmer = await make_farmer()
    new_loc = await make_location(address="Masvingo")
    updated = await farmer_service.update_farmer(
        session, farmer.farmer_id, {"location_id": new_loc.location_id}
    )
    assert updated.location_id == new_loc.location_id


async def test_update_farmer_ignores_unknown_fields(session, make_farmer):
    user, farmer = await make_farmer()
    await farmer_service.update_farmer(
        session, farmer.farmer_id, {"user_type": "admin", "is_locked": True}
    )
    refreshed = await farmer_service.get_farmer(session, farmer.farmer_id)
    assert refreshed.user.user_type is UserType.FARMER
    assert refreshed.user.is_locked is False


async def test_update_farmer_to_taken_phone_is_409(session, make_farmer, make_user):
    await make_user(phone="+263773330000")
    _, farmer = await make_farmer()
    with pytest.raises(HTTPException) as exc:
        await farmer_service.update_farmer(
            session, farmer.farmer_id, {"phone_number": "+263773330000"}
        )
    assert exc.value.status_code == 409


async def test_update_farmer_keeping_own_phone_is_allowed(session, make_farmer):
    user, farmer = await make_farmer()
    updated = await farmer_service.update_farmer(
        session, farmer.farmer_id, {"phone_number": user.phone_number}
    )
    assert updated.farmer_id == farmer.farmer_id


async def test_update_farmer_unknown_location_is_409(session, make_farmer):
    _, farmer = await make_farmer()
    with pytest.raises(HTTPException) as exc:
        await farmer_service.update_farmer(
            session, farmer.farmer_id, {"location_id": uuid.uuid4()}
        )
    assert exc.value.status_code == 409


async def test_update_farmer_unknown_id_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await farmer_service.update_farmer(session, uuid.uuid4(), {"ward_name": "x"})
    assert exc.value.status_code == 404


async def test_delete_farmer_removes_profile_and_user(session, make_farmer):
    user, farmer = await make_farmer()
    result = await farmer_service.delete_farmer(session, farmer.farmer_id)
    assert result == {"message": "Farmer deleted successfully."}
    assert (
        await session.execute(select(Farmer).where(Farmer.farmer_id == farmer.farmer_id))
    ).first() is None
    assert (await session.execute(select(User).where(User.id == user.id))).first() is None


async def test_delete_farmer_unknown_id_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await farmer_service.delete_farmer(session, uuid.uuid4())
    assert exc.value.status_code == 404
