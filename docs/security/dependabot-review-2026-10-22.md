# Dependabot vulnerability review — 2026-10-22

## Result

GitHub reported **28 open Pillow alerts: 3 critical, 16 high, and 9 moderate**
when reviewed. They are 28 distinct advisories on one dependency, not 28
different packages. Every alert lists **Pillow 13.0.0** as its patched version.
At review time, the declared `pillow = ">=12.3.0"` allowed the affected 12.3.0
release, and GitHub could not determine an installed version because the
repository had no supported lockfile.

The principal remediation required a Python support change: at review time,
`pyproject.toml` advertised `python = ">=3.10,<4.0"` and CI tested Python
3.10, while [Pillow 13.0.0 requires Python >=3.11](https://pypi.org/project/pillow/13.0.0/).
Upstream [Pillow 13 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
confirm the security fixes and the removal of Python 3.10 support.

## Alert inventory

The linked GitHub alert is the source for each severity, affected range, and
patched version. All 28 were open when checked on 2026-10-22. Each affected
range includes 12.3.0 and each patched version is 13.0.0.

| Severity | Alert | Vulnerability and trigger |
| --- | --- | --- |
| Critical | [#58](https://github.com/AlgoGators/algosystem/security/dependabot/58) | Heap buffer overflow saving TIFF to `BytesIO`. |
| Critical | [#41](https://github.com/AlgoGators/algosystem/security/dependabot/41) | EPS filename argument injection in a Ghostscript invocation; potential code execution when that path is used. |
| Critical | [#32](https://github.com/AlgoGators/algosystem/security/dependabot/32) | Heap buffer overflow decoding crafted JPEG data. |
| High | [#43](https://github.com/AlgoGators/algosystem/security/dependabot/43) | Double free in `Image.transform()` after allocation failure. |
| High | [#40](https://github.com/AlgoGators/algosystem/security/dependabot/40) | Out-of-bounds access in morphology on a zero-width image. |
| High | [#36](https://github.com/AlgoGators/algosystem/security/dependabot/36) | TIFF encoder ColorMap mismatch causes out-of-bounds read. |
| High | [#33](https://github.com/AlgoGators/algosystem/security/dependabot/33) | TIFF decoder out-of-bounds read can disclose heap bytes through pixels. |
| High | [#56](https://github.com/AlgoGators/algosystem/security/dependabot/56) | PDF page-tree parent cycle can hang `rewrite_pages()`. |
| High | [#55](https://github.com/AlgoGators/algosystem/security/dependabot/55) | APNG disposal can allocate a full canvas before its decompression-bomb check. |
| High | [#54](https://github.com/AlgoGators/algosystem/security/dependabot/54) | Small MSP RLE file can expand into unbounded memory. |
| High | [#53](https://github.com/AlgoGators/algosystem/security/dependabot/53) | PDF `save_all` can take quadratic time. |
| High | [#45](https://github.com/AlgoGators/algosystem/security/dependabot/45) | `Image.merge()` can dereference a null pointer for an invalid first band. |
| High | [#39](https://github.com/AlgoGators/algosystem/security/dependabot/39) | GIF seek leaves rejected oversized dimensions on the image object, allowing memory exhaustion after a caught error. |
| High | [#37](https://github.com/AlgoGators/algosystem/security/dependabot/37) | TIFF decoder can return uninitialized memory as pixels for short JPEG strips. |
| High | [#35](https://github.com/AlgoGators/algosystem/security/dependabot/35) | Malformed PDF page tree or trailer chain can recurse without bound. |
| High | [#59](https://github.com/AlgoGators/algosystem/security/dependabot/59) | Crafted TIFF tags can cause encoder memory disclosure or a segmentation fault. |
| High | [#48](https://github.com/AlgoGators/algosystem/security/dependabot/48) | MIC frame counting can loop indefinitely through an embedded TIFF. |
| High | [#46](https://github.com/AlgoGators/algosystem/security/dependabot/46) | Rank filtering a zero-size image can dereference a null pointer. |
| High | [#44](https://github.com/AlgoGators/algosystem/security/dependabot/44) | FreeType glyph rendering with an active stroker can free an invalid pointer. |
| Moderate | [#49](https://github.com/AlgoGators/algosystem/security/dependabot/49) | GIF comment concatenation on open can take quadratic time. |
| Moderate | [#47](https://github.com/AlgoGators/algosystem/security/dependabot/47) | GIF comment copying on save can take quadratic time. |
| Moderate | [#51](https://github.com/AlgoGators/algosystem/security/dependabot/51) | A small XBM file can cause minutes of regex processing in `Image.open()`. |
| Moderate | [#50](https://github.com/AlgoGators/algosystem/security/dependabot/50) | `Image.quantize()` with an empty palette can leak stack memory. |
| Moderate | [#38](https://github.com/AlgoGators/algosystem/security/dependabot/38) | EPS `load(scale=...)` can make Ghostscript render beyond the configured image-size limit. |
| Moderate | [#34](https://github.com/AlgoGators/algosystem/security/dependabot/34) | Tiled TIFF decoding can read beyond a tile buffer. |
| Moderate | [#52](https://github.com/AlgoGators/algosystem/security/dependabot/52) | PDF `get_value()` has an ineffective recursion-depth guard when appending to an existing PDF. |
| Moderate | [#42](https://github.com/AlgoGators/algosystem/security/dependabot/42) | `P;2L` and `P;4L` decoders can read one to three bytes beyond the input buffer. |
| Moderate | [#57](https://github.com/AlgoGators/algosystem/security/dependabot/57) | TIFF encoding to an in-memory buffer can use freed heap memory. |

## AlgoSystem exposure

The tracked `algosystem/` and `tests/` code has no direct `PIL` import or
image-upload parser. The public backtest path accepts a pandas price/equity
series; the reporting adapter calls quantstats to generate a tearsheet.
Consequently, the listed malicious-image and Ghostscript preconditions are not
established in the normal tracked API path. This is a **limited reachability
finding**, not proof that every downstream or private caller is safe.

Pillow is still a runtime dependency. The manifest declares it directly as a
security floor, and Matplotlib also depends on Pillow. Removing the direct
declaration alone would let Matplotlib bring Pillow back and would not establish
a safe version. Generated charts may exercise Pillow without accepting a
malicious image. Confirm actual deployed versions and any off-repository image,
PDF, EPS, or font ingestion before downgrading operational priority.

## Remediation in this working tree

- `pyproject.toml` now requires Python `>=3.11,<4.0` and Pillow `>=13.0.0`.
  This protects downstream installs that do not use this repository's lockfile.
- CI now tests Python 3.11 and 3.12; the package classifier, installation
  guidance, and `.codex/SPEC.md` support guidance reflect the new floor.
- `poetry.lock` is now present and no longer ignored, ready to be tracked with
  Pillow 13.0.0 resolved. `poetry check --lock` passes.
- The full test suite passes with Python 3.12 and Pillow 13.0.0. An isolated
  Python 3.11 smoke test generated a quantstats 0.0.86 HTML tearsheet with
  Pillow 13.0.0. A completely clean install was blocked by missing local
  `pg_config` while compiling `psycopg2`; this is an environment prerequisite
  rather than a Pillow conflict.
- Black found no formatting changes across 132 Python files. Isort, Ruff,
  and all eight import contracts pass against the current main branch.

GitHub's alerts remain open until these working-tree changes reach the default
branch and Dependabot rescans it. No alerts were dismissed or manually altered.
