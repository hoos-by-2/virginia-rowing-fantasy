"""Team and manager name resolution.

Yahoo team names are the lookup keys into team_names.csv, which maps each team
to its manager's real name and, optionally, a display override for team names
that are inappropriate for the shared output or unrenderable. Yahoo names with
no override are sanitized automatically (emoji and other symbol characters
stripped, whitespace collapsed).
"""

import csv
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

TEAM_NAME_COLUMN = "Team Name"
MANAGER_NAME_COLUMN = "Name"
DISPLAY_NAME_COLUMN = "Display Team Name"

# Emoji and other pictographs (So), modifier symbols like skin tones (Sk), and
# control/format characters such as zero-width joiners (Cc, Cf, Co, Cs, Cn).
_STRIPPED_CATEGORIES = {"So", "Sk", "Cc", "Cf", "Co", "Cs", "Cn"}
# Variation selectors are category Mn (which is otherwise kept for combining
# accents), so they need stripping explicitly.
_INVISIBLE_CHARS = re.compile("[\\ufe00-\\ufe0f]")


@dataclass(frozen=True)
class TeamNameEntry:
    manager_name: str
    display_team_name: str | None = None


def load_team_names(path: Path) -> dict[str, TeamNameEntry]:
    """Load the Yahoo-team-name -> names mapping from CSV.

    The "Display Team Name" column is optional, both per row and as a column
    (two-column files predating it load fine).
    """
    entries: dict[str, TeamNameEntry] = {}
    with Path(path).open(newline="") as file:
        reader = csv.DictReader(file)
        missing = {TEAM_NAME_COLUMN, MANAGER_NAME_COLUMN} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Team names file {path} is missing columns: {sorted(missing)}")
        for row in reader:
            team_name = (row[TEAM_NAME_COLUMN] or "").strip()
            if not team_name:
                continue
            display = (row.get(DISPLAY_NAME_COLUMN) or "").strip()
            entries[team_name] = TeamNameEntry(
                manager_name=(row[MANAGER_NAME_COLUMN] or "").strip(),
                display_team_name=display or None,
            )
    return entries


def sanitize_name(raw: str) -> str:
    """Strip emoji/symbol/control characters and collapse whitespace.

    Stripped characters become spaces (collapsed afterwards) so that an emoji
    glued between words separates them instead of fusing them.
    """
    normalized = unicodedata.normalize("NFC", raw)
    kept = "".join(
        " " if unicodedata.category(char) in _STRIPPED_CATEGORIES else char for char in normalized
    )
    kept = _INVISIBLE_CHARS.sub(" ", kept)
    return " ".join(kept.split())


def display_team_name(raw_team_name: str, entries: dict[str, TeamNameEntry]) -> str:
    """The team name to show in output: explicit override, else sanitized Yahoo name."""
    entry = entries.get(raw_team_name)
    if entry and entry.display_team_name:
        return entry.display_team_name
    return sanitize_name(raw_team_name)


def resolve_names(
    raw_team_name: str,
    entries: dict[str, TeamNameEntry],
    yahoo_manager_name: str | None = None,
) -> tuple[str, str]:
    """Resolve a Yahoo team name to (display team name, manager name).

    Falls back to the Yahoo manager nickname (with a warning) for teams missing
    from the team names file; raises if no manager name can be found at all.
    """
    display = display_team_name(raw_team_name, entries)
    entry = entries.get(raw_team_name)
    if entry and entry.manager_name:
        return display, entry.manager_name
    logger.warning("Team name not found in team names file: %r", raw_team_name)
    if yahoo_manager_name:
        return display, yahoo_manager_name
    raise ValueError(f"Manager name not found for team: {raw_team_name!r}")
