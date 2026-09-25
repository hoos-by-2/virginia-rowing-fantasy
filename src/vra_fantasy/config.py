"""Season configuration loaded from config.yaml.

Holds only values that are constant across a season (league IDs, game ID, paths).
Per-run values like the week number are CLI input, not config.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, field_validator


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    game_id: int
    league_ids: list[str]
    output_dir: Path
    team_names_path: Path = Path("team_names.csv")

    @field_validator("output_dir", "team_names_path")
    @classmethod
    def _expand_user(cls, path: Path) -> Path:
        return path.expanduser()

    @field_validator("league_ids")
    @classmethod
    def _require_leagues(cls, league_ids: list[str]) -> list[str]:
        if not league_ids:
            raise ValueError("league_ids must contain at least one league ID")
        return league_ids


def load_config(path: str | Path = "config.yaml") -> Config:
    """Load and validate the season config from a YAML file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open() as file:
        data = yaml.safe_load(file) or {}
    config = Config.model_validate(data)
    if not config.team_names_path.is_file():
        raise FileNotFoundError(
            f"Team names file not found: {config.team_names_path} "
            "(set team_names_path in the config; see team_names.example.csv)"
        )
    return config
