"""Tests for event editing dialogs."""

from decimal import Decimal

import pytest
from PySide6.QtWidgets import QDialog

from boris import config as cfg
from boris import edit_event


@pytest.fixture
def warnings(monkeypatch):
    messages = []
    monkeypatch.setattr(edit_event.QMessageBox, "warning", lambda *args: messages.append(args))
    return messages


def close(widget, qapp):
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


@pytest.mark.parametrize(
    "observation_type, time_format, expected_seconds, expected_time",
    [(cfg.LIVE, cfg.S, True, False), (cfg.MEDIA, cfg.HHMMSS, False, True)],
)
def test_event_dialog_initializes_media_and_live_controls(qapp, observation_type, time_format, expected_seconds, expected_time):
    widget = edit_event.DlgEditEvent(
        observation_type,
        time_value=Decimal("12.500"),
        current_time=42.25,
        time_format=time_format,
        show_set_current_time=True,
    )
    try:
        assert widget.time_widget.rb_seconds.isChecked() is expected_seconds
        assert widget.time_widget.rb_time.isChecked() is expected_time
        assert not widget.gb_image_index.isVisible()
        assert not widget.cb_set_time_na.isVisible()
        assert not widget.lb_frame_idx.isVisible()
        assert not widget.sb_frame_idx.isVisible()
        assert not widget.cb_set_frame_idx_na.isVisible()
        assert not widget.pb_set_to_current_time.isHidden()

        widget.set_to_current_time()
        assert widget.time_widget.get_time() == Decimal("42.250")

        widget.set_to_current_image_index()
        assert widget.sb_image_idx.value() == 0
        widget.close_widget()
        assert widget.result() == QDialog.DialogCode.Accepted
    finally:
        close(widget, qapp)


def test_image_event_dialog_uses_indices_dates_and_na_state(qapp, warnings):
    exif_time = Decimal(cfg.DATE_CUTOFF + 20)
    widget = edit_event.DlgEditEvent(
        cfg.IMAGES,
        time_value=Decimal("NaN"),
        image_idx=3,
        current_time=7,
        show_set_current_time=False,
        exif_date_time=exif_time,
    )
    try:
        assert widget.sb_image_idx.value() == 3
        assert not widget.pb_set_to_current_time.isHidden()
        assert widget.time_widget.rb_seconds.isChecked()

        widget.set_to_current_image_index()
        assert widget.sb_image_idx.value() == 7
        widget.set_to_current_time()
        assert widget.time_widget.rb_datetime.isChecked()
        assert widget.time_widget.get_time() == exif_time.quantize(Decimal(".001"))

        widget.cb_set_time_na.setChecked(True)
        assert widget.time_widget.isHidden()
        assert not widget.time_widget.isEnabled()
        assert widget.pb_set_to_current_time.isHidden()

        widget.cb_set_time_na.setChecked(False)
        assert not widget.time_widget.isHidden()
        assert widget.time_widget.isEnabled()
        assert not widget.pb_set_to_current_time.isHidden()

        widget.sb_image_idx.setValue(0)
        widget.close_widget()
        assert "image index cannot be null" in warnings[-1][2]
        assert widget.result() == QDialog.DialogCode.Rejected

        widget.sb_image_idx.setValue(1)
        widget.close_widget()
        assert widget.result() == QDialog.DialogCode.Accepted
    finally:
        close(widget, qapp)


def test_image_event_dialog_without_exif_keeps_current_time_button_hidden(qapp):
    widget = edit_event.DlgEditEvent(cfg.IMAGES, image_idx=1, exif_date_time=None)
    try:
        assert widget.pb_set_to_current_time.isHidden()
        widget.set_to_current_time()
        assert widget.time_widget.le_seconds.text() == ""
    finally:
        close(widget, qapp)


def test_event_dialog_selects_datetime_format_for_absolute_times(qapp):
    widget = edit_event.DlgEditEvent(cfg.MEDIA, time_value=Decimal(cfg.DATE_CUTOFF + 1))
    try:
        assert widget.time_widget.rb_datetime.isChecked()
    finally:
        close(widget, qapp)


@pytest.fixture
def selected_events_dialog(qapp):
    widget = edit_event.EditSelectedEvents()
    widget.all_subjects = ["Alice", "Bob"]
    widget.all_behaviors = ["Run", "Sleep"]
    yield widget
    close(widget, qapp)


def test_selected_events_dialog_switches_fields_and_populates_values(selected_events_dialog):
    selected_events_dialog.rbSubject.setChecked(True)
    assert [selected_events_dialog.newText.item(index).text() for index in range(selected_events_dialog.newText.count())] == ["Alice", "Bob"]
    assert selected_events_dialog.newText.isEnabled()
    assert not selected_events_dialog.commentText.isEnabled()

    selected_events_dialog.rbBehavior.setChecked(True)
    assert [selected_events_dialog.newText.item(index).text() for index in range(selected_events_dialog.newText.count())] == ["Run", "Sleep"]

    selected_events_dialog.rbComment.setChecked(True)
    assert selected_events_dialog.newText.count() == 0
    assert not selected_events_dialog.newText.isEnabled()
    assert selected_events_dialog.commentText.isEnabled()


def test_selected_events_dialog_requires_list_selection_and_accepts_comment(monkeypatch, selected_events_dialog, warnings):
    selected_events_dialog.rbSubject.setChecked(True)
    selected_events_dialog.pbOK_clicked()
    assert "select a new value" in warnings[-1][2]
    assert selected_events_dialog.result() == QDialog.DialogCode.Rejected

    selected_events_dialog.newText.setCurrentRow(0)
    selected_events_dialog.pbOK_clicked()
    assert selected_events_dialog.result() == QDialog.DialogCode.Accepted

    selected_events_dialog.reject()
    selected_events_dialog.rbComment.setChecked(True)
    selected_events_dialog.pbOK_clicked()
    assert selected_events_dialog.result() == QDialog.DialogCode.Accepted


def test_selected_events_dialog_cancel_button_rejects(selected_events_dialog):
    selected_events_dialog.pbCancel_clicked()
    assert selected_events_dialog.result() == QDialog.DialogCode.Rejected
