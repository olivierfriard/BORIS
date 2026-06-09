import io
import json

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
