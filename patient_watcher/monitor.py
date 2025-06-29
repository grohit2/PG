#!/usr/bin/env python3
"""
Cross-platform web-page watcher.
Archives HTML *and* SHA-256 digest under:
    patient/<id>/<YYYYMMDD_HHMMSS_TZ>.{html,sha256}

Usage
-----
    python monitor.py                 # uses config.yml & patient list paths in it
    python monitor.py -c other.yml    # point to a different config

Dependencies
------------
    pip install requests beautifulsoup4 pyyaml
Requires Python ≥ 3.9 (zoneinfo).
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import yaml                       # PyYAML
from bs4 import BeautifulSoup


# ──── helpers ─────────────────────────────────────────────────────────
def log(msg: str) -> None:
    """Console logger with local ISO-8601 timestamp."""
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[{ts}] {msg}")


def normalize(html: str) -> str:
    """Strip dynamic noise before hashing."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("form#form1")
    return (main or soup).get_text(strip=True)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def patient_dir(pid: str) -> pathlib.Path:
    d = pathlib.Path("patient") / pid
    d.mkdir(parents=True, exist_ok=True)
    return d


# ──── configuration ───────────────────────────────────────────────────
def load_yaml(path: pathlib.Path) -> dict:
    try:
        with path.open(encoding="utf-8") as fp:
            return yaml.safe_load(fp) or {}
    except FileNotFoundError:
        sys.exit(f"[FATAL] Config file not found: {path}")
    except yaml.YAMLError as exc:
        sys.exit(f"[FATAL] Invalid YAML in {path}: {exc}")


def load_config(path: pathlib.Path) -> tuple[str, list[str], int, ZoneInfo]:
    cfg = load_yaml(path)

    try:
        base_url: str = cfg["base_url"]
    except KeyError:
        sys.exit("[FATAL] `base_url` missing in config.yml")

    check_every = int(cfg.get("check_every_sec", 600))
    tz = ZoneInfo(cfg.get("timezone", "UTC"))

    patients_path = path.with_name(cfg.get("patient_list_file", "patients.txt"))
    patient_ids = read_patient_ids(patients_path)

    if "{id}" not in base_url:
        sys.exit("[FATAL] `base_url` must contain the placeholder {id}")
    if not patient_ids:
        sys.exit("[FATAL] Patient list is empty")

    return base_url, patient_ids, check_every, tz


def read_patient_ids(path: pathlib.Path) -> list[str]:
    if not path.exists():
        sys.exit(f"[FATAL] Patient list file not found: {path}")

    if path.suffix.lower() in {".yml", ".yaml"}:
        data = load_yaml(path)
        return [str(pid) for pid in data.get("patient_ids", [])]
    else:  # plain text, one ID per line
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]


# ──── core routine ────────────────────────────────────────────────────
def monitor(pid: str, url: str, tz: ZoneInfo) -> None:
    root = patient_dir(pid)
    hash_file = root / "last_hash.txt"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        log(f"ERROR – fetch failed for {pid}: {exc}")
        return

    html = resp.text
    digest = sha256(normalize(html))
    prev = hash_file.read_text() if hash_file.exists() else None

    if prev == digest:
        log(f"{pid}: no change.")
        return

    ts = datetime.now(tz).strftime("%Y%m%d_%H%M%S_%Z")
    (root / f"{ts}.html").write_text(html, encoding="utf-8")
    (root / f"{ts}.sha256").write_text(digest)
    hash_file.write_text(digest)

    status = "first run – baseline" if prev is None else "⚠️  change detected"
    log(f"{pid}: {status}.  ↳ snapshot saved as {root / (ts + '.html')}")


# ──── entrypoint ──────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Patient page watcher")
    ap.add_argument(
        "-c", "--config",
        type=pathlib.Path,
        default=pathlib.Path(__file__).with_name("config.yml"),
        help="Path to YAML config (default: ./config.yml)",
    )
    args = ap.parse_args()

    base_url, patient_ids, interval, tz = load_config(args.config)
    urls = {pid: base_url.format(id=pid) for pid in patient_ids}

    log(f"Monitoring {len(urls)} patient(s) every {interval} s – Ctrl-C to stop.\n")

    try:
        while True:
            for pid, url in urls.items():
                monitor(pid, url, tz)
            time.sleep(interval)
    except KeyboardInterrupt:
        log("Stopped by user")


if __name__ == "__main__":
    main()
