import itertools
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _generate_rsa_pair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


TEST_PRIVATE_PEM, TEST_PUBLIC_PEM = _generate_rsa_pair()
OTHER_PRIVATE_PEM, _ = _generate_rsa_pair()

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["JWT_ALGORITHM"] = "RS256"
os.environ["JWT_PRIVATE_KEY"] = TEST_PRIVATE_PEM
os.environ["JWT_PUBLIC_KEY"] = TEST_PUBLIC_PEM
os.environ["FILE_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["ADMIN_PHONE_NUMBER"] = ""
os.environ["ADMIN_PASSWORD"] = ""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import DateTime, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool

import database
from database import Base
from ivhuRedu import models as _models
from ivhuRedu.models.user import User, UserType
from ivhuRedu.models.location import Location
from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.extension_worker import ExtensionWorker
from ivhuRedu.models.password_reset_otp import PasswordResetOTP
from ivhuRedu.services.security import hash_password, create_access_token


def _attach_utc(target, *_args):
    for column in target.__table__.columns:
        if isinstance(column.type, DateTime):
            value = target.__dict__.get(column.key)
            if isinstance(value, datetime) and value.tzinfo is None:
                target.__dict__[column.key] = value.replace(tzinfo=timezone.utc)


event.listen(Base, "load", _attach_utc, propagate=True)
event.listen(Base, "refresh", _attach_utc, propagate=True)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng.sync_engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


@pytest.fixture
def make_location(session_factory):
    async def _make(**overrides):
        data = dict(latitude=-17.8252, longitude=31.0335, address="Harare, Zimbabwe")
        data.update(overrides)
        async with session_factory() as s:
            obj = Location(**data)
            s.add(obj)
            await s.commit()
            return obj

    return _make


@pytest.fixture
def make_user(session_factory):
    counter = itertools.count(1)

    async def _make(
        user_type=UserType.ADMIN,
        password="Password123",
        phone=None,
        email=None,
        must_change_password=False,
        is_locked=False,
        locked_until=None,
    ):
        n = next(counter)
        async with session_factory() as s:
            user = User(
                first_name="Test",
                last_name=f"User{n}",
                phone_number=phone or f"+2637700{n:05d}",
                email=email,
                hashed_password=await hash_password(password) if password else None,
                user_type=user_type,
                must_change_password=must_change_password,
                is_locked=is_locked,
                locked_until=locked_until,
            )
            s.add(user)
            await s.commit()
            return user

    return _make


@pytest.fixture
def make_worker(session_factory, make_user, make_location):
    async def _make(**user_kwargs):
        user = await make_user(user_type=UserType.EXTENSION_WORKER, **user_kwargs)
        location = await make_location()
        async with session_factory() as s:
            worker = ExtensionWorker(
                user_id=user.id,
                hashed_ussd_pincode="x",
                assigned_ward_name="Ward 1",
                location_id=location.location_id,
            )
            s.add(worker)
            await s.commit()
            return user, worker

    return _make


@pytest.fixture
def make_farmer(session_factory, make_user, make_location):
    async def _make(**user_kwargs):
        user = await make_user(user_type=UserType.FARMER, **user_kwargs)
        location = await make_location()
        async with session_factory() as s:
            farmer = Farmer(
                user_id=user.id,
                ward_name="Ward 2",
                primary_crop="maize",
                location_id=location.location_id,
            )
            s.add(farmer)
            await s.commit()
            return user, farmer

    return _make


@pytest.fixture
def make_otp(session_factory):
    async def _make(user_id, code_hash="hash", **overrides):
        data = dict(
            user_id=user_id,
            code_hash=code_hash,
            attempts=0,
            expires_at=datetime.now(timezone.utc).replace(microsecond=0)
            + timedelta(minutes=5),
        )
        data.update(overrides)
        async with session_factory() as s:
            obj = PasswordResetOTP(**data)
            s.add(obj)
            await s.commit()
            return obj

    return _make


@pytest.fixture
def auth_headers():
    async def _headers(user):
        token = await create_access_token(
            {"sub": str(user.id), "role": user.user_type.value}
        )
        return {"Authorization": f"Bearer {token}"}

    return _headers


class FakeSMS:
    def __init__(self):
        self.sent = []

    async def send_sms(self, request, *args, **kwargs):
        self.sent.append(request)
        return {"status": "queued"}


@pytest.fixture
def fake_sms():
    return FakeSMS()


@pytest_asyncio.fixture
async def client(session_factory, fake_sms, monkeypatch):
    import dependency
    import main
    from ivhuRedu.services.sms_services import get_sms_service

    async def _get_db():
        async with session_factory() as s:
            yield s

    monkeypatch.setattr(database, "async_session", session_factory)
    monkeypatch.setattr(dependency, "async_session", session_factory)
    monkeypatch.setattr(main, "async_session", session_factory)

    main.app.dependency_overrides[dependency.get_db] = _get_db
    main.app.dependency_overrides[database.get_db] = _get_db
    main.app.dependency_overrides[get_sms_service] = lambda: fake_sms

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as c:
        yield c
    main.app.dependency_overrides.clear()
