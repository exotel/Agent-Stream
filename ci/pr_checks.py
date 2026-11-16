"""PR checks. Standard library only, so nothing is downloaded.

On a pull request: fails the build when a file the pull request adds or changes has an
unresolved merge-conflict marker, or is a .json / .py / .sh file that does not parse.
Every failure names the file and the fix, in the job log and as an annotation on the diff.

On a manual run (no pull request): checks every tracked file and reports only, to show
where the repo stands. It never fails the build.
"""
import json
import os
import pathlib
import py_compile
import re
import subprocess
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", "vendor", "third_party"}
MARKERS = ("<<<<<<< ", ">>>>>>> ")
problems = []  # each: {"path", "line", "summary", "fix"}
ON_PR = bool(os.environ.get("PR_NUMBER"))


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def files_to_check():
    """Files this pull request adds or changes; on a manual run, every tracked file."""
    if not ON_PR:
        listed = git("ls-files", "-z")
        if listed.returncode != 0:
            sys.exit("could not list tracked files (git ls-files failed): " + listed.stderr.strip())
        return [name for name in listed.stdout.split("\0") if name]
    base = os.environ.get("PR_BASE_BRANCH", "master")
    fetched = git("fetch", "-q", "origin", base, "--depth=50")
    diff = git("diff", "--name-only", "--diff-filter=d", "-z", "FETCH_HEAD...HEAD")
    if diff.returncode != 0:
        diff = git("diff", "--name-only", "--diff-filter=d", "-z", "FETCH_HEAD", "HEAD")
    if fetched.returncode != 0 or diff.returncode != 0:
        print("Could not work out which files this pull request changes, so nothing was checked.")
        print("git said:", (fetched.stderr or diff.stderr).strip())
        print("Re-run the workflow. If it keeps failing, check that the destination branch '%s' exists." % base)
        sys.exit(1)
    return [name for name in diff.stdout.split("\0") if name]


def json_with_comments(path):
    """Config files that tools read as JSON-with-comments; strict JSON parsing would reject them."""
    name = path.name
    return name.startswith(("tsconfig", "jsconfig")) or name in {".eslintrc.json", "devcontainer.json"} \
        or ".vscode" in path.parts


def add(path, line, summary, fix):
    problems.append({"path": str(path), "line": line, "summary": summary, "fix": fix})


def annotate():
    """Mark each problem on the pull request diff (GitHub reads these lines from the job log)."""
    for problem in problems:
        message = f"{problem['summary']}. {problem['fix']}".replace("%", "%25").replace("\r", " ").replace("\n", " ")
        print(f"::error file={problem['path']},line={problem['line']}::{message}")


for path in sorted(pathlib.Path(name) for name in files_to_check()):
    if not path.is_file() or path.is_symlink() or SKIP_DIRS & set(path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue  # binary or unreadable: nothing to parse
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith(MARKERS):
            add(path, number, "Unresolved merge-conflict marker",
                "Resolve the conflict and delete the <<<<<<< / ======= / >>>>>>> lines.")
            break
    if path.suffix == ".json" and not json_with_comments(path):
        try:
            json.loads(text)
        except json.JSONDecodeError as err:
            add(path, err.lineno, f"Not valid JSON: {err.msg}", f"Check with: python3 -m json.tool {path}")
    elif path.suffix == ".py":
        try:
            py_compile.compile(str(path), doraise=True, cfile="/tmp/pr_check.pyc")
        except py_compile.PyCompileError as err:
            line = getattr(err.exc_value, "lineno", None) or 1
            add(path, line, f"Python syntax error: {getattr(err.exc_value, 'msg', 'invalid syntax')}",
                f"Check with: python3 -m py_compile {path}")
    elif path.suffix == ".sh":
        first_line = text.splitlines()[0] if text else ""
        shell = "sh" if re.match(r"#!\s*\S*(/|env\s+)sh(\s|$)", first_line) else "bash"
        result = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True)
        if result.returncode != 0:
            message = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "syntax error"
            # bash says "file: line 5: ..."; dash says "file: 5: ..."
            found = re.search(r":\s*(?:line\s+)?(\d+):", message)
            line = int(found.group(1)) if found else 1
            add(path, line, f"Shell syntax error: {message}", f"Check with: {shell} -n {path}")

if not ON_PR:
    print("Manual run (no pull request): every tracked file was checked. This run reports only and never fails.")
    for problem in problems:
        print(f" - {problem['path']}:{problem['line']}: {problem['summary']}. {problem['fix']}")
    print(f"{len(problems)} problem(s) in the repo today." if problems else "No problems in the repo today.")
    sys.exit(0)

annotate()

if problems:
    print("================= WHAT YOU NEED TO DO =================")
    for problem in problems:
        print(f" - {problem['path']}:{problem['line']}: {problem['summary']}. {problem['fix']}")
    print("Fix the files above and push; the checks re-run automatically.")
    print("=======================================================")
    sys.exit(1)
print("PR checks passed: the files this pull request changes have no conflict markers and all JSON / Python / shell files parse.")
