import math
import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.extension_worker import (
    ExtensionWorker,
    WorkerAvailabilityStatus,
)
from ivhuRedu.models.farmer_request import (
    FarmerRequest,
    RequestStatus,
)
from ivhuRedu.repositories.farmer_request import FarmerRequestRepository
from ivhuRedu.schemas.farmer_request import (
    FarmerRequestCreate,
    FarmerRequestUpdate,
)


class FarmerRequestService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FarmerRequestRepository(db)

    @staticmethod
    def calculate_distance(
        latitude1: float,
        longitude1: float,
        latitude2: float,
        longitude2: float,
    ) -> float:

        earth_radius = 6_371_000

        lat1 = math.radians(latitude1)
        lat2 = math.radians(latitude2)

        delta_lat = math.radians(latitude2 - latitude1)
        delta_lon = math.radians(longitude2 - longitude1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(delta_lon / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )

        return earth_radius * c

    async def assign_nearest_worker(
        self,
        farmer_id: uuid.UUID,
    ):
        farmer_result = await self.db.execute(
            select(Farmer)
            .options(selectinload(Farmer.location))
            .where(Farmer.farmer_id == farmer_id)
        )

        farmer = farmer_result.scalar_one_or_none()

        if not farmer:
            raise ValueError("Farmer not found")

        if not farmer.location:
            raise ValueError("Farmer location not found")

        farmer_lat = farmer.location.latitude
        farmer_lon = farmer.location.longitude

        worker_result = await self.db.execute(
            select(ExtensionWorker)
            .options(selectinload(ExtensionWorker.location))
            .where(
                ExtensionWorker.availability_status
                == WorkerAvailabilityStatus.AVAILABLE
            )
        )

        workers = worker_result.scalars().all()

        if not workers:
            return None

        nearest_worker = None
        nearest_distance = float("inf")

        for worker in workers:

            if not worker.location:
                continue

            worker_lat = worker.location.latitude
            worker_lon = worker.location.longitude

            distance = self.calculate_distance(
                farmer_lat,
                farmer_lon,
                worker_lat,
                worker_lon,
            )

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_worker = worker

        if not nearest_worker:
            return None

        return {
            "worker_id": nearest_worker.worker_id,
            "distance_in_meters": round(
                nearest_distance,
                2,
            ),
        }

    async def create_farmer_request(
        self,
        request_in: FarmerRequestCreate,
    ):

        request_data = {
            "phone_number": request_in.phone_number,
            "request_type": request_in.request_type,
            "ussd_session_id": request_in.ussd_session_id,
            "status": request_in.status or RequestStatus.PENDING,
            "description": request_in.description,
            "location": request_in.location,
            "farmer_id": request_in.farmer_id,
        }

        db_request = await self.repo.create(request_data)

        if request_in.farmer_id:

            assignment = await self.assign_nearest_worker(
                request_in.farmer_id
            )

            if assignment:

                db_request.assigned_worker_id = (
                    assignment["worker_id"]
                )

                db_request.distance_in_meters = (
                    assignment["distance_in_meters"]
                )

                db_request.status = RequestStatus.ASSIGNED

                await self.db.commit()
                await self.db.refresh(db_request)

        return db_request

    async def create_multiple_farmer_requests(
        self,
        requests_in: List[FarmerRequestCreate],
    ):

        created = []

        for request_in in requests_in:
            request = await self.create_farmer_request(
                request_in
            )
            created.append(request)

        return created

    async def get_all_farmer_requests(
        self,
        skip: int = 0,
        limit: int = 100,
    ):

        return await self.repo.get_all(
            skip,
            limit,
        )

    async def get_requests_by_specific_farmer(
        self,
        farmer_id: uuid.UUID,
    ):

        return await self.repo.get_by_farmer_id(
            farmer_id
        )

    async def get_farmer_request_by_id(
        self,
        request_id: uuid.UUID,
    ):

        request = await self.repo.get_by_id(
            request_id
        )

        if not request:
            raise ValueError("Farmer request not found")

        return request

    async def update_farmer_request_details(
        self,
        request_id: uuid.UUID,
        request_in: FarmerRequestUpdate,
    ):

        request = await self.repo.get_by_id(
            request_id
        )

        if not request:
            raise ValueError("Farmer request not found")

        update_data = request_in.model_dump(
            exclude_unset=True
        )

        return await self.repo.update(
            request,
            update_data,
        )

    async def delete_farmer_request_record(
        self,
        request_id: uuid.UUID,
    ):

        request = await self.repo.get_by_id(
            request_id
        )

        if not request:
            raise ValueError("Farmer request not found")

        await self.repo.delete(request)

    async def remove_duplicate_requests(self):

        return await self.repo.remove_duplicates()

    async def search_requests_by_ussd_keyword(
        self,
        keyword: str,
    ):

        return await self.repo.search_by_keyword(
            keyword
        )

    async def assign_requests_to_worker_batch(
        self,
        request_ids: List[uuid.UUID],
        worker_id: uuid.UUID,
    ):

        return await self.repo.assign_to_worker(
            request_ids,
            worker_id,
        )
