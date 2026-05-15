import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".vscode",
    "node_modules",
}

PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?key|client[_-]?secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/$+=:.]{12,}"),
    re.compile(r"(?i)(token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/$+=:.]{12,}"),
    re.compile(r"ca-pub-\d{10,}"),
]

IGNORE_LINE_HINTS = (
    "your_application_password",
    "get_access_token(",
    "request.form['password']",
    "request.form.get('password'",
)


def should_scan(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return False
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".xlsx", ".db"}:
        return False
    return True


def scan_file(path: Path) -> list[str]:
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings
    for i, line in enumerate(text.splitlines(), start=1):
        if any(hint in line for hint in IGNORE_LINE_HINTS):
            continue
        for pattern in PATTERNS:
            if pattern.search(line):
                findings.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()[:180]}")
                break
    return findings


def main() -> None:
    matches = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if not should_scan(path):
            continue
        matches.extend(scan_file(path))

    if matches:
        print("Potential secret exposures found:")
        for item in matches:
            print(f"- {item}")
    else:
        print("No obvious secret patterns found.")


if __name__ == "__main__":
    main()
