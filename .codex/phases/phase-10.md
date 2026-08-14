# Phase 10 — Fix the CI failure: quantstats' undeclared IPython dependency

Read `.codex/SPEC.md` first. This is a small, surgical phase. Do not refactor
anything beyond what is described here.

## The bug

CI fails on Python 3.10, 3.11 and 3.12 with:

```
ImportError while importing test module
'tests/backtesting/infrastructure/test_quantstats_calculator.py'.
E   ModuleNotFoundError: No module named 'IPython'
```

The full suite passes locally (243 passed). It fails only on a clean install.

Root cause: `quantstats` imports `IPython` at runtime but declares **no**
dependencies at all in its package metadata — `distribution('quantstats').requires`
is empty. Local developer venvs happen to have IPython left over from an older
dependency set, so the import resolves. CI installs clean and it does not.

This is a genuine packaging bug in our manifest, not a CI configuration problem.
Anyone who `pip install algosystem` into a clean environment and touches the
tearsheet path hits the same `ModuleNotFoundError`.

## Job A — Declare the dependency

Add `ipython` to `[tool.poetry.dependencies]` in `pyproject.toml`, in the main
(runtime) group — **not** the dev group. The tearsheet path is shipped library
functionality, so the dependency is a runtime one.

Constraints:

- Use a floor plus an open-ended upper bound consistent with how the
  neighbouring entries are written (e.g. `>=8.12.0`). Do **not** pin an exact
  version.
- Respect the existing `python = ">=3.10,<4.0"` floor: the constraint you pick
  must resolve on Python 3.10 as well as 3.12. Newer IPython majors have dropped
  3.10 support — verify the constraint actually resolves across the full
  supported range rather than assuming.
- There is a `.codex/RILEY-OPT-INTEGRATION.md` note that the previous commit
  added several dependency floors purely to clear security advisories, with a
  comment saying so. Follow the same commenting style if you add a similar note.

## Job B — Check for the same class of bug elsewhere

`quantstats` declaring no metadata dependencies means **every** module it
imports is undeclared for us. IPython is the one CI caught because a test
imports that path eagerly; there may be others that only fail on a code path CI
does not currently exercise.

Determine what `quantstats` actually imports at runtime and cross-check each
against our manifest. Anything it needs that we do not declare, and that is not
already pulled in transitively by another declared dependency, must be declared
too. Report exactly what you checked and what you found.

Do not speculatively add packages that are genuinely already transitive — state
which ones you confirmed transitive and via which parent.

## Job C — Prove it the way CI does

The whole point is that a local venv hides this. Do not verify by running the
suite in the existing environment — it will pass regardless and tell you
nothing.

Verify in a **clean** environment that does not inherit the developer venv's
leftovers. Create a throwaway virtual environment, install the project from the
manifest, and run the failing test module in it:

```
tests/backtesting/infrastructure/test_quantstats_calculator.py
```

Report the pass/fail from that clean environment specifically, and say which
Python version you ran it on. If you cannot create a clean environment in this
sandbox, say so plainly in `deviations` rather than substituting a run in the
existing venv and calling it verification.

## Do not

- Do not add IPython to the dev group as a workaround.
- Do not add a `pytest.importorskip` or a skip marker to the failing test to get
  CI green. The dependency is genuinely missing; hiding the symptom ships a
  library that breaks for users.
- Do not vendor or stub IPython.
- Do not bump the project version. It stays at **0.1.9**.
- Do not touch `poetry.lock` expectations — it is gitignored by deliberate
  decision.

## Verify

Run each **once**, at the end:

```
poetry run python -m pytest tests/ -q
poetry run lint-imports
poetry run ruff check algosystem/
poetry run black --check algosystem/ tests/
```

All contracts must remain kept. The suite must still be 243 passed.

## Budget discipline

Never run `git diff` over the whole tree — Phase 4 and Phase 9 both died that
way. Run each verification command once, at the end. This phase is small; if you
find yourself making sweeping edits you have misread it.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-10"`.

- `summary` — the constraint you chose, why, and the clean-environment result
  from Job C.
- `deviations` — anything about Job B or the clean-environment check that did
  not go as described above.
- `followups` — any other undeclared-dependency risk you found but did not fix.
