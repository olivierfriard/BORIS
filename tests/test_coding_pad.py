from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEvent, QRect

from boris import coding_pad, config as cfg


def project():
    return {
        cfg.ETHOGRAM: {
            "0": {cfg.BEHAVIOR_CODE: "A", cfg.TYPE: cfg.STATE_EVENT, cfg.BEHAVIOR_CATEGORY: "Alpha", cfg.COLOR: "#ff0000"},
            "1": {cfg.BEHAVIOR_CODE: "B", cfg.TYPE: cfg.POINT_EVENT, cfg.BEHAVIOR_CATEGORY: "Beta", cfg.COLOR: ""},
            "2": {cfg.BEHAVIOR_CODE: "C", cfg.TYPE: cfg.POINT_EVENT, cfg.BEHAVIOR_CATEGORY: "Alpha", cfg.COLOR: "#00ff00"},
        },
        cfg.BEHAVIORAL_CATEGORIES_CONF: {
            "alpha": {"name": "Alpha", cfg.COLOR: "#112233"},
            "beta": {"name": "Beta", cfg.COLOR: ""},
        },
    }


def buttons(pad):
    return {
        item.widget().pushButton.text(): item.widget().pushButton
        for index in range(pad.grid.count())
        if (item := pad.grid.itemAt(index)).widget() is not None
    }


@pytest.fixture
def pad(qapp):
    window = coding_pad.CodingPad(project(), ["A", "B"])
    window.behavioral_category_colors_list = ["yellow", "cyan"]
    window.behavior_colors_list = ["tab:orange", "purple"]
    window.compose()
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_compose_filters_behaviors_and_configures_state_buttons(pad):
    pad_buttons = buttons(pad)

    assert set(pad_buttons) == {"A", "B"}
    assert pad_buttons["A"].isCheckable()
    assert not pad_buttons["B"].isCheckable()
    assert "background-color: #112233;" in pad_buttons["A"].styleSheet()
    assert "background-color: cyan;" in pad_buttons["B"].styleSheet()
    assert pad_buttons["A"].font().pointSize() == 20


def test_configuration_changes_font_and_button_color_modes(pad):
    pad.cb_config.setCurrentIndex(1)
    assert pad.preferences["button font size"] == 24
    assert buttons(pad)["A"].font().pointSize() == 24

    pad.cb_config.setCurrentIndex(2)
    assert pad.preferences["button font size"] == 20

    pad.cb_config.setCurrentIndex(4)
    assert pad.preferences["button color"] == "behavior"
    assert "background-color: #ff0000;" in buttons(pad)["A"].styleSheet()
    assert "background-color: purple;" in buttons(pad)["B"].styleSheet()

    pad.cb_config.setCurrentIndex(5)
    assert pad.preferences["button color"] == "no color"
    assert "background-color:" not in buttons(pad)["A"].styleSheet()

    pad.cb_config.setCurrentIndex(3)
    assert pad.preferences["button color"] == cfg.BEHAVIOR_CATEGORY


def test_buttons_and_events_emit_expected_signals(pad):
    clicks, events, closed = [], [], []
    pad.click_signal.connect(clicks.append)
    pad.sendEventSignal.connect(events.append)
    pad.close_signal.connect(lambda geometry, preferences: closed.append((geometry, preferences.copy())))

    buttons(pad)["A"].click()
    key_event = QEvent(QEvent.Type.KeyPress)
    assert pad.eventFilter(pad, key_event)
    assert not pad.eventFilter(pad, QEvent(QEvent.Type.Enter))
    pad.close()

    assert clicks == ["A"]
    assert events == [key_event]
    assert closed == [(pad.geometry(), pad.preferences)]


def test_resize_reapplies_button_configuration(pad):
    pad.preferences["button font size"] = 28
    pad.resizeEvent(None)

    assert all(button.font().pointSize() == 28 for button in buttons(pad).values())


def test_compose_replaces_previous_buttons_and_uses_category_palette_without_overrides(qapp):
    coding_pad_project = project()
    del coding_pad_project[cfg.BEHAVIORAL_CATEGORIES_CONF]
    pad = coding_pad.CodingPad(coding_pad_project, ["A", "B"])
    pad.behavioral_category_colors_list = ["yellow", "cyan"]
    pad.behavior_colors_list = ["red", "blue"]
    try:
        pad.compose()
        pad.compose()

        assert set(buttons(pad)) == {"A", "B"}
        assert "background-color: cyan;" in buttons(pad)["B"].styleSheet()
    finally:
        pad.close()
        pad.deleteLater()
        qapp.processEvents()


