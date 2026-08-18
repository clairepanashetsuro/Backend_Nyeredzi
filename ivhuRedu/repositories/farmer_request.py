import uuid
from typing import List, Optional

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, cast, String

from ivhuRedu.models.farmer_request import FarmerRequest


class FarmerRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request_data: dict) -> FarmerRequest:
        db_request = FarmerRequest(**request_data)

        self.db.add(db_request)

        await self.db.commit()
        await self.db.refresh(db_request)

        return db_request

    async def create_multiple(
        self,
        requests_data: List[dict]
    ) -> List[FarmerRequest]:

        created = []

        for data in requests_data:
            db_request = FarmerRequest(**data)

            self.db.add(db_request)
            created.append(db_request)

        await self.db.commit()

        for req in created:
            await self.db.refresh(req)

        return created

    async def get_by_phone(
        self,
        phone_number: str
    ) -> List[FarmerRequest]:

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.phone_number == phone_number
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[FarmerRequest]:

        stmt = (
            select(FarmerRequest)
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def get_by_farmer_id(
        self,
        farmer_id: uuid.UUID
    ) -> List[FarmerRequest]:

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.farmer_id == farmer_id
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def get_by_id(
        self,
        request_id: uuid.UUID
    ) -> Optional[FarmerRequest]:

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.request_id == request_id
            )
        )

        result = await self.db.execute(stmt)

        return result.scalars().first()

    async def update(
        self,
        db_request: FarmerRequest,
        update_data: dict
    ) -> FarmerRequest:

        for field, value in update_data.items():
            setattr(db_request, field, value)

        await self.db.commit()
        await self.db.refresh(db_request)

        return db_request

    async def delete(
        self,
        db_request: FarmerRequest
    ) -> None:

        await self.db.delete(db_request)

        await self.db.commit()

    async def search_by_keyword(
        self,
        keyword: str
    ) -> List[FarmerRequest]:

        search = f"%{keyword}%"

        stmt = (
            select(FarmerRequest)
            .filter(
                or_(
                    cast(FarmerRequest.request_type, String).ilike(search),
                    cast(FarmerRequest.status, String).ilike(search),
                    FarmerRequest.phone_number.ilike(search),
                    FarmerRequest.description.ilike(search),
                    FarmerRequest.location.ilike(search)
                )
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def assign_to_worker(
        self,
        request_ids: List[uuid.UUID],
        worker_id: uuid.UUID
    ) -> List[FarmerRequest]:

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.request_id.in_(request_ids)
            )
        )

        result = await self.db.execute(stmt)

        requests = result.scalars().all()

        for req in requests:
            req.assigned_worker_id = worker_id
            req.status = "assigned"

        await self.db.commit()

        for req in requests:
            await self.db.refresh(req)

        return list(requests)

    async def remove_duplicates(self) -> int:

        subquery = (
            select(
                FarmerRequest.phone_number,
                FarmerRequest.request_type,
                FarmerRequest.status,
                func.min(
                    FarmerRequest.created_at
                ).label("min_created")
            )
            .group_by(
                FarmerRequest.phone_number,
                FarmerRequest.request_type,
                FarmerRequest.status
            )
            .having(
                func.count(
                    FarmerRequest.request_id
                ) > 1
            )
            .subquery()
        )

        stmt = (
            select(FarmerRequest)
            .join(
                subquery,
                (
                    FarmerRequest.phone_number ==
                    subquery.c.phone_number
                )
                &
                (
                    FarmerRequest.request_type ==
                    subquery.c.request_type
                )
                &
                (
                    FarmerRequest.status ==
                    subquery.c.status
                )
                &
                (
                    FarmerRequest.created_at >
                    subquery.c.min_created
                )
            )
        )

        result = await self.db.execute(stmt)

        duplicates = result.scalars().all()

        count = len(duplicates)

        for dup in duplicates:
            await self.db.delete(dup)

        await self.db.commit()

        return count


    async def create_ussd_request(
        self,
        phone_number: str,
        request_type: str,
        description: str,
        location: str,
        ussd_session_id: str,
        farmer_id: Optional[uuid.UUID] = None
    ) -> FarmerRequest:
        """
        Create a request submitted through USSD.
        """

        request_data = {
            "phone_number": phone_number,
            "request_type": request_type,
            "description": description,
            "location": location,
            "ussd_session_id": ussd_session_id,
            "status": "pending",
        }

        if farmer_id is not None:
            request_data["farmer_id"] = farmer_id

        return await self.create(request_data)

    async def get_ussd_requests_by_phone(
        self,
        phone_number: str,
        limit: int = 5
    ) -> List[FarmerRequest]:
        """
        Get the farmer's latest USSD requests.
        """

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.phone_number == phone_number
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def get_ussd_request_by_session(
        self,
        session_id: str
    ) -> Optional[FarmerRequest]:
        """
        Find a request using the Africa's Talking USSD session ID.
        """

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.ussd_session_id == session_id
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
        )

        result = await self.db.execute(stmt)

        return result.scalars().first()

    async def get_reports_by_phone(
        self,
        phone_number: str,
        limit: int = 5
    ) -> List[FarmerRequest]:
        """
        Get land degradation reports belonging to a farmer.
        """

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.phone_number == phone_number
            )
            .filter(
                FarmerRequest.request_type.ilike(
                    "%Land Degradation%"
                )
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def get_reports_by_ward(
        self,
        ward_number: str,
        limit: int = 10
    ) -> List[FarmerRequest]:
        """
        Get land degradation reports for a ward.

        The ward is stored in the existing location column.
        """

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.location == ward_number
            )
            .filter(
                FarmerRequest.request_type.ilike(
                    "%Land Degradation%"
                )
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def get_active_requests_by_phone(
        self,
        phone_number: str
    ) -> List[FarmerRequest]:
        """
        Get active requests belonging to a farmer.
        """

        stmt = (
            select(FarmerRequest)
            .filter(
                FarmerRequest.phone_number == phone_number
            )
            .filter(
                FarmerRequest.status.in_(
                    [
                        "pending",
                        "assigned",
                        "in_progress"
                    ]
                )
            )
            .order_by(
                FarmerRequest.created_at.desc()
            )
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())