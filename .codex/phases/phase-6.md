# Phase 6 — Revert the version bump, then clear the dependency vulnerabilities

Read `.codex/SPEC.md` first. This phase touches dependencies and metadata only.
Do not restructure code, and do not change library behaviour.

---

## Job A — Undo the 0.2.0 version bump

The release is not happening yet; features are still missing. Put the version
back to `0.1.9` in all three places:

- `pyproject.toml` → `version = "0.1.9"`
- `algosystem/__init__.py` → `__version__ = "0.1.9"`
- `CHANGELOG.md` → retitle the `## 0.2.0 - 2026-08-09` section to
  `## Unreleased`. Keep every entry; only the heading changes. Do not add a
  date.

Nothing else about the changelog content changes — the restructure is still
accurately described there, it simply has not shipped.

## Job B — Clear the Dependabot alerts

GitHub reports 28 open alerts (19 high, 9 moderate) against the default branch.
Many are already resolved on this branch because Phase 1 deleted the packages
that pulled them in — `flask`, `weasyprint`, `markdown`, `python-pptx`,
`plotly` and `kaleido` are gone, which takes `weasyprint` with it, including the
one advisory that has **no** patched version available.

What remains falls into three groups.

### B1 — Runtime dependencies that are not used at all

Verified by grepping `algosystem/` for actual imports. Each of these has zero
import sites and should be removed from `[tool.poetry.dependencies]` outright.
Removing a dependency is a better vulnerability fix than upgrading it.

| Package | Import sites | Action |
|---|---|---|
| `ipython` (pinned `8.12.0`) | 0 | remove — a hard pin on a stale version, drags in old transitives |
| `pyyaml` | 0 | remove |
| `pytz` | 0 | remove — pandas pulls it if needed |
| `flake8` | 0 | remove — `ruff` already covers linting, and a linter is not a runtime dependency |
| `pytest` | 0 | **remove from runtime deps** — it is declared in *both* `[tool.poetry.dependencies]` and the dev group. Keep only the dev-group entry. |

Before deleting each one, confirm the zero-import finding yourself, and confirm
nothing in `tests/`, `docs/` or the CI workflows needs it. `seaborn` and
`matplotlib` have no direct import sites either but **must stay** — quantstats
requires them. `openpyxl` likewise stays: pandas needs it for the Excel branch
of `AlgoSystem.export_data`.

### B2 — Direct dependencies that need a floor raised

| Package | Required | Notes |
|---|---|---|
| `requests` | `>=2.33.0` | keep as a direct dep even though nothing imports it — declaring it is how we force the floor on yfinance's transitive copy |
| `pyarrow` | `>=23.0.1` | currently `^19.0.1`; needed by the parquet benchmark cache |
| `python-dotenv` | `>=1.2.2` | |
| `black` (dev) | `>=26.3.1` | |
| `pytest` (dev) | `>=9.0.3` | major version bump from 8.x — see the warning below |

### B3 — Transitive packages with no direct declaration

`pillow`, `urllib3` and `orjson` are pulled in by matplotlib, requests and
plotly respectively. `orjson` may vanish once plotly is gone — check the lock
file before doing anything about it.

For the ones that remain, add explicit floors to `[tool.poetry.dependencies]`
so the resolver cannot pick a vulnerable version: `pillow >=12.3.0` and
`urllib3 >=2.7.0`. Add a short comment above them noting they are declared for
security floors rather than direct use, so nobody deletes them later as
"unused".

`pillow` is the single largest cluster — roughly half the alerts — so verify
the resolved version specifically after re-locking.

## The Python floor is likely the blocker

`pyproject.toml` declares `python = ">=3.9,<4.0"`. Modern `pillow` and `pyarrow`
almost certainly require `>=3.10` or `>=3.11`, so the resolver will refuse to
pick the patched versions while the floor sits at 3.9.

Raise the floor to the **lowest version that resolves all of the above**. Try
`>=3.10` first; only go to `>=3.11` if 3.10 cannot resolve. Report which you
landed on and why.

Supporting evidence that 3.9 is already stale, not a deliberate commitment:
`[tool.black]` sets `target-version = ["py311"]` and `[tool.mypy]` sets
`python_version = "3.11"`. Update the `classifiers` list to match whatever floor
you choose — it currently advertises 3.9.

## Warnings

- **pytest 8 → 9 is a major bump.** It may break fixtures or collection. If the
  suite breaks, fix the tests — do not pin back to 8.x and do not skip tests to
  make it pass. If it proves genuinely unfixable within this phase, leave pytest
  at 8.x, say so plainly in `deviations`, and put it in `followups`.
- **Do not touch `psycopg2`.** It is the Postgres driver and switching it to
  `psycopg2-binary` is a packaging decision for a human.
- Re-lock with `poetry lock` and install with `poetry install` so `poetry.lock`
  is committed in a consistent state.

## Verify

Run each of these once, at the end. **Do not run `git diff` over the whole tree**
— a previous phase died from re-emitting large diffs repeatedly.

```
poetry lock
poetry install --with dev
poetry run python -m pytest tests/ -q
poetry run lint-imports
poetry run ruff check algosystem/
poetry run python -c "import algosystem; print(algosystem.__version__)"
poetry show pillow urllib3 requests pyarrow python-dotenv
```

The last command is the acceptance check for this phase: report the resolved
version of each, so the fix can be confirmed against the advisory floors above.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-6"`.

In `summary`, state the Python floor you landed on and the resolved `pillow`
version. In `deviations`, list any package you could **not** get to its patched
floor and exactly what blocked it. In `followups`, list any alert that remains
open and why.
