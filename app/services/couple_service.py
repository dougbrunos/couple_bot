import random
import string
from datetime import datetime, timedelta
from typing import Tuple, Optional
from sqlalchemy.orm import Session

from app.database.models import Couple, User
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.utils.date_utils import utc_now, ensure_utc


class CoupleService:
    @staticmethod
    def _generate_code(length: int = 4) -> str:
        chars = string.ascii_uppercase + string.digits
        ambiguous = "0O1I"
        filtered_chars = "".join(c for c in chars if c not in ambiguous)
        suffix = "".join(random.choices(filtered_chars, k=length))
        return f"CASAL-{suffix}"

    @classmethod
    def create_or_get_invite(
        cls, session: Session, telegram_id: int
    ) -> Tuple[Optional[str], Optional[datetime], str]:
        """Gera ou recupera convite ativo."""
        user = UserRepository.get_by_telegram_id(session, telegram_id)
        if not user:
            return None, None, "USER_NOT_FOUND"

        couple = CoupleRepository.get_by_user_id(session, user.id)
        if couple and couple.user_2_id is not None:
            return None, None, "ALREADY_PAIRED"

        now = utc_now()
        if (
            couple
            and couple.invite_code
            and couple.invite_expires_at
            and ensure_utc(couple.invite_expires_at) > now
        ):
            return couple.invite_code, ensure_utc(couple.invite_expires_at), "OK"

        expires_at = now + timedelta(minutes=30)
        invite_code = cls._generate_code()

        for _ in range(5):
            existing = CoupleRepository.get_by_valid_invite_code(session, invite_code, now)
            if not existing:
                break
            invite_code = cls._generate_code()

        CoupleRepository.create_invite(
            session, user_1_id=user.id, invite_code=invite_code, expires_at=expires_at
        )
        return invite_code, expires_at, "OK"

    @classmethod
    def join_couple(
        cls, session: Session, telegram_id: int, invite_code: str
    ) -> Tuple[Optional[Couple], Optional[User], str]:
        """Valida o convite e conecta o segundo usuário ao casal.
        Retorna (couple, partner_user, status).
        Possíveis status: 'OK', 'INVALID_OR_EXPIRED', 'CANNOT_PAIR_SELF', 'ALREADY_PAIRED', 'USER_NOT_FOUND'
        """
        user = UserRepository.get_by_telegram_id(session, telegram_id)
        if not user:
            return None, None, "USER_NOT_FOUND"

        # Se já pertence a um casal com duas pessoas
        existing_couple = CoupleRepository.get_by_user_id(session, user.id)
        if existing_couple and existing_couple.user_2_id is not None:
            return None, None, "ALREADY_PAIRED"

        clean_code = invite_code.strip().upper()
        now = utc_now()
        couple = CoupleRepository.get_by_valid_invite_code(session, clean_code, now)
        if not couple:
            return None, None, "INVALID_OR_EXPIRED"

        if couple.user_1_id == user.id:
            return None, None, "CANNOT_PAIR_SELF"

        # Se o usuário 2 tinha um convite pendente vazio criado anteriormente por ele mesmo, removemos
        if existing_couple and existing_couple.id != couple.id and existing_couple.user_2_id is None:
            session.delete(existing_couple)
            session.flush()

        partner = UserRepository.get_by_id(session, couple.user_1_id)
        joined = CoupleRepository.join_couple(session, couple.id, user.id)
        return joined, partner, "OK"
