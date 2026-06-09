import datetime as dt

from boris import plot_events


class TestPlotEventsTimeAxis:
    def test_can_use_date_axis_for_regular_duration(self):
        assert plot_events._can_use_date_axis(dt.datetime(2017, 1, 1), 0, 3600)

    def test_cannot_use_date_axis_for_very_large_duration(self):
        assert not plot_events._can_use_date_axis(dt.datetime(2017, 1, 1), 0, 1_000_000_000_000)

    def test_plot_time_returns_numeric_value_without_date_axis(self):
        assert plot_events._plot_time(1_000_000_000_000, dt.datetime(2017, 1, 1), False) == 1_000_000_000_000

    def test_hhmmss_axis_formatter_handles_very_large_duration(self):
        assert plot_events._hhmmss_axis_formatter(1_000_000_000_000, 0) == "277777777:46:40"
