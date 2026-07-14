"""
Utilitários de tempo — todas as métricas de duração deste dashboard são
em HORAS (não dias), conforme regra definida no README.
"""

from datetime import datetime, timedelta


def parse_iso(ts: str) -> datetime:
    """Converte timestamp ISO da API do Plane (ex: '2026-06-30T18:24:03.582442Z') em datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def hours_between(start: datetime, end: datetime) -> float:
    """Horas corridas entre dois timestamps (usado em lead time, cycle time, etc.)."""
    if start is None or end is None:
        return None
    return round((end - start).total_seconds() / 3600, 2)


def business_hours_between(start: datetime, end: datetime, hours_per_day: int = 8) -> float:
    """
    Horas úteis entre duas datas — conta apenas dias de semana (seg-sex),
    cada um valendo `hours_per_day` horas. Usado para converter estimativas
    em dias úteis para horas, não para medir tempo real decorrido.
    """
    if start is None or end is None:
        return None
    days = 0
    current = start.date()
    end_date = end.date()
    while current <= end_date:
        if current.weekday() < 5:  # 0=segunda ... 4=sexta
            days += 1
        current += timedelta(days=1)
    return days * hours_per_day


def format_date_br(dt: datetime) -> str:
    """Formata como dd/mm/aaaa."""
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def format_datetime_br(dt: datetime) -> str:
    """Formata como dd/mm/aaaa HH:MM — usado no rodapé do dashboard (hora do sync)."""
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")
