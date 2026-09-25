from pathlib import Path

import pytest
from pydantic import ValidationError

from vra_fantasy.config import Config, load_config


@pytest.fixture
def team_names_file(tmp_path: Path) -> Path:
    path = tmp_path / "team_names.csv"
    path.write_text("Team Name,Name,Display Team Name\nSome Team,Jane Doe,\n")
    return path


@pytest.fixture
def config_file(tmp_path: Path, team_names_file: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        f"""
game_id: "461"
output_dir: "{tmp_path / "output"}"
team_names_path: "{team_names_file}"
league_ids:
  - "920510"
  - "515852"
"""
    )
    return path


def test_load_valid_config(config_file: Path, team_names_file: Path, tmp_path: Path):
    config = load_config(config_file)
    assert config.game_id == 461
    assert config.league_ids == ["920510", "515852"]
    assert config.output_dir == tmp_path / "output"
    assert config.team_names_path == team_names_file


def test_missing_config_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(tmp_path / "nope.yaml")


def test_missing_required_key(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text('game_id: "461"\noutput_dir: "out"\n')
    with pytest.raises(ValidationError, match="league_ids"):
        load_config(path)


def test_unknown_key_rejected(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text('game_id: "461"\noutput_dir: "out"\nleague_ids: ["1"]\nweek_number: 5\n')
    with pytest.raises(ValidationError, match="week_number"):
        load_config(path)


def test_empty_league_ids_rejected():
    with pytest.raises(ValidationError, match="at least one league ID"):
        Config(game_id=461, league_ids=[], output_dir=Path("out"))


def test_paths_expand_user():
    config = Config(
        game_id=461,
        league_ids=["1"],
        output_dir=Path("~/fantasy/output"),
        team_names_path=Path("~/fantasy/team_names.csv"),
    )
    assert config.output_dir == Path.home() / "fantasy/output"
    assert config.team_names_path == Path.home() / "fantasy/team_names.csv"


def test_missing_team_names_file(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text(
        f'game_id: "461"\noutput_dir: "out"\nleague_ids: ["1"]\n'
        f'team_names_path: "{tmp_path / "missing.csv"}"\n'
    )
    with pytest.raises(FileNotFoundError, match="Team names file not found"):
        load_config(path)
