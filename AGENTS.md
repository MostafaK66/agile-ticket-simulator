# Engineering contract

- Support Python 3.11 and 3.12 with a `src/` package layout.
- Keep configuration immutable and validate all external inputs.
- Simulations with the same configuration must produce identical results.
- Inject randomness, clocks, model fitting, and filesystem boundaries where practical.
- Preserve chronological splits; never train on validation observations.
- Tests must be deterministic, offline, and independent of external services.
- Run Ruff, strict mypy, branch-aware coverage, and compile checks before merging.
- Never commit generated data, model files, caches, logs, or credentials.
