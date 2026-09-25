import re
from datetime import datetime, date, time, timezone
from typing import Optional, Tuple
import pytz
from app.config import config


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def to_local_tz(dt: datetime, tz_name: Optional[str] = None) -> datetime:
    tz = pytz.timezone(tz_name or config.TIMEZONE)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(tz)


def get_local_now(tz_name: Optional[str] = None) -> datetime:
    tz = pytz.timezone(tz_name or config.TIMEZONE)
    return datetime.now(tz)


def parse_date_input(
    text: str, tz_name: Optional[str] = None
) -> Tuple[Optional[date], Optional[str]]:
    text = text.strip()
    match_full = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", text)
    match_short = re.match(r"^(\d{1,2})[/.-](\d{1,2})$", text)

    local_now = get_local_now(tz_name)
    today = local_now.date()

    if match_full:
        day, month, year = (
            int(match_full.group(1)),
            int(match_full.group(2)),
            int(match_full.group(3)),
        )
    elif match_short:
        day, month = int(match_short.group(1)), int(match_short.group(2))
        year = today.year
        try:
            candidate = date(year, month, day)
            if candidate < today:
                year += 1
        except ValueError:
            pass
    else:
        return None, "Formato inválido. Por favor, envie a data no formato DD/MM/AAAA (ex: 26/09/2026)."

    try:
        parsed_date = date(year, month, day)
    except ValueError:
        return None, "Data inválida no calendário. Por favor, verifique o dia e o mês."

    if parsed_date < today:
        return None, "A data informada já passou. Por favor, envie uma data de hoje em diante."

    return parsed_date, None


def parse_time_input(text: str) -> Tuple[Optional[time], Optional[str]]:
    text = text.strip().replace("h", ":").replace("H", ":")
    match = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if not match:
        if text.isdigit() and 0 <= int(text) <= 23:
            return time(int(text), 0), None
        return None, "Formato inválido. Por favor, envie o horário no formato HH:MM (ex: 20:00)."

    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None, "Horário inválido. As horas devem ser de 00 a 23 e os minutos de 00 a 59."

    return time(hour, minute), None


def combine_to_utc(d: date, t: time, tz_name: Optional[str] = None) -> datetime:
    tz = pytz.timezone(tz_name or config.TIMEZONE)
    local_dt = tz.localize(datetime.combine(d, t))
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)
