from ivhuRedu.models.field_image import FieldImage
from ivhuRedu.models.field_report import FieldReport


async def create_report(session_factory, worker_id, **overrides):
    data = dict(worker_id=worker_id, description_type="pest")
    data.update(overrides)
    async with session_factory() as s:
        report = FieldReport(**data)
        s.add(report)
        await s.commit()
        return report


async def create_image(session_factory, report_id, url="secure_storage/x.enc"):
    async with session_factory() as s:
        image = FieldImage(report_id=report_id, image_url=url)
        s.add(image)
        await s.commit()
        return image
