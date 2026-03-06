"""
Fetches the MD DNR trout stocking page, extracts meaningful content,
and compares it against the previously stored hash.

Outputs GitHub Actions step outputs:
  changed = true/false
  summary = human-readable description of what changed
"""

import hashlib
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://dnr.maryland.gov/fisheries/pages/trout/stocking.aspx"
HASH_FILE = Path("data/last_hash.txt")
CONTENT_FILE = Path("data/last_content.txt")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TroutStockingWatcher/1.0; "
        "+https://github.com)"
    )
}


def fetch_content() -> str:
    """Fetch and extract the meaningful text content from the stocking page."""
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Drop noisy tags
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()

    # SharePoint pages nest content in a few possible containers — try each
    main = (
        soup.find("div", {"id": "DeltaPlaceHolderMain"})
        or soup.find("div", {"id": "s4-bodyContainer"})
        or soup.find("div", {"class": "ms-rtestate-field"})
        or soup.find("main")
        or soup.body
    )

    text = main.get_text(separator="\n", strip=True) if main else soup.get_text()

    # Collapse blank lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)


def set_output(name: str, value: str) -> None:
    """Write a GitHub Actions step output."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            # Multiline-safe encoding
            safe = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            f.write(f"{name}={safe}\n")
    else:
        # Local dev fallback
        print(f"[output] {name}={value}")


def build_summary(old_content: str | None, new_content: str) -> str:
    """Build a short, useful notification message."""
    if old_content is None:
        return "Baseline snapshot saved. Future changes will trigger notifications."

    old_lines = set(old_content.splitlines())
    new_lines = set(new_content.splitlines())

    added = [ln for ln in new_lines - old_lines if ln]
    removed = [ln for ln in old_lines - new_lines if ln]

    parts = ["The Maryland DNR trout stocking page has changed.\n"]

    if added:
        parts.append("New content detected:")
        for ln in added[:5]:  # cap at 5 lines to keep notification short
            parts.append(f"  + {ln}")
        if len(added) > 5:
            parts.append(f"  ... and {len(added) - 5} more additions")

    if removed:
        parts.append("Removed content:")
        for ln in removed[:5]:
            parts.append(f"  - {ln}")
        if len(removed) > 5:
            parts.append(f"  ... and {len(removed) - 5} more removals")

    return "\n".join(parts)


def main() -> None:
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        content = fetch_content()
    except Exception as exc:
        print(f"Error fetching page: {exc}", file=sys.stderr)
        set_output("changed", "false")
        sys.exit(0)

    current_hash = hashlib.sha256(content.encode()).hexdigest()
    print(f"Current hash: {current_hash}")

    stored_hash = HASH_FILE.read_text().strip() if HASH_FILE.exists() else None
    old_content = CONTENT_FILE.read_text() if CONTENT_FILE.exists() else None

    if stored_hash is None:
        print("First run — saving baseline snapshot.")
        HASH_FILE.write_text(current_hash)
        CONTENT_FILE.write_text(content)
        set_output("changed", "false")
        return

    print(f"Stored hash:  {stored_hash}")

    if current_hash == stored_hash:
        print("No changes detected.")
        set_output("changed", "false")
        return

    print("Change detected!")
    summary = build_summary(old_content, content)
    print(summary)

    HASH_FILE.write_text(current_hash)
    CONTENT_FILE.write_text(content)

    set_output("changed", "true")
    set_output("summary", summary)


if __name__ == "__main__":
    main()