class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeCodingPad:
    def __init__(self, pj, filtered_behaviors):
        self.pj = pj
        self.filtered_behaviors = filtered_behaviors
        self.behavior_colors_list = []
        self.behavioral_category_colors_list = []
        self.preferences = {"button font size": 20, "button color": cfg.BEHAVIOR_CATEGORY}
        self.sendEventSignal = Signal()
        self.click_signal = Signal()
        self.close_signal = Signal()
        self.calls = []

    def compose(self):
        self.calls.append(("compose",))

    def setWindowFlags(self, flags):
        self.calls.append(("flags", flags))

    def show(self):
        self.calls.append(("show",))

    def setGeometry(self, *geometry):
        self.calls.append(("geometry", geometry))

    def button_configuration(self):
        self.calls.append(("button configuration",))


class EthogramTable:
    def __init__(self, behavior_codes):
        self.behavior_codes = behavior_codes

    def rowCount(self):
        return len(self.behavior_codes)

    def item(self, row, column):
        assert column == 1
        return SimpleNamespace(text=lambda: self.behavior_codes[row])


def owner(behavior_codes, player_type=cfg.MEDIA, config_param=None):
    return SimpleNamespace(
        playerType=player_type,
        pj=project(),
        twEthogram=EthogramTable(behavior_codes),
        config_param=config_param
        or {
            "plot_colors": ["red", "blue"],
            "behav_category_colors": ["yellow", "cyan"],
        },
        signal_from_widget=lambda *_: None,
        click_signal_from_coding_pad=lambda *_: None,
        close_signal_from_coding_pad=lambda *_: None,
    )


def test_show_coding_pad_warns_for_viewer_or_empty_behaviors(monkeypatch):
    warnings = []
    monkeypatch.setattr(coding_pad.QMessageBox, "warning", lambda *args: warnings.append(args))

    coding_pad.show_coding_pad(owner(["A"], player_type=cfg.VIEWER_MEDIA))
    coding_pad.show_coding_pad(owner([]))

    assert "VIEW" in warnings[0][2]
    assert "No behaviors" in warnings[1][2]

    existing = owner([])
    existing.codingpad = FakeCodingPad(project(), ["A"])
    coding_pad.show_coding_pad(existing)
    assert "No behaviors" in warnings[2][2]


def test_show_coding_pad_creates_restores_and_reuses_the_pad(monkeypatch):
    monkeypatch.setattr(coding_pad, "CodingPad", FakeCodingPad)
    geometry = QRect(3, 4, 500, 300)
    configuration = {"button font size": 32, "button color": "behavior"}
    window = owner(
        ["A", "B"],
        config_param={
            "plot_colors": ["black"],
            "behav_category_colors": ["green"],
            cfg.CODING_PAD_GEOMETRY: geometry,
            cfg.CODING_PAD_CONFIG: configuration,
        },
    )

    coding_pad.show_coding_pad(window)
    pad = window.codingpad

    assert pad.filtered_behaviors == ["A", "B"]
    assert pad.behavior_colors_list == ["black"]
    assert pad.behavioral_category_colors_list == ["green"]
    assert pad.preferences == configuration
    assert len(pad.sendEventSignal.callbacks) == 1
    assert len(pad.click_signal.callbacks) == 1
    assert len(pad.close_signal.callbacks) == 1
    assert ("geometry", (3, 4, 500, 300)) in pad.calls
    assert ("button configuration",) in pad.calls

    window.twEthogram = EthogramTable(["B"])
    window.config_param["plot_colors"] = ["purple"]
    coding_pad.show_coding_pad(window)

    assert pad.filtered_behaviors == ["B"]
    assert pad.behavior_colors_list == ["purple"]
    assert pad.calls.count(("show",)) == 2


def test_show_coding_pad_uses_default_geometry_when_none_is_saved(monkeypatch):
    monkeypatch.setattr(coding_pad, "CodingPad", FakeCodingPad)
    window = owner(["A"])

    coding_pad.show_coding_pad(window)

    assert ("geometry", (100, 100, 660, 500)) in window.codingpad.calls
