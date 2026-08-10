import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ivhuRedu.models.user import User, UserType
from ivhuRedu.models.farmer import Farmer

from ivhuRedu.repositories.user import user_repository

from ivhuRedu.schemas.farmer import FarmerCreate


logger = logging.getLogger(__name__)





def create_farmer(
    db: Session,
    data: FarmerCreate,
):
    


    

    existing_user = user_repository.get_by_phone_number(
        db,
        data.phone_number,
    )


    if existing_user:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists.",
        )



    user = User(

        first_name=data.first_name,

        last_name=data.last_name,

        phone_number=data.phone_number,

        user_type=UserType.FARMER,

        # Farmers do not login through dashboard
        hashed_password=None,

        must_change_password=False,
    )


    db.add(user)

    db.flush()



    

    farmer = Farmer(

        user_id=user.id,

        ward_name=data.ward_name,

        location_id=data.location_id,
    )


    db.add(farmer)



    try:

        db.commit()

        db.refresh(farmer)

        return farmer


    except IntegrityError:

        db.rollback()

        logger.exception(
            "Failed creating farmer"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Farmer could not be created.",
        )


import uuid




def get_farmer(
    db: Session,
    farmer_id: uuid.UUID,
):
    farmer = (
        db.query(Farmer)
        .filter(Farmer.farmer_id == farmer_id)
        .first()
    )

    if not farmer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found.",
        )

    return farmer




def update_farmer(
    db: Session,
    farmer_id: uuid.UUID,
    data: dict,
):
    farmer = get_farmer(
        db,
        farmer_id,
    )

    user = farmer.user

    user_fields = {
        "first_name",
        "last_name",
        "phone_number",
        
    }

    farmer_fields = {
        "ward_name",
        "location_id",
    }

    for field, value in data.items():

        if field in user_fields:
            setattr(user, field, value)

        elif field in farmer_fields:
            setattr(farmer, field, value)

    try:

        db.commit()

        db.refresh(farmer)

        return farmer

    except IntegrityError:

        db.rollback()

        logger.exception(
            "Failed updating farmer."
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Farmer could not be updated.",
        )

def delete_farmer(
    db: Session,
    farmer_id: uuid.UUID,
):
    farmer = get_farmer(db, farmer_id)

    user = farmer.user

    db.delete(farmer)
    db.delete(user)

    db.commit()
    return {
        "message": "Farmer deleted successfully."
    }