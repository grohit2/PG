"""
Cross-platform web-page watcher that archives HTML *and* its hash
to patient/<id>/<timestamp_IST>.{html,sha256}

Dependencies: requests, beautifulsoup4
    pip install requests beautifulsoup4
Requires Python ≥ 3.9 (for zoneinfo).
"""

from __future__ import annotations
import hashlib
import pathlib
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo  # ← std-lib in 3.9+

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────
PATIENT_URLS = [
    "http://115.241.194.20/LIS/Reports/Patient_Report.aspx/20250335112",
    # add more URLs here as you scale
]
CHECK_EVERY_SEC = 30          # 10 min (use smaller while testing)
IST = ZoneInfo("Asia/Kolkata") # Indian Standard Time (UTC+05:30)
# ──────────────────────────────────────────────────────────────


def ts_ist() -> str:
    """Return a timestamp suitable for filenames, in IST."""
    return datetime.now(IST).strftime("%Y%m%d_%H%M%S")


def log(msg: str) -> None:
    """Unified logger (local time in ISO-8601)."""
    print(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {msg}")


def normalize(html: str) -> str:
    """Reduce HTML to the stable bits you care about before hashing."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("form#form1")
    return (main or soup).get_text(strip=True)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_patient_dir(patient_id: str) -> pathlib.Path:
    root = pathlib.Path("patient") / patient_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_prev_hash(patient_dir: pathlib.Path) -> str | None:
    try:
        return (patient_dir / "last_hash.txt").read_text()
    except FileNotFoundError:
        return None


def save_prev_hash(patient_dir: pathlib.Path, h: str) -> None:
    (patient_dir / "last_hash.txt").write_text(h)


def archive_snapshot(patient_dir: pathlib.Path, ts: str, html: str, digest: str) -> None:
    """Write the HTML and its digest next to each other."""
    (patient_dir / f"{ts}.html").write_text(html, encoding="utf-8")
    (patient_dir / f"{ts}.sha256").write_text(digest)
    log(f"    ↳ snapshot saved as {patient_dir / (ts + '.html')}")


def check_once(url: str) -> None:
    patient_id = url.rstrip("/").rsplit("/", 1)[-1]
    patient_dir = ensure_patient_dir(patient_id)

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        log(f"ERROR – fetch failed for {patient_id}: {exc}")
        return

    html = resp.text
    digest = sha256(normalize(html))
    prev = load_prev_hash(patient_dir)
    ts = ts_ist()

    if prev is None:
        log(f"{patient_id}: first run → baseline archived.")
        archive_snapshot(patient_dir, ts, html, digest)
        save_prev_hash(patient_dir, digest)
    elif digest != prev:
        log(f"{patient_id}: ⚠️  change detected!")
        archive_snapshot(patient_dir, ts, html, digest)
        save_prev_hash(patient_dir, digest)
        # TODO: notify (email, Slack, SMS, etc.)
    else:
        log(f"{patient_id}: no change.")


def main() -> None:
    log(f"Monitoring {len(PATIENT_URLS)} patient page(s) – Ctrl-C to stop.\n")
    while True:
        for url in PATIENT_URLS:
            check_once(url)
        time.sleep(CHECK_EVERY_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped by user")
