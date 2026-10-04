"""
module for testing column_visibility.py (show / hide the columns of the ethogram, subjects and events tables)

pytest -s -vv test_column_visibility.py
"""

import os
import sys

import pytest
from PySide6.QtCore import QAbstractTableModel, QSettings, Qt
from PySide6.QtWidgets import QApplication, QTableView, QTableWidget

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from boris import column_visibility

LABELS = ["Key", "Code", "Type", "Description"]


@pytest.fixture()
def table(tmp_path, monkeypatch):
    """Store column preferences in an isolated temporary configuration file.

    Function written by Codex - ChatGPT 6.
    """
    monkeypatch.setattr(column_visibility, "_settings", lambda: QSettings(str(tmp_path / ".boris"), QSettings.Format.IniFormat))
    _app = QApplication.instance() or QApplication([])
    table = QTableWidget(0, len(LABELS))
    table.setHorizontalHeaderLabels(LABELS)
    return table


def test_hide_column_is_saved(table):
    column_visibility.setup(table, column_visibility.ETHOGRAM)
    assert not any(table.isColumnHidden(c) for c in range(len(LABELS)))

    column_visibility.set_column_visible(table, column_visibility.ETHOGRAM, "Type", False)
    assert table.isColumnHidden(2)
    assert column_visibility.hidden_columns(column_visibility.ETHOGRAM) == ["Type"]

    # a new table (e.g. after restarting BORIS) gets the saved hidden columns
    table2 = QTableWidget(0, len(LABELS))
    table2.setHorizontalHeaderLabels(LABELS)
    column_visibility.setup(table2, column_visibility.ETHOGRAM)
    assert [table2.isColumnHidden(c) for c in range(len(LABELS))] == [False, False, True, False]

    # the tables are independent
    assert column_visibility.hidden_columns(column_visibility.SUBJECTS) == []


def test_show_column_and_show_all(table):
    column_visibility.setup(table, column_visibility.EVENTS)
    column_visibility.set_column_visible(table, column_visibility.EVENTS, "Type", False)
    column_visibility.set_column_visible(table, column_visibility.EVENTS, "Code", False)
    column_visibility.set_column_visible(table, column_visibility.EVENTS, "Type", True)
    assert [table.isColumnHidden(c) for c in range(len(LABELS))] == [False, True, False, False]

    column_visibility.show_all_columns(table, column_visibility.EVENTS)
    assert not any(table.isColumnHidden(c) for c in range(len(LABELS)))
    assert column_visibility.hidden_columns(column_visibility.EVENTS) == []


def test_menu_lists_columns_and_keeps_one_visible(table):
    column_visibility.setup(table, column_visibility.SUBJECTS)
    for label in LABELS[1:]:
        column_visibility.set_column_visible(table, column_visibility.SUBJECTS, label, False)

    actions = [a for a in column_visibility.columns_menu(table, column_visibility.SUBJECTS).actions() if a.isCheckable()]
    assert [a.text() for a in actions] == LABELS
    assert [a.isChecked() for a in actions] == [True, False, False, False]
    # the last visible column can not be unchecked
    assert not actions[0].isEnabled()

    # toggling a check box hides / shows the column
    actions[2].setChecked(True)
    assert not table.isColumnHidden(2)


def test_all_hidden_keeps_first_column_visible(table, monkeypatch):
    column_visibility.save_hidden_columns(column_visibility.ETHOGRAM, LABELS)
    column_visibility.apply_hidden_columns(table, column_visibility.ETHOGRAM)
    assert not table.isColumnHidden(0)


class EventsModel(QAbstractTableModel):
    """like core.TableModel: headerData without default role"""

    def rowCount(self, parent=None):
        return 0

    def columnCount(self, parent=None):
        return len(LABELS)

    def data(self, index, role):
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return LABELS[section]


def test_table_view_with_new_model(table):
    view = QTableView()
    view.setModel(EventsModel())
    column_visibility.setup(view, column_visibility.EVENTS)
    column_visibility.set_column_visible(view, column_visibility.EVENTS, "Type", False)
    assert view.isColumnHidden(2)

    # a new model resets the hidden columns: apply them again
    view.setModel(EventsModel())
    column_visibility.apply_hidden_columns(view, column_visibility.EVENTS)
    assert [view.isColumnHidden(c) for c in range(len(LABELS))] == [False, False, True, False]
