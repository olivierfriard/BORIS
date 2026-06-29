import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boris import config as cfg
from boris import plugins


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class TestOfficialPluginsReleases:
    def test_official_plugins_branch_source(self):
        assert plugins.official_plugins_branch_source() == {
            "type": "branch",
            "branch": "main",
            "archive_url": "https://github.com/olivierfriard/BORIS_plugins/archive/refs/heads/main.zip",
            "text": "main branch",
        }

    def test_normalize_legacy_release_source(self):
        assert plugins.normalize_official_plugins_source(
            {
                "tag_name": "v1.2.0",
                "archive_url": "https://api.github.com/repos/olivierfriard/BORIS_plugins/zipball/v1.2.0",
            }
        ) == {
            "type": "release",
            "tag_name": "v1.2.0",
            "archive_url": "https://api.github.com/repos/olivierfriard/BORIS_plugins/zipball/v1.2.0",
            "text": "v1.2.0",
        }

    def test_list_official_plugins_releases(self, monkeypatch):
        releases_payload = [
            {
                "tag_name": "v1.2.0",
                "name": "BORIS plugins 1.2.0",
                "zipball_url": "https://api.github.com/repos/olivierfriard/BORIS_plugins/zipball/v1.2.0",
                "published_at": "2026-06-01T12:00:00Z",
                "draft": False,
                "prerelease": False,
            },
            {
                "tag_name": "v1.3.0-beta",
                "name": "v1.3.0-beta",
                "zipball_url": "https://api.github.com/repos/olivierfriard/BORIS_plugins/zipball/v1.3.0-beta",
                "published_at": "2026-06-02T12:00:00Z",
                "draft": False,
                "prerelease": True,
            },
            {
                "tag_name": "draft",
                "name": "draft",
                "zipball_url": "https://api.github.com/repos/olivierfriard/BORIS_plugins/zipball/draft",
                "draft": True,
            },
        ]

        def fake_urlopen(request, timeout):
            assert request.full_url.endswith("/releases?per_page=100")
            assert timeout == 30
            return FakeResponse(json.dumps(releases_payload).encode())

        monkeypatch.setattr(plugins.urllib.request, "urlopen", fake_urlopen)

        releases = plugins.list_official_plugins_releases()

        assert releases == [
            {
                "type": "release",
                "tag_name": "v1.2.0",
                "archive_url": "https://api.github.com/repos/olivierfriard/BORIS_plugins/zipball/v1.2.0",
                "text": "BORIS plugins 1.2.0 (v1.2.0) - 2026-06-01",
            },
            {
                "type": "release",
                "tag_name": "v1.3.0-beta",
                "archive_url": "https://api.github.com/repos/olivierfriard/BORIS_plugins/zipball/v1.3.0-beta",
                "text": "v1.3.0-beta - 2026-06-02 [pre-release]",
            },
        ]


class TestOfficialPluginDirectories:
    def test_official_plugins_dir_does_not_fallback_to_bundled_plugins(self, monkeypatch, tmp_path):
        monkeypatch.setattr(plugins, "_official_plugins_root_candidates", lambda config_param=None: [tmp_path / "missing"])

        assert plugins.get_official_plugins_dir({}) is None
        assert plugins.get_official_plugin_files({}) == []

    def test_official_plugins_dir_does_not_autodiscover_default_repository(self, monkeypatch, tmp_path):
        plugins_dir = tmp_path / "BORIS_plugins" / "plugins"
        plugins_dir.mkdir(parents=True)
        plugin_file = plugins_dir / "example.py"
        plugin_file.write_text(
            '__plugin_name__ = "Example official plugin"\n'
            '__version__ = "1.0"\n'
            "def run():\n"
            "    return None\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(plugins.Path, "home", lambda: tmp_path)

        assert plugins.get_official_plugins_dir({}) is None
        assert plugins.get_official_plugin_files({}) == []

    def test_empty_configured_official_plugins_directory_has_no_plugins_yet(self, tmp_path):
        empty_dir = tmp_path / "empty_plugins_target"
        empty_dir.mkdir()
        config_param = {cfg.OFFICIAL_PLUGINS_DIR: str(empty_dir)}

        assert plugins.get_official_plugins_dir(config_param) is None
        assert plugins.get_official_plugin_files(config_param) == []

    def test_official_plugins_dir_uses_external_repository_plugins_directory(self, tmp_path):
        plugins_dir = tmp_path / "BORIS_plugins" / "plugins"
        plugins_dir.mkdir(parents=True)
        plugin_file = plugins_dir / "example.py"
        plugin_file.write_text(
            '__plugin_name__ = "Example official plugin"\n'
            '__version__ = "1.0"\n'
            "def run():\n"
            "    return None\n",
            encoding="utf-8",
        )

        config_param = {cfg.OFFICIAL_PLUGINS_DIR: str(tmp_path / "BORIS_plugins")}

        assert plugins.get_official_plugins_dir(config_param) == plugins_dir
        assert plugins.get_official_plugin_files(config_param) == [plugin_file]


class TestPluginBorisVersionRequirement:
    def test_requirement_accepts_current_or_newer_version(self):
        assert plugins.boris_version_satisfies_requirement("9.12.0", ">=9.12")
        assert plugins.boris_version_satisfies_requirement("9.12.1", ">=9.12")

    def test_requirement_rejects_older_version(self):
        assert not plugins.boris_version_satisfies_requirement("9.11.9", ">=9.12")

    def test_requirement_without_operator_defaults_to_minimum_version(self):
        assert plugins.boris_version_satisfies_requirement("9.12.0", "9.12")
        assert not plugins.boris_version_satisfies_requirement("9.11.9", "9.12")

    def test_requirement_supports_exact_and_upper_bound_comparisons(self):
        assert plugins.boris_version_satisfies_requirement("9.12.0", "==9.12")
        assert plugins.boris_version_satisfies_requirement("9.11.9", "<9.12")
        assert not plugins.boris_version_satisfies_requirement("9.12.0", "<9.12")

    def test_requirement_supports_v_prefixed_versions(self):
        assert plugins.boris_version_satisfies_requirement("v9.12.0", ">=v9.12")

    def test_requirement_rejects_malformed_required_version(self):
        assert not plugins.boris_version_satisfies_requirement("9.12.0", ">=current")
