from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import (
    Base,
    EventScope,
    RecurrenceType,
    ReminderStatus,
    utc_now,
)
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.database.repositories.event_repo import EventRepository
from app.database.repositories.reminder_repo import ReminderRepository


@pytest.fixture
def session():
    """Cria uma sessão isolada com SQLite em memória para os testes."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    try:
        yield db_session
    finally:
        db_session.close()


def test_user_repository(session):
    user = UserRepository.create_or_update(session, telegram_id=123456, name="Douglas")
    assert user.id is not None
    assert user.name == "Douglas"

    # Atualização de nome existente
    user_updated = UserRepository.create_or_update(session, telegram_id=123456, name="Douglas Silva")
    assert user_updated.id == user.id
    assert user_updated.name == "Douglas Silva"


def test_couple_repository(session):
    u1 = UserRepository.create_or_update(session, telegram_id=111, name="Douglas")
    u2 = UserRepository.create_or_update(session, telegram_id=222, name="Namorada")

    # Criar convite
    expires = utc_now() + timedelta(minutes=30)
    couple = CoupleRepository.create_invite(session, user_1_id=u1.id, invite_code="CASAL-TEST", expires_at=expires)
    assert couple.id is not None
    assert couple.invite_code == "CASAL-TEST"

    # Buscar convite válido
    found = CoupleRepository.get_by_valid_invite_code(session, "CASAL-TEST")
    assert found is not None
    assert found.id == couple.id

    # Conectar parceiro
    joined = CoupleRepository.join_couple(session, couple.id, user_2_id=u2.id)
    assert joined is not None
    assert joined.user_2_id == u2.id
    assert joined.invite_code is None

    # Obter parceiro
    partner = CoupleRepository.get_partner(session, u1.id)
    assert partner is not None
    assert partner.name == "Namorada"


def test_event_and_reminder_repositories(session):
    u1 = UserRepository.create_or_update(session, telegram_id=111, name="Douglas")
    u2 = UserRepository.create_or_update(session, telegram_id=222, name="Namorada")
    couple = CoupleRepository.create_invite(session, user_1_id=u1.id, invite_code="CASAL-TEST", expires_at=utc_now() + timedelta(minutes=30))
    CoupleRepository.join_couple(session, couple.id, user_2_id=u2.id)

    # Criar evento
    event_start = utc_now() + timedelta(hours=2)
    event = EventRepository.create(
        session,
        couple_id=couple.id,
        created_by=u1.id,
        title="Jantar",
        start_at=event_start,
        scope=EventScope.SHARED,
    )
    assert event.id is not None
    assert event.title == "Jantar"

    # Criar lembrete 1 hora antes
    reminder_time = event_start - timedelta(hours=1)
    reminder = ReminderRepository.create(
        session,
        event_id=event.id,
        scheduled_at=reminder_time,
        minutes_before=60,
    )
    assert reminder.id is not None
    assert reminder.status == ReminderStatus.PENDING

    # Testar list_pending
    pending = ReminderRepository.list_pending(session, current_time=event_start)
    assert len(pending) == 1
    assert pending[0].id == reminder.id

    # Marcar como enviado
    ReminderRepository.mark_as_sent(session, reminder.id)
    pending_after = ReminderRepository.list_pending(session, current_time=event_start)
    assert len(pending_after) == 0

    # Deletar evento (deve cancelar/remover lembretes cascateados)
    deleted = EventRepository.delete(session, event.id)
    assert deleted is True
    assert EventRepository.get_by_id(session, event.id) is None
