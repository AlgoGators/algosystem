#!/bin/bash -eu

# The target exercises the Python domain and needs only its numeric dependencies.
python3 -m pip install --no-deps .
python3 -m pip install numpy pandas

pyinstaller --distpath "$OUT" --onefile --name ticker_fuzzer.pkg fuzz/ticker_fuzzer.py
cat > "$OUT/ticker_fuzzer" <<'WRAPPER'
#!/bin/sh
# LLVMFuzzerTestOneInput is provided by the Atheris executable.
this_dir=$(dirname "$0")
exec "$this_dir/ticker_fuzzer.pkg" "$@"
WRAPPER
chmod +x "$OUT/ticker_fuzzer"
