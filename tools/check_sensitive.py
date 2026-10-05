"""Inspect Git-index content; never print matched secret values."""
from pathlib import Path
import re
import subprocess
import sys

PATTERNS = {
    "OpenAI token": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "credential URL": re.compile(rb"https?://[^\s/:]+:[^\s/@]+@"),
    "hardcoded provider key": re.compile(rb"(?:OPENAI_API_KEY|FAL_KEY)\s*=\s*[\"'][^\"'\r\n]{12,}[\"']"),
}


def check(git="git", root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    def run(*args):
        return subprocess.check_output([git, "-C", str(root), *args])
    names = [name for name in run("ls-files", "--cached", "-z").decode().split("\0") if name]
    failures = []
    for name in names:
        path = Path(name)
        if (path.name.startswith(".env") and path.name != ".env.example") or path.suffix.lower() in (".pem", ".key", ".p12", ".pfx", ".db", ".sqlite", ".sqlite3", ".pyc") or path.parts[0] in ("data", "media", "uploads", "recovery", "work", "outputs", ".venv"):
            failures.append((name, "sensitive or generated file")); continue
        content = run("show", ":" + name)
        for label, pattern in PATTERNS.items():
            if pattern.search(content): failures.append((name, label))
    for name, label in failures: print(f"BLOCKED: {name}: {label}")
    print(f"Inspected {len(names)} Git-index files; {len(failures)} findings. Secret values are never printed.")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(check(sys.argv[1] if len(sys.argv) > 1 else "git"))
