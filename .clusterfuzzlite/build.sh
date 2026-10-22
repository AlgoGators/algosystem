#!/bin/bash -eu

python3 -m pip install --no-deps .

pyinstaller --distpath "$OUT" --onefile --name metric_key_fuzzer.pkg fuzz/metric_key_fuzzer.py
cat > "$OUT/metric_key_fuzzer" <<'WRAPPER'
#!/bin/sh
# LLVMFuzzerTestOneInput is provided by the Atheris executable.
this_dir=$(dirname "$0")
exec "$this_dir/metric_key_fuzzer.pkg" "$@"
WRAPPER
chmod +x "$OUT/metric_key_fuzzer"

# Keep representative valid and invalid metric names in the initial corpus.
python3 - <<'CORPUS'
import os
from zipfile import ZipFile

from algosystem.shared.metric_key import LEGACY_ALIASES, MetricKey

with ZipFile(os.path.join(os.environ["OUT"], "metric_key_fuzzer_seed_corpus.zip"), "w") as archive:
    for name in (MetricKey.SHARPE_RATIO.value, MetricKey.BETA.value, *LEGACY_ALIASES, "invalid"):
        archive.writestr(name, name)
CORPUS
