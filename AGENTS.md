# AlgoSystem — agent instructions

This repository is mid-restructure onto a domain-driven layout.

**Read `.codex/SPEC.md` before changing anything.** It defines the target
architecture, the non-negotiable dependency rules (R1–R7), the package layout,
and the reply protocol. It is authoritative.

Phase prompts live in `.codex/phases/`. Reports from completed phases live in
`.codex/reports/` — read the most recent one to see what state the code is
actually in.

Quick orientation:

- AlgoSystem does three things: backtest a price series, persist runs to
  Postgres, and report via **quantstats tearsheets**. Reporting is not
  reimplemented here; the old custom dashboard was deleted deliberately.
- The domain (`algosystem/*/domain/`) imports only stdlib, pandas, numpy and
  `algosystem.shared`. Vendor libraries live behind ports in `infrastructure/`.
- Metric names come from the `MetricKey` enum in `algosystem/shared/`, never
  from string literals.
- Failures raise typed errors from `algosystem/shared/errors.py`. Never return
  `{"error": ...}`. Never write a bare `except:`.

Run checks with `python -m pytest tests/ -q`, `python -m black algosystem/
tests/`, `python -m isort algosystem/ tests/`.

Do not commit; leave changes in the working tree for review.
