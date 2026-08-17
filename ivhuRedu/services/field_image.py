import os
from uuid import UUID, uuid4
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.repositories.field_image import FieldImageRepository
from ivhuRedu.schemas.field_image import ReportImageCreate, ReportImageResponse
from ivhuRedu.utils.crypto import encrypt_file_data, decrypt_file_data  

SECURE_STORAGE_DIR = os.path.join(os.getcwd(), "secure_storage")
os.makedirs(SECURE_STORAGE_DIR, exist_ok=True)


class FieldImageService:

    def __init__(self, db: AsyncSession):
        self.repo = FieldImageRepository(db)

    async def encrypt_and_store_image(self, report_id: UUID, file: UploadFile) -> ReportImageResponse:
        raw_data = await file.read()
        encrypted_data = encrypt_file_data(raw_data)
        
        secure_filename = f"{uuid4()}.enc"
        physical_path = os.path.join(SECURE_STORAGE_DIR, secure_filename)
        
        with open(physical_path, "wb") as buffer:
            buffer.write(encrypted_data)
            
        image_data = ReportImageCreate(report_id=report_id, file_url=physical_path)
        db_model = await self.repo.create(image_data)
        
        return ReportImageResponse(
            image_id=db_model.image_id,
            report_id=db_model.report_id,
            file_url=db_model.image_url,
            uploaded_at=db_model.uploaded_at
        )

   
    async def get_decrypted_image_bytes(self, image_id: UUID) -> bytes:
        db_model = await self.repo.get_by_id(image_id)
        if not db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record missing")
        
        if not os.path.exists(db_model.image_url):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Physical encrypted file could not be found on server disk"
            )
            
        
        with open(db_model.image_url, "rb") as f:
            encrypted_bytes = f.read()
            
       
        return decrypt_file_data(encrypted_bytes)

    async def get_images_by_report(self, report_id: UUID) -> list[ReportImageResponse]:
        db_models = await self.repo.get_by_report_id(report_id)
        return [
            ReportImageResponse(
                image_id=model.image_id,
                report_id=model.report_id,
                file_url=model.image_url,
                uploaded_at=model.uploaded_at
            )
            for model in db_models
        ]

    async def get_image(self, image_id: UUID) -> ReportImageResponse:
        db_model = await self.repo.get_by_id(image_id)
        if not db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record missing")
        return ReportImageResponse(
            image_id=db_model.image_id,
            report_id=db_model.report_id,
            file_url=db_model.image_url,
            uploaded_at=db_model.uploaded_at
        )

    async def update_image(self, image_id: UUID, data) -> ReportImageResponse:
        db_model = await self.repo.update(image_id, data)
        if not db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record missing")
        return ReportImageResponse(
            image_id=db_model.image_id,
            report_id=db_model.report_id,
            file_url=db_model.image_url,
            uploaded_at=db_model.uploaded_at
        )

    async def delete_image(self, image_id: UUID) -> None:
        db_model = await self.repo.get_by_id(image_id)
        if not db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record missing")
        
        if os.path.exists(db_model.image_url):
            os.remove(db_model.image_url)
            
        await self.repo.delete(image_id)
