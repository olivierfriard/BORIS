"""Tests for duration input widgets."""

from decimal import Decimal

import pytest

from boris import config as cfg
from boris import duration_widget


@pytest.fixture
def hhmmss_widget(qapp):
    widget = duration_widget.Widget_hhmmss()
    yield widget
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


@pytest.fixture
def duration(qapp):
    widget = duration_widget.Duration_widget()
    yield widget
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def test_hhmmss_widget_emits_duration_and_changes_sign(hhmmss_widget):
    values = []
    hhmmss_widget.time_changed_signal.connect(values.append)

    hhmmss_widget.hours.setValue(1)
    hhmmss_widget.minutes.setValue(2)
    hhmmss_widget.seconds.setValue(3)
    hhmmss_widget.milliseconds.setValue(400)
    hhmmss_widget.update_time_value()
    assert values[-1] == 3723.4

    hhmmss_widget.change_sign()
    assert hhmmss_widget.sign.text() == "-"
    assert values[-1] == -3723.4

    hhmmss_widget.change_sign()
    assert hhmmss_widget.sign.text() == "+"
    assert values[-1] == 3723.4


@pytest.mark.parametrize(
    "value, val_max, expected_value, expected_prefix",
    [
        (60, 59, 0, "0"),
        (-1, 59, 59, ""),
        (5, 59, 5, "0"),
        (10, 59, 10, ""),
        (100, 999, 100, ""),
    ],
)
def test_hhmmss_widget_normalizes_limits_and_prefixes(hhmmss_widget, value, val_max, expected_value, expected_prefix):
    widget = hhmmss_widget.minutes if val_max == 59 else hhmmss_widget.milliseconds

    widget.setValue(value)

    assert widget.value() == expected_value
    assert widget.prefix() == expected_prefix


def test_hhmmss_widget_uses_three_digit_prefix_for_milliseconds(hhmmss_widget):
    hhmmss_widget.value_changed(5, hhmmss_widget.milliseconds, 0, 999)
    assert hhmmss_widget.milliseconds.prefix() == "00"

    hhmmss_widget.value_changed(10, hhmmss_widget.milliseconds, 0, 999)
    assert hhmmss_widget.milliseconds.prefix() == "0"


def test_seconds_widget_emits_its_value(qapp):
    widget = duration_widget.Widget_seconds()
    values = []
    widget.time_changed_signal.connect(values.append)
    try:
        widget.seconds2.setValue(-12.345)
        assert values[-1] == -12.345
        widget.value_changed(4.5)
        assert values[-1] == 4.5
    finally:
        widget.close()
        widget.deleteLater()
        qapp.processEvents()


def test_duration_widget_sets_and_returns_positive_negative_and_nan_values(duration):
    duration.set_time(Decimal("3661.234"))
    assert duration.w1.sign.text() == "+"
    assert duration.w1.hours.value() == 1
    assert duration.w1.minutes.value() == 1
    assert duration.w1.seconds.value() == 1
    assert duration.w1.milliseconds.value() == 234
    assert duration.w2.seconds2.value() == 3661.234
    assert duration.get_time() == Decimal("3661.234")

    duration.set_time(Decimal("-2.5"))
    assert duration.w1.sign.text() == "-"
    assert duration.w1.seconds.value() == 2
    assert duration.w1.milliseconds.value() == 500
    assert duration.get_time() == Decimal("-2.500")

    before = duration.get_time()
    duration.set_time(Decimal("NaN"))
    assert duration.get_time() == before


def test_duration_widget_tracks_edits_and_switches_formats(duration):
    duration.time_changed(Decimal("1.23456"))
    assert duration.get_time() == Decimal("1.235")

    duration.set_format_s()
    assert duration.format_s.isChecked()
    assert duration.Stack.currentIndex() == 1
    assert duration.w2.seconds2.value() == 1.235

    duration.time_changed(7200.5)
    duration.set_format_hhmmss()
    assert duration.format_hhmmss.isChecked()
    assert duration.Stack.currentIndex() == 0
    assert duration.w1.hours.value() == 2
    assert duration.w1.milliseconds.value() == 500

    duration.set_format(cfg.HHMMSS)
    assert duration.Stack.currentIndex() == 0
    duration.set_format(cfg.HHMMSSZZZ)
    assert duration.Stack.currentIndex() == 0
    duration.set_format(cfg.S)
    assert duration.Stack.currentIndex() == 1
