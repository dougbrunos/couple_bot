from typing import Optional
from sqlalchemy.orm import Session
from app.database.models import User, utc_now


class UserRepository:
    @staticmethod
    def get_by_id(session: Session, user_id: int) -> Optional[User]:
        return session.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_telegram_id(session: Session, telegram_id: int) -> Optional[User]:
        return session.query(User).filter(User.telegram_id == telegram_id).first()

    @staticmethod
    def create_or_update(session: Session, telegram_id: int, name: str) -> User:
        user = UserRepository.get_by_telegram_id(session, telegram_id)
        if user:
            if user.name != name:
                user.name = name
                user.updated_at = utc_now()
                session.flush()
            return user

        user = User(telegram_id=telegram_id, name=name)
        session.add(user)
        session.flush()
        return user
