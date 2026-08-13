import uuid
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, delete

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

    async def create_multiple(self, requests_data: List[dict]) -> List[FarmerRequest]:
        created = []
        for data in requests_data:
            db_request = FarmerRequest(**data)
            self.db.add(db_request)
            created.append(db_request)
        await self.db.commit()
        for req in created:
            await self.db.refresh(req)
        return created

    async def get_by_phone(self, phone_number: str) -> List[FarmerRequest]:
        stmt = (
            select(FarmerRequest)
            .filter(FarmerRequest.phone_number == phone_number)
            .order_by(FarmerRequest.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[FarmerRequest]:
        stmt = select(FarmerRequest).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_farmer_id(self, farmer_id: uuid.UUID) -> List[FarmerRequest]:
        stmt = (
            select(FarmerRequest)
            .filter(FarmerRequest.farmer_id == farmer_id)
            .order_by(FarmerRequest.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, request_id: uuid.UUID) -> Optional[FarmerRequest]:
        stmt = select(FarmerRequest).filter(FarmerRequest.request_id == request_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update(self, db_request: FarmerRequest, update_data: dict) -> FarmerRequest:
        for field, value in update_data.items():
            setattr(db_request, field, value)
        await self.db.commit()
        await self.db.refresh(db_request)
        return db_request

    async def delete(self, db_request: FarmerRequest) -> None:
        await self.db.delete(db_request)
        await self.db.commit()

    async def search_by_keyword(self, keyword: str) -> List[FarmerRequest]:
        search = f"%{keyword}%"
        stmt = (
            select(FarmerRequest)
            .filter(
                or_(
                    FarmerRequest.request_type.ilike(search),
                    FarmerRequest.status.ilike(search),
                    FarmerRequest.phone_number.ilike(search),
                    FarmerRequest.description.ilike(search),
                    FarmerRequest.location.ilike(search)
                )
            )
            .order_by(FarmerRequest.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def assign_to_worker(self, request_ids: List[uuid.UUID], worker_id: uuid.UUID) -> List[FarmerRequest]:
        stmt = select(FarmerRequest).filter(FarmerRequest.request_id.in_(request_ids))
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
                func.min(FarmerRequest.created_at).label("min_created")
            )
            .group_by(
                FarmerRequest.phone_number,
                FarmerRequest.request_type,
                FarmerRequest.status
            )
            .having(func.count(FarmerRequest.request_id) > 1)
            .subquery()
        )

        stmt = (
            select(FarmerRequest)
            .join(
                subquery,
                (FarmerRequest.phone_number == subquery.c.phone_number) &
                (FarmerRequest.request_type == subquery.c.request_type) &
                (FarmerRequest.status == subquery.c.status) &
                (FarmerRequest.created_at > subquery.c.min_created)
            )
        )
        result = await self.db.execute(stmt)
        duplicates = result.scalars().all()

        count = len(duplicates)
        for dup in duplicates:
            await self.db.delete(dup)

        await self.db.commit()
        return count
