from uuid import UUID

from sqlalchemy.orm import Session

from ivhuRedu.models.farmer import Farmer


class FarmerRepository:

    def __init__(self, db: Session):
        self.db = db


    
    def create_farmer(self, farmer: Farmer) -> Farmer:
        self.db.add(farmer)
        self.db.commit()
        self.db.refresh(farmer)

        return farmer



    def get_by_id(self, farmer_id: UUID) -> Farmer | None:
        return (
            self.db.query(Farmer)
            .filter(Farmer.farmer_id == farmer_id)
            .first()
        )


    
    def get_by_user_id(self, user_id: UUID) -> Farmer | None:
        return (
            self.db.query(Farmer)
            .filter(Farmer.user_id == user_id)
            .first()
        )


    
    def exists_by_user_id(self, user_id: UUID) -> bool:
        return (
            self.db.query(Farmer)
            .filter(Farmer.user_id == user_id)
            .first()
            is not None
        )


    
    def get_by_location(self, location_id: UUID) -> list[Farmer]:
        return (
            self.db.query(Farmer)
            .filter(Farmer.location_id == location_id)
            .all()
        )


    def update_farmer(
        self,
        farmer_id: UUID,
        ward_name: str | None = None,
        location_id: UUID | None = None
    ) -> Farmer | None:

        farmer = self.get_by_id(farmer_id)

        if not farmer:
            return None

        if ward_name:
            farmer.ward_name = ward_name

        if location_id:
            farmer.location_id = location_id

        self.db.commit()
        self.db.refresh(farmer)

        return farmer