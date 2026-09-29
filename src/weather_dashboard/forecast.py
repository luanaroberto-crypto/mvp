"""Agregação da previsão de 3 em 3 horas em resumos diários (lógica pura, sem I/O)."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date

from weather_dashboard.models import DailyForecast, ForecastEntry

# Horário usado como referência para escolher o ícone/descrição "representativo" do dia.
REPRESENTATIVE_HOUR = 12


def summarize_daily(entries: Iterable[ForecastEntry], max_days: int = 5) -> list[DailyForecast]:
    """Agrupa os pontos por dia e calcula mínima, máxima, umidade média e condição dominante.

    A condição do dia é a descrição mais frequente; em caso de empate, vence a do ponto
    mais próximo do meio-dia, que costuma representar melhor o dia do que a madrugada.
    """
    if max_days < 1:
        raise ValueError("max_days deve ser pelo menos 1")

    by_day: dict[date, list[ForecastEntry]] = defaultdict(list)
    for entry in entries:
        by_day[entry.timestamp.date()].append(entry)

    return [_summarize_day(day, by_day[day]) for day in sorted(by_day)[:max_days]]


def _summarize_day(day: date, entries: list[ForecastEntry]) -> DailyForecast:
    counts = Counter(entry.description for entry in entries)
    top_count = max(counts.values())
    candidates = [entry for entry in entries if counts[entry.description] == top_count]
    representative = min(candidates, key=lambda e: abs(e.timestamp.hour - REPRESENTATIVE_HOUR))

    return DailyForecast(
        day=day,
        temp_min=min(entry.temperature for entry in entries),
        temp_max=max(entry.temperature for entry in entries),
        humidity=round(sum(entry.humidity for entry in entries) / len(entries)),
        description=representative.description,
        icon=representative.icon,
    )
