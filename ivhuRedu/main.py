"""
main.py
---------
Application entry point: builds the FastAPI app, creates every database
table on startup, seeds a first ADMIN user if none exists yet, and wires
up the auth and users routers.
"""



# Importing the `models` package runs models/__init__.py, which imports
# every model class in turn - that's what actually registers each table
# on Base.metadata before create_all() runs below. See the comment at the
# top of models/__init__.py for why this is centralised there rather than
# listed out module-by-module here.
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from sqlalchemy.orm import Session

from ivhuRedu.database import Base, SessionLocal, engine

import ivhuRedu.models as models
from ivhuRedu.models import User, UserType
from ivhuRedu.routers import auth as auth_router
from ivhuRedu.routers import user as user_router
from ivhuRedu.services.security import hash_password

logger = logging.getLogger("uvicorn.error")

# Build every table that doesn't already exist. A real production
# deployment would normally replace this with proper Alembic migrations.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="IvhuRedu API", version="1")

app.include_router(auth_router.router)
app.include_router(user_router.router)


def onboard_default_admin() -> None:
    """
    Seed exactly one ADMIN user the first time the application starts, so
    there is always a way to log in and create further users/admins
    afterwards. Without this, creating an admin normally requires already
    being logged in as an admin - a chicken-and-egg problem for a brand
    new deployment.

    Credentials come from environment variables rather than being
    hardcoded - "Keep Secrets in a Vault, Not a File". In a real
    deployment these would come from a proper secret manager (HashiCorp
    Vault / AWS Secrets Manager / Azure Key Vault), not a .env file
    checked into git.

    Safe to run on every restart: if an admin already exists, it does
    nothing.
    """
    admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
    admin_password = os.getenv("ADMIN_PASSWORD")

    # Without both of these we cannot safely create an admin account, so
    # skip onboarding rather than guessing at default credentials -
    # "Secure Defaults": if a setting is missing, block, don't guess.
    if not admin_phone or not admin_password:
        logger.warning(
            "ADMIN_PHONE_NUMBER / ADMIN_PASSWORD not set - skipping default admin onboarding."
        )
        return

    db: Session = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.user_type == UserType.ADMIN).first()
        if existing_admin:
            return  # An admin already exists - nothing further to do.

        admin = User(
            first_name=os.getenv("ADMIN_FIRST_NAME", "System"),
            last_name=os.getenv("ADMIN_LAST_NAME", "Administrator"),
            email=os.getenv("ADMIN_EMAIL"),
            phone_number=admin_phone,
            # Hash the password before it ever touches the database -
            # same rule as every other user.
            hashed_password=hash_password(admin_password),
            user_type=UserType.ADMIN,
        )
        db.add(admin)
        db.commit()
        logger.info("Default admin user created.")
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    """FastAPI calls this once, automatically, right after the app boots."""
    onboard_default_admin()