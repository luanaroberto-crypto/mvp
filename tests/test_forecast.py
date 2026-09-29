from datetime import date, datetime, timedelta, timezone

import pytest

from weather_dashboard.forecast import summarize_daily
from weather_dashboard.models import ForecastEntry

TZ = timezone(timedelta(hours=-3))


def entry(
    day: int,
    hour: int,
    temp: float,
    humidity: int = 50,
    description: str = "céu limpo",
    icon: str = "01d",
) -> ForecastEntry:
    return ForecastEntry(
        timestamp=datetime(2026, 9, day, hour, tzinfo=TZ),
        temperature=temp,
        humidity=humidity,
        description=description,
        icon=icon,
    )


class TestSummarizeDaily:
    def test_returns_empty_list_for_no_entries(self):
        assert summarize_daily([]) == []

    def test_groups_entries_by_local_day_in_chronological_order(self):
        entries = [entry(30, 9, 18), entry(29, 12, 25), entry(30, 15, 22)]

        result = summarize_daily(entries)

        assert [d.day for d in result] == [date(2026, 9, 29), date(2026, 9, 30)]

    def test_computes_min_max_and_rounded_average_humidity(self):
        entries = [entry(29, 6, 15.5, 80), entry(29, 12, 27.2, 55), entry(29, 18, 21.0, 60)]

        [day] = summarize_daily(entries)

        assert day.temp_min == 15.5
        assert day.temp_max == 27.2
        assert day.humidity == 65  # (80 + 55 + 60) / 3 = 65

    def test_uses_most_frequent_condition(self):
        entries = [
            entry(29, 0, 18, description="chuva leve", icon="10n"),
            entry(29, 3, 17, description="chuva leve", icon="10n"),
            entry(29, 12, 25, description="céu limpo", icon="01d"),
        ]

        [day] = summarize_daily(entries)

        assert (day.description, day.icon) == ("chuva leve", "10n")

    def test_breaks_ties_with_entry_closest_to_noon(self):
        entries = [
            entry(29, 0, 18, description="chuva leve", icon="10n"),
            entry(29, 12, 25, description="céu limpo", icon="01d"),
        ]

        [day] = summarize_daily(entries)

        assert (day.description, day.icon) == ("céu limpo", "01d")

    def test_limits_number_of_days(self):
        entries = [entry(d, 12, 20) for d in range(20, 28)]

        result = summarize_daily(entries, max_days=3)

        assert [d.day.day for d in result] == [20, 21, 22]

    @pytest.mark.parametrize("max_days", [0, -1])
    def test_rejects_non_positive_max_days(self, max_days):
        with pytest.raises(ValueError, match="max_days"):
            summarize_daily([entry(29, 12, 20)], max_days=max_days)
