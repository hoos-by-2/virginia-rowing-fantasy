# virginia-rowing-fantasy

Aggregates weekly Yahoo fantasy football standings across the Virginia Rowing alumni
leagues into a single table, shared with participants as CSV. Pulls standings and
matchup results for every league via the
[yfpy](https://github.com/uberfastman/yfpy) Yahoo Fantasy Sports API wrapper, combines
them into one overall standings DataFrame (ranked by points scored), and reports the
week's awards across all leagues: the closest matchup, the biggest blowout, the top
and lowest scores, the luckiest winner and unluckiest loser, performance against
Yahoo projections (over/underachiever and upset of the week), the best and worst
Yahoo matchup grades, and each league's showing against the all-league median. The
awards file also carries the week's transaction ledger: roster-move counts, the most
active manager, and trade recaps (plus the biggest FAAB bid, in leagues that use FAAB).

Each run writes three files:

| File | Contents |
|------|----------|
| `standings_week_N.csv` | Abridged standings for the weekly email |
| `complete_standings_week_N.csv` | All columns (draft grades, streaks, moves, playoff picture, ...) for further analysis |
| `weekly_awards_week_N.txt` | Weekly award recaps (extremes, luck, projections, grades) and the transaction ledger |

## Setup

Requires Python 3.12+ and [pipenv](https://pipenv.pypa.io/).

```shell
pipenv install --dev
```

### Yahoo API credentials

1. Create a Yahoo Developer app with Fantasy Sports (read) permission — follow the
   [yfpy setup guide](https://github.com/uberfastman/yfpy#setup).
2. Copy the template and fill in your app's credentials:
   ```shell
   cp .env.template .env
   ```
   Set `YAHOO_CONSUMER_KEY` and `YAHOO_CONSUMER_SECRET` (the app's client ID and
   secret) and leave `YAHOO_TOKEN_TYPE=bearer` as-is. The token fields
   (`YAHOO_ACCESS_TOKEN`, `YAHOO_REFRESH_TOKEN`, `YAHOO_TOKEN_TIME`) stay empty —
   yfpy fills them in after the first authorization.
3. The first run opens a browser window to authorize the app; paste the verification
   code into the prompt. After that, yfpy stores the access token fields in `.env` and
   refreshes them automatically — no re-authorization needed.

`.env` is gitignored (only `.env.template` is committed). Never commit `.env`.

### Team names file

`team_names.csv` maps Yahoo team names to the managers' real names for the output
table. It contains real people's names, so it is gitignored and must **never** be
committed; copy the committed template to see the format:

```csv
Team Name,Name,Display Team Name
Example Yahoo Team,Jane Doe,
inappropriate_team_name,Alex Example,The Renamed Team
```

- `Team Name` — the team's name exactly as it appears in Yahoo (lookup key).
- `Name` — the manager's real name, shown in the output.
- `Display Team Name` — optional override shown instead of the Yahoo name; leave
  blank to use the Yahoo name. Emoji and special characters are stripped from
  un-overridden names automatically.

Teams missing from the file fall back to their Yahoo manager nickname, with a warning.

## Usage

```shell
pipenv run fantasy-standings --week 15
```

Omit `--week` to be prompted for it. Other flags: `--output-dir` overrides the config
output directory, `--config` points at an alternate config file, and `--no-awards` 
skips the weekly awards and transaction ledger.

Equivalent make target:

```shell
make standings WEEK=15
```

### Configuration (`config.yaml`)

Season-long settings; only the week number changes run to run (and is therefore CLI
input, not config).

| Key | Meaning |
|-----|---------|
| `game_id` | Yahoo's ID for the NFL season (changes every year — see below) |
| `output_dir` | Where the weekly files are written (`~` ok; created if missing) |
| `team_names_path` | Path to the team names CSV |
| `league_ids` | The Yahoo league IDs to aggregate |

### New season checklist

1. Look up the new season's game ID (uses any league from the old config to
   authenticate):
   ```shell
   pipenv run fantasy-game-id
   ```
2. Update `game_id` and the new `league_ids` in `config.yaml`.
3. Add the season's team names to `team_names.csv`.

## Development

`pyproject.toml` is the single source of truth for runtime dependencies; the Pipfile
installs the project editable so pipenv resolves them from there. After changing
dependencies in `pyproject.toml`, run `make lock`.

| Command | Does |
|---------|------|
| `make test` | Run the pytest suite |
| `make lint` / `make format` | ruff check / ruff format |
| `make lock` | Re-resolve dependencies from pyproject.toml and sync the venv |

Project layout: `src/vra_fantasy/` — `yahoo.py` is the only module that talks to the
Yahoo API; `names.py`, `standings.py`, and `stats.py` are pure transforms over fetched
data; `schema.py` defines the output columns (derived from the `TeamRecord` model);
`output.py` writes files; `cli.py` ties it together. `notebooks/` has an exploratory
analysis notebook that reuses the same modules.
