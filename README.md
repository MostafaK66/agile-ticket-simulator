# Agile Ticket Simulator

A deterministic Python toolkit for generating synthetic Agile ticket lifecycles,
aggregating daily delivery/flow metrics, and evaluating lightweight rolling forecasts.
It is the production-oriented successor to the original `generate_fake_data` scripts.

No private data, network connection, external service, GPU, or model download is
required.

## Improvements

- Python 3.11+ package with a Hatchling `src/` layout and thin CLI.
- Immutable, validated TOML configuration for dates, projects, teams, capacity, and
  output locations.
- Local seeded randomness: identical configurations generate identical data without
  mutating Python or NumPy global random state.
- Exactly the configured number of tickets always receives an initial `Refined` event;
  progress probability controls later transitions.
- Story points respect each project's per-increment capacity. Tickets that cannot fit
  receive zero points instead of silently exceeding capacity.
- Daily Created, Done, and active-flow metrics use the appropriate event dates and
  explicitly fill missing calendar days with zero.
- The former predictor branch's intent is retained as a chronological walk-forward
  ridge forecast without XGBoost, unsafe `joblib` deserialization, or data leakage.
- Domain-specific exceptions, dependency-injected boundaries, offline tests, strict
  mypy, Ruff, branch-aware coverage, and GitHub Actions CI.

## Installation

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

For development, install `.[dev]`.

## Usage

Copy and edit the example:

```bash
cp config.example.toml config.toml
agile-simulate --config config.toml
# Equivalent:
python -m agile_ticket_simulator --config config.toml
```

On Windows, use `Copy-Item config.example.toml config.toml`.

The configured output directory receives:

- `ticket_events.csv`: one row per ticket status transition.
- `program_increments.csv`: all observed increments in chronological order.
- `daily_metrics.csv`: complete daily metrics by project.
- `forecasts.csv`: validation predictions when forecasting is enabled.
- `run.json`: counts, seed, and forecast MAE values.

Generated files and local `config.toml` are ignored by Git.

## Data model and forecasting

Every ticket receives stable project, team, feature, type, priority, creation date,
and team-size attributes. Status events progress through Refined, To Do, In Progress,
In Review, and Done. Program increments are calculated from the configured start date.

Forecasting builds copied lag windows for each project and daily metric. It reserves
the newest observations for validation and refits a ridge regression using only data
available before each prediction. Predictions are non-negative integer counts.

## Development

```bash
make install
make quality
```

The quality target runs Ruff, strict mypy, deterministic pytest with branch coverage,
and bytecode compilation on the complete package.

## Attribution and license

Copyright © 2026 MostafaK66. Released under the [MIT License](LICENSE). See
[NOTICE](NOTICE) for the project history and branch attribution.
