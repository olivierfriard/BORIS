import os
from pathlib import Path
import shutil

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("UV_CACHE_DIR", "/tmp/boris-uv-cache")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication


def pytest_configure(config):
    # Matplotlib needs an application before test modules select the Qt backend.
    config.boris_test_application = QApplication.instance() or QApplication([])


@pytest.fixture(scope="session")
def qapp(pytestconfig):
    return pytestconfig.boris_test_application


@pytest.fixture(scope="session")
def input_files(tmp_path_factory):
    destination = tmp_path_factory.mktemp("boris-input") / "files"
    shutil.copytree(Path(__file__).parent / "files", destination)
    return destination


@pytest.fixture(autouse=True)
def test_directory(tmp_path, input_files, monkeypatch, qapp):
    # Legacy tests use relative paths. Keep all their output outside the checkout.
    try:
        (tmp_path / "files").symlink_to(input_files, target_is_directory=True)
    except OSError:
        shutil.copytree(input_files, tmp_path / "files")
    (tmp_path / "output").mkdir()
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


@pytest.fixture(autouse=True)
def close_test_sqlite_connections(monkeypatch):
    """Close SQLite connections created by helpers during a test."""
    from boris import db_functions

    connections = []
    connect = db_functions.sqlite3.connect

    def track_connection(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(db_functions.sqlite3, "connect", track_connection)
    yield
    for connection in connections:
        connection.close()


@pytest.fixture
def before(test_directory):
    return test_directory / "output"
