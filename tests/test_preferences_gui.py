"""Tests for preferences controls using PySide6."""

import pytest
from PySide6.QtWidgets import QDialog

from boris import config as cfg
from boris import preferences


@pytest.fixture
def window(qapp):
    widget = preferences.Preferences()
    yield widget
    widget.close()
    widget.deleteLater()


def test_ok(window):
    window.pbOK.click()
    assert window.result() == QDialog.DialogCode.Accepted


def test_cancel(window):
    window.pbCancel.click()
    assert window.result() == QDialog.DialogCode.Rejected


def test_reset_colors(window):
    window.te_behav_colors.setPlainText("custom behavior color")
    window.te_category_colors.setPlainText("custom category color")
    window.pb_reset_behav_colors.click()
    window.pb_reset_category_colors.click()
    assert window.te_behav_colors.toPlainText().splitlines() == list(cfg.BEHAVIORS_PLOT_COLORS)
    assert window.te_category_colors.toPlainText().splitlines() == list(cfg.CATEGORY_COLORS_LIST)


@pytest.mark.parametrize("response, expected", [(cfg.CANCEL, False), ("Refresh preferences", True)])
def test_refresh_preferences(window, monkeypatch, response, expected):
    monkeypatch.setattr(preferences.dialog, "MessageDialog", lambda *args: response)
    window.pb_refresh.click()
    assert window.flag_refresh is expected
    assert window.result() == (QDialog.DialogCode.Accepted if expected else QDialog.DialogCode.Rejected)
