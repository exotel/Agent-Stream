# Sourced by the language scripts. Sets:
#   CHANGED  - files this pull request adds or modifies, one per line
#   BASELINE - 1 on a manual run, or when the pull request changes the workflow itself; the language scripts then also
#              run their report-only checks across the whole repo once, to show where it stands
BASE="${PR_BASE_BRANCH:-master}"
DIFF_OK=1
git fetch -q origin "$BASE" --depth=50 2>/dev/null || DIFF_OK=0
CHANGED=$(git diff --name-only --diff-filter=d FETCH_HEAD...HEAD 2>/dev/null) \
  || CHANGED=$(git diff --name-only --diff-filter=d FETCH_HEAD HEAD 2>/dev/null) || { CHANGED=""; DIFF_OK=0; }
if [ "$DIFF_OK" = 0 ] && [ -n "${PR_NUMBER:-}" ]; then
  echo "Could not work out which files this pull request changes (git fetch or git diff against '$BASE' failed), so nothing was checked."
  echo "Re-run the workflow. If it keeps failing, check that the destination branch exists."
  exit 1
fi
BASELINE=0
if [ -z "${PR_NUMBER:-}" ]; then
  echo "manual run (no pull request): report-only checks run across the whole repo; the blocking checks apply to pull requests"
  CHANGED=""; BASELINE=1
fi
if printf '%s\n' "$CHANGED" | grep -qE '^(\.github/workflows/|ci/)'; then BASELINE=1; fi

report_only() {  # report_only "<what>"  - call after a report-only command failed
  echo "REPORT-ONLY: $1 failed or could not run in this image. This does not fail the build."
}
must_fix() {     # must_fix "<gate>" "<how to check locally>"
  echo ""
  echo "================= WHAT YOU NEED TO DO ================="
  echo "$1 failed on files this pull request changes (listed above)."
  echo "Check locally: $2"
  echo "Fix and push; the checks re-run automatically."
  echo "======================================================="
}
