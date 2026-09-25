from datetime import datetime
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database.models import Couple, User, utc_now


class CoupleRepository:
    @staticmethod
    def get_by_id(session: Session, couple_id: int) -> Optional[Couple]:
        return session.query(Couple).filter(Couple.id == couple_id).first()

    @staticmethod
    def get_by_user_id(session: Session, user_id: int) -> Optional[Couple]:
        return (
            session.query(Couple)
            .filter(or_(Couple.user_1_id == user_id, Couple.user_2_id == user_id))
            .first()
        )

    @staticmethod
    def create_invite(
        session: Session, user_1_id: int, invite_code: str, expires_at: datetime
    ) -> Couple:
        couple = (
            session.query(Couple)
            .filter(Couple.user_1_id == user_1_id, Couple.user_2_id.is_(None))
            .first()
        )
        if couple:
            couple.invite_code = invite_code
            couple.invite_expires_at = expires_at
        else:
            couple = Couple(
                user_1_id=user_1_id,
                invite_code=invite_code,
                invite_expires_at=expires_at,
            )
            session.add(couple)
        session.flush()
        return couple

    @staticmethod
    def get_by_valid_invite_code(
        session: Session, invite_code: str, current_time: Optional[datetime] = None
    ) -> Optional[Couple]:
        if current_time is None:
            current_time = utc_now()

        return (
            session.query(Couple)
            .filter(
                Couple.invite_code == invite_code.upper().strip(),
                Couple.user_2_id.is_(None),
                Couple.invite_expires_at > current_time,
            )
            .first()
        )

    @staticmethod
    def join_couple(session: Session, couple_id: int, user_2_id: int) -> Optional[Couple]:
        couple = CoupleRepository.get_by_id(session, couple_id)
        if not couple or couple.user_2_id is not None:
            return None

        couple.user_2_id = user_2_id
        couple.invite_code = None
        couple.invite_expires_at = None
        session.flush()
        return couple

    @staticmethod
    def get_partner(session: Session, user_id: int) -> Optional[User]:
        couple = CoupleRepository.get_by_user_id(session, user_id)
        if not couple:
            return None

        if couple.user_1_id == user_id:
            return couple.user_2
        return couple.user_1
