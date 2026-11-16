#!/usr/bin/env bash
# JavaScript / TypeScript. Fails the build: a changed .js file that does not parse.
# Report only: the repo's own lint and test scripts from package.json.
set -u
. ci/changed.sh
FAIL=0
JS=$(printf '%s\n' "$CHANGED" | grep -E '\.(js|mjs|cjs)$' | grep -vE '(^|/)(node_modules|dist|build)/|\.min\.js$' || true)
if [ -n "$JS" ]; then
  echo "--- syntax: changed JavaScript files ---"
  while IFS= read -r f; do
    [ -f "$f" ] && { node --check "$f" || FAIL=1; }
  done <<< "$JS"
else
  echo "no JavaScript files changed: syntax check has nothing to check"
fi

PKGS=$(find . -maxdepth 2 -name package.json -not -path '*/node_modules/*' -not -path './.git/*' | sed 's|/package.json$||' | sort | head -4)
if [ -z "$PKGS" ]; then
  echo "no package.json at the repo root or one level down: lint and test scripts skipped"
else
  WEB=$(printf '%s\n' "$CHANGED" | grep -E '\.(js|mjs|cjs|jsx|ts|tsx)$|(^|/)package(-lock)?\.json$' || true)
  while IFS= read -r dir; do
    prefix="${dir#./}"; [ "$prefix" = "." ] && prefix=""
    touched=0
    [ "$BASELINE" = 1 ] && touched=1
    if [ -n "$WEB" ]; then
      if [ -z "$prefix" ]; then touched=1; elif printf '%s\n' "$WEB" | grep -q "^$prefix/"; then touched=1; fi
    fi
    [ "$touched" = 1 ] || continue
    SCRIPTS=$(cd "$dir" && node -e 'const s=require("./package.json").scripts||{};console.log(["lint","test"].filter(k=>s[k]).join(" "))' 2>/dev/null)
    if [ -z "$SCRIPTS" ]; then echo "${prefix:-.}/package.json has no lint or test script yet"; continue; fi
    echo "--- ${prefix:-.}: install (report only) ---"
    if ( cd "$dir" && if [ -f package-lock.json ]; then timeout 420 npm ci --no-audit --no-fund >/dev/null 2>&1; else timeout 420 npm install --no-audit --no-fund >/dev/null 2>&1; fi ); then
      for s in $SCRIPTS; do
        echo "--- ${prefix:-.}: npm run $s (report only) ---"
        ( cd "$dir" && CI=true timeout 420 npm run "$s" 2>&1 | tail -40; [ "${PIPESTATUS[0]}" = "0" ] ) || report_only "npm run $s in ${prefix:-.}"
      done
    else
      report_only "installing npm packages in ${prefix:-.}"
    fi
  done <<< "$PKGS"
fi

if [ "$FAIL" != 0 ]; then must_fix "JavaScript syntax check" "node --check <your changed files>"; exit 1; fi
echo "JavaScript checks done."
