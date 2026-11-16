#!/usr/bin/env bash
# Python. Fails the build: real lint errors (syntax, undefined names) in files this PR changes.
# Report only: the same lint across the repo, and the unit tests.
set -u
. ci/changed.sh
FAIL=0
pip install --quiet ruff >/dev/null 2>&1 || echo "could not install ruff: lint skipped"
RULES="E9,F63,F7,F82"

PY=$(printf '%s\n' "$CHANGED" | grep -E '\.py$' || true)
if [ -n "$PY" ] && command -v ruff >/dev/null; then
  echo "--- lint: changed Python files ---"
  while IFS= read -r f; do
    [ -f "$f" ] && { ruff check --select "$RULES" --output-format concise --no-cache "$f" || FAIL=1; }
  done <<< "$PY"
else
  echo "no Python files changed: lint has nothing to check"
fi

if [ "$BASELINE" = 1 ] && command -v ruff >/dev/null; then
  echo "--- baseline (report only): real lint errors across the repo today ---"
  ruff check --select "$RULES" --output-format concise --no-cache . | tail -20 || true
fi

HAS_TESTS=$(find . \( -name 'test_*.py' -o -name '*_test.py' \) -not -path './.git/*' -not -path '*/node_modules/*' | head -1)
if [ -n "$HAS_TESTS" ] && { [ -n "$PY" ] || [ "$BASELINE" = 1 ]; }; then
  echo "--- unit tests (report only) ---"
  pip install --quiet pytest >/dev/null 2>&1 || true
  find . -maxdepth 2 -name 'requirements*.txt' -not -path './.git/*' | sort | head -4 | while IFS= read -r req; do
    timeout 300 pip install --quiet -r "$req" >/dev/null 2>&1 || report_only "installing $req"
  done
  [ -f pyproject.toml ] && { timeout 420 pip install --quiet -e . >/dev/null 2>&1 || true; }
  timeout 600 python -m pytest -q --maxfail=25 -p no:cacheprovider 2>&1 | tail -40
  [ "${PIPESTATUS[0]}" = "0" ] || report_only "the unit tests"
elif [ -z "$HAS_TESTS" ]; then
  echo "no Python tests in this repo yet"
fi

if [ "$FAIL" != 0 ]; then must_fix "Python lint" "ruff check --select $RULES <your changed files>"; exit 1; fi
echo "Python checks done."
