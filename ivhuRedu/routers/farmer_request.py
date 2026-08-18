import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from ivhuRedu.schemas.farmer_request import (
    FarmerRequestCreate,
    FarmerRequestUpdate,
)
from ivhuRedu.services.farmer_request import FarmerRequestService

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
async def create_farmer_request(
    request_in: FarmerRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(db).create_farmer_request(
        request_in
    )


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
)
async def create_multiple_farmer_requests(
    requests_in: List[FarmerRequestCreate],
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(db).create_multiple_farmer_requests(
        requests_in
    )


@router.post(
    "/duplicates/cleanup",
    status_code=status.HTTP_200_OK,
)
async def remove_duplicate_requests(
    db: AsyncSession = Depends(get_db),
):
    removed_count = await FarmerRequestService(
        db
    ).remove_duplicate_requests()

    return {
        "message": (
            f"Successfully removed "
            f"{removed_count} duplicate farmer requests."
        )
    }


@router.get("/search")
async def search_requests_by_ussd_keyword(
    keyword: str,
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(
        db
    ).search_requests_by_ussd_keyword(keyword)


@router.post("/assign")
async def assign_requests_to_worker_batch(
    request_ids: List[uuid.UUID],
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(
        db
    ).assign_requests_to_worker_batch(
        request_ids,
        worker_id,
    )


@router.get("/")
async def get_all_farmer_requests(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(
        db
    ).get_all_farmer_requests(
        skip,
        limit,
    )


@router.get("/farmer/{farmer_id}")
async def get_farmer_requests_by_farmer_id(
    farmer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(
        db
    ).get_requests_by_specific_farmer(
        farmer_id
    )


@router.get("/{request_id}")
async def get_farmer_request_by_request_id(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(
        db
    ).get_farmer_request_by_id(
        request_id
    )


@router.patch("/{request_id}")
async def update_farmer_request(
    request_id: uuid.UUID,
    request_in: FarmerRequestUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await FarmerRequestService(
        db
    ).update_farmer_request_details(
        request_id,
        request_in,
    )


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_farmer_request_record(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await FarmerRequestService(
        db
    ).delete_farmer_request_record(
        request_id
    )

    return None
