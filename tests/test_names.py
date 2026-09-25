from pathlib import Path

import pytest

from vra_fantasy.names import (
    TeamNameEntry,
    display_team_name,
    load_team_names,
    resolve_names,
    sanitize_name,
)


class TestLoadTeamNames:
    def test_three_column_file(self, tmp_path: Path):
        path = tmp_path / "team_names.csv"
        path.write_text(
            "Team Name,Name,Display Team Name\n"
            "Philly Bulldogs,John Heuisler,\n"
            "bad name,Casey Lingan,The Renamed Team\n"
        )
        entries = load_team_names(path)
        assert entries["Philly Bulldogs"] == TeamNameEntry("John Heuisler", None)
        assert entries["bad name"] == TeamNameEntry("Casey Lingan", "The Renamed Team")

    def test_legacy_two_column_file(self, tmp_path: Path):
        path = tmp_path / "team_names.csv"
        path.write_text("Team Name,Name\nPhilly Bulldogs,John Heuisler\n")
        entries = load_team_names(path)
        assert entries["Philly Bulldogs"] == TeamNameEntry("John Heuisler", None)

    def test_missing_required_column(self, tmp_path: Path):
        path = tmp_path / "team_names.csv"
        path.write_text("Team Name,Manager\nX,Y\n")
        with pytest.raises(ValueError, match="missing columns"):
            load_team_names(path)

    def test_blank_rows_skipped(self, tmp_path: Path):
        path = tmp_path / "team_names.csv"
        path.write_text("Team Name,Name\n,\nReal Team,Jane Doe\n")
        assert list(load_team_names(path)) == ["Real Team"]


class TestSanitizeName:
    def test_plain_name_unchanged(self):
        assert sanitize_name("Philly Bulldogs") == "Philly Bulldogs"

    def test_emoji_stripped(self):
        assert sanitize_name("Team Rocket 🚀🔥") == "Team Rocket"
        assert sanitize_name("🏈 Gridiron 🏈 Gang") == "Gridiron Gang"

    def test_variation_selector_and_zwj_stripped(self):
        assert sanitize_name("Zap ⚡️ Squad") == "Zap Squad"
        assert sanitize_name("Family 👨‍👩‍👧 Team") == "Family Team"

    def test_whitespace_collapsed(self):
        assert sanitize_name("  Too   Many\tSpaces ") == "Too Many Spaces"

    def test_accents_and_punctuation_kept(self):
        assert sanitize_name("Café Olé!") == "Café Olé!"
        assert sanitize_name("D'Angelo's Team-Name") == "D'Angelo's Team-Name"


class TestResolveNames:
    ENTRIES = {
        "Known Team": TeamNameEntry("Jane Doe"),
        "Ugly 🚀 Name": TeamNameEntry("John Smith", "Pretty Name"),
    }

    def test_known_team(self):
        assert resolve_names("Known Team", self.ENTRIES) == ("Known Team", "Jane Doe")

    def test_display_override(self):
        assert resolve_names("Ugly 🚀 Name", self.ENTRIES) == ("Pretty Name", "John Smith")

    def test_unknown_team_falls_back_to_yahoo_nickname(self, caplog):
        display, manager = resolve_names("Mystery 🎩 Team", self.ENTRIES, "yahoo_nick")
        assert (display, manager) == ("Mystery Team", "yahoo_nick")
        assert "not found in team names file" in caplog.text

    def test_unknown_team_without_fallback_raises(self):
        with pytest.raises(ValueError, match="Manager name not found"):
            resolve_names("Mystery Team", self.ENTRIES)

    def test_display_team_name_sanitizes_unknown(self):
        assert display_team_name("Some 🐍 Team", {}) == "Some Team"
