import re
import tomllib

import pytest

from weather_dashboard import __version__
from weather_dashboard.config import FALLBACK_VERSION, PROJECT_ROOT, VERSION_FILE, read_version

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class TestReadVersion:
    def test_reads_and_strips_version_file(self, tmp_path):
        version_file = tmp_path / "VERSION"
        version_file.write_text("  2.3.4\n", encoding="utf-8")

        assert read_version(version_file) == "2.3.4"

    def test_falls_back_to_dev_when_file_is_missing(self, tmp_path):
        assert read_version(tmp_path / "VERSION") == FALLBACK_VERSION == "dev"

    @pytest.mark.parametrize("content", ["", "   \n"])
    def test_falls_back_to_dev_when_file_is_empty(self, tmp_path, content):
        version_file = tmp_path / "VERSION"
        version_file.write_text(content, encoding="utf-8")

        assert read_version(version_file) == "dev"


class TestProjectVersion:
    def test_version_file_is_bare_semver(self):
        # Sem prefixo "v": ele é adicionado apenas na exibição, pelo frontend.
        assert SEMVER.match(VERSION_FILE.read_text(encoding="utf-8").strip())

    def test_package_exposes_version_file_value(self):
        assert __version__ == VERSION_FILE.read_text(encoding="utf-8").strip()

    def test_pyproject_version_matches_version_file(self):
        pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        assert pyproject["project"]["version"] == __version__
