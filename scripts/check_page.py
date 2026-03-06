"""
Fetches MD DNR trout stocking data from the JSON API, filters for
Gunpowder Falls rows, and compares against the previous snapshot.

Writes:
  data/gunpowder_rows.json  — current Gunpowder Falls rows
  data/last_check.json      — metadata for the GitHub Pages site

GitHub Actions step outputs:
  changed        = true/false
  summary        = short one-liner for push notification
  email_body     = full email text
  email_subject  = email subject line
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://webapps02.dnr.state.md.us/DNRTroutStockingAPI/api/RecentStockings"
PAGE_URL = "https://dnrweb.dnr.state.md.us/fisheries/stocking/stockingtable.html"
DATA_FILE = Path("data/gunpowder_rows.json")
META_FILE = Path("data/last_check.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TroutStockingWatcher/1.0; "
        "+https://github.com)"
    )
}

SPECIES_MAP = {"Rainbow": "RB", "Golden": "GN", "Brown": "BN"}


# ---------------------------------------------------------------------------
# Fetch & filter
# ---------------------------------------------------------------------------

def fetch_gunpowder_rows() -> list[dict]:
    resp = requests.get(API_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rows = [
        r for r in data
        if "gunpowder" in r.get("LOCATION", "").lower()
    ]

    for r in rows:
        species = r.get("Species", "")
        r["_species_abbr"] = SPECIES_MAP.get(species, species)

    rows.sort(key=lambda r: r.get("ActivityDate", ""), reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Row identity & formatting
# ---------------------------------------------------------------------------

def row_key(r: dict) -> str:
    return "|".join([
        r.get("ActivityDate", ""),
        r.get("LOCATION", ""),
        r.get("Species", ""),
        str(r.get("NumOfFish", "")),
    ])


def fmt_date(iso: str) -> str:
    try:
        if iso.startswith("/Date("):
            ms = int(iso[6:iso.index(")")])
            return datetime.utcfromtimestamp(ms / 1000).strftime("%m/%d/%Y")
        return iso[:10].replace("-", "/")
    except Exception:
        return iso


def fmt_row(r: dict, prefix: str = "   ") -> str:
    date = fmt_date(r.get("ActivityDate", ""))
    location = r.get("LOCATION", "")
    count = int(r.get("NumOfFish") or 0)
    species = r.get("_species_abbr", r.get("Species", ""))
    regs = r.get("RegulationDetails", "")
    return f"{prefix}{date}  |  {location}  |  {count:,} {species}  |  {regs}"


# ---------------------------------------------------------------------------
# Email body builder
# ---------------------------------------------------------------------------

def build_email_body(current: list[dict], previous: list[dict] | None,
                     new_keys: set, gone_rows: list[dict]) -> tuple[str, str]:
    if previous is None:
        lines = [
            "Gunpowder Falls — Trout Stocking Data",
            "=" * 42,
            "(First run — baseline saved. Future emails will highlight changes.)",
            "",
        ]
        for r in current:
            lines.append(fmt_row(r))
        lines += ["", PAGE_URL]
        return "\n".join(lines), "Baseline saved."

    changed = bool(new_keys or gone_rows)
    curr_map = {row_key(r): r for r in current}

    lines = ["Gunpowder Falls — Trout Stocking Data", "=" * 42]

    if changed:
        if new_keys:
            lines += ["", "  *** NEW STOCKINGS ***"]
            for k in new_keys:
                lines.append(fmt_row(curr_map[k], prefix="  [NEW]  "))
        if gone_rows:
            lines += ["", "  *** REMOVED FROM FEED ***"]
            for r in gone_rows:
                lines.append(fmt_row(r, prefix="  [GONE] "))
        lines += ["", "  --- Unchanged ---"]
    else:
        lines += ["", "  No changes since last check.", ""]

    for r in current:
        if row_key(r) not in new_keys:
            lines.append(fmt_row(r))

    lines += ["", "-" * 42, PAGE_URL]

    body = "\n".join(lines)
    if new_keys:
        push = f"{len(new_keys)} new Gunpowder Falls stocking(s) added."
    elif gone_rows:
        push = f"{len(gone_rows)} Gunpowder Falls stocking(s) removed from feed."
    else:
        push = "No changes to Gunpowder Falls stockings."

    return body, push


# ---------------------------------------------------------------------------
# GitHub Actions output helpers
# ---------------------------------------------------------------------------

def set_output(name: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            safe = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            f.write(f"{name}={safe}\n")
    else:
        print(f"[output] {name}={value[:120]}")


def set_multiline_output(name: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        delimiter = "EOF_TROUT"
        with open(github_output, "a") as f:
            f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
    else:
        print(f"[output] {name}=\n{value}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        current = fetch_gunpowder_rows()
    except Exception as exc:
        print(f"Error fetching data: {exc}", file=sys.stderr)
        # Write error state to metadata so the page can show it
        META_FILE.write_text(json.dumps({
            "timestamp": now_iso,
            "changed": False,
            "error": str(exc),
            "new_keys": [],
            "gone_rows": [],
        }, indent=2))
        set_output("changed", "false")
        set_multiline_output("email_body", f"Error fetching stocking data: {exc}")
        set_output("email_subject", "ERROR: MD DNR Trout Stocking Watcher")
        sys.exit(0)

    print(f"Fetched {len(current)} Gunpowder Falls row(s)")

    previous = None
    if DATA_FILE.exists():
        try:
            previous = json.loads(DATA_FILE.read_text())
        except Exception:
            previous = None

    # Diff
    curr_key_set = {row_key(r) for r in current}
    prev_key_set = {row_key(r) for r in previous} if previous else set()
    new_keys = curr_key_set - prev_key_set
    gone_keys = prev_key_set - curr_key_set

    prev_map = {row_key(r): r for r in previous} if previous else {}
    gone_rows = [prev_map[k] for k in gone_keys]

    changed = bool(new_keys or gone_rows) and previous is not None

    print(f"New: {len(new_keys)}  Gone: {len(gone_rows)}  Changed: {changed}")

    email_body, push_summary = build_email_body(current, previous, new_keys, gone_rows)

    # Save current data
    DATA_FILE.write_text(json.dumps(current, indent=2))

    # Save metadata for GitHub Pages
    META_FILE.write_text(json.dumps({
        "timestamp": now_iso,
        "changed": changed,
        "first_run": previous is None,
        "error": None,
        "new_keys": list(new_keys),
        "gone_rows": gone_rows,
    }, indent=2))

    if changed:
        subject = "UPDATED: Gunpowder Falls Trout Stocking"
    elif previous is None:
        subject = "Trout Watcher: Baseline saved"
    else:
        subject = "No change: Gunpowder Falls Trout Stocking"

    set_output("changed", "true" if changed else "false")
    set_output("summary", push_summary)
    set_multiline_output("email_body", email_body)
    set_output("email_subject", subject)


if __name__ == "__main__":
    main()
