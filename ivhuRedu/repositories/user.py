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