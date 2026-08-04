"""
repositories/user.py
-----------------------
Data-access layer for the User entity: every direct database query lives
here so the service layer (services/user.py) never has to know any
SQLAlchemy query syntax - it just calls plain methods like get() or
create().

Kept stateless on purpose: methods take `db` as a parameter rather than
storing a session on `self`, so the single module-level instance at the
bottom of this file is safe to share and reuse across every request.
"""

import uuid

from sqlalchemy.orm import Session

from ivhuRedu.models.user import User


class UserRepository:
    def get(self, db: Session, id: uuid.UUID):
      
        return db.get(User, id)

    def get_by_email(self, db: Session, email: str):

        return db.query(User).filter(User.email == email).first()

    def get_by_phone_number(self, db: Session, phone_number: str):
        
        return db.query(User).filter(User.phone_number == phone_number).first()

    def get_by_user_type(self, db: Session, user_type):
        return db.query(User).filter(User.user_type == user_type).first()

    def get_all(self, db: Session):
        return db.query(User).all()

    def create(self, db: Session, data: dict):
        user = User(**data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update(self, db: Session, db_obj: User, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: User):
        db.delete(db_obj)
        db.commit()


user_repository = UserRepository()