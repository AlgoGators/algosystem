import subprocess
import sys
from pathlib import Path


def test_validation_domain_import_does_not_load_heavy_modules():
    code = """
import sys
import algosystem.validation.domain

forbidden = {"pandas", "matplotlib", "multiprocessing", "quantstats"}
loaded = sorted(forbidden.intersection(sys.modules))
if loaded:
    raise SystemExit(f"validation domain imported forbidden modules: {loaded}")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_domain_files_do_not_hide_layer_imports_with_dynamic_imports():
    root = Path(__file__).resolve().parents[3] / "algosystem"
    offenders = []
    for path in sorted(root.glob("*/domain/**/*.py")):
        text = path.read_text(encoding="utf-8")
        if any(pattern in text for pattern in ("import_module", "__import__", "importlib")):
            offenders.append(str(path.relative_to(root.parent)))

    assert offenders == []
