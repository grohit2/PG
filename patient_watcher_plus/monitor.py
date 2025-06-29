#!/usr/bin/env python3
"""Patient watcher with WhatsApp notifications.

Archives HTML & SHA‑256 digest under:
    patient/<id>/<YYYYMMDD_HHMMSS_TZ>.{html,sha256}

On each new snapshot it optionally sends a WhatsApp message via
a separate Node.js script defined in the YAML config.

Run
----
    python monitor.py                 # uses config.yml
    python monitor.py -c other.yml
"""
from __future__ import annotations

import argparse, hashlib, pathlib, sys, time, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import requests, yaml
from bs4 import BeautifulSoup

def log(msg: str) -> None:
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[{ts}] {msg}")

def normalize(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("form#form1")
    return (main or soup).get_text(strip=True)

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def patient_dir(pid: str) -> pathlib.Path:
    d = pathlib.Path("patient") / pid
    d.mkdir(parents=True, exist_ok=True)
    return d

def load_yaml(path: pathlib.Path) -> dict:
    try:
        with path.open(encoding="utf-8") as fp:
            return yaml.safe_load(fp) or {}
    except FileNotFoundError:
        sys.exit(f"[FATAL] Config file not found: {path}")
    except yaml.YAMLError as exc:
        sys.exit(f"[FATAL] Invalid YAML in {path}: {exc}")

def read_patient_ids(path: pathlib.Path) -> list[str]:
    if not path.exists():
        sys.exit(f"[FATAL] Patient list file not found: {path}")
    if path.suffix.lower() in {'.yml', '.yaml'}:
        data = load_yaml(path)
        return [str(pid) for pid in data.get('patient_ids', [])]
    return [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]

def load_config(path: pathlib.Path):
    cfg = load_yaml(path)
    if '{id}' not in cfg.get('base_url', ''):
        sys.exit('[FATAL] base_url missing or lacks {id} placeholder')

    patient_file = path.with_name(cfg.get('patient_list_file', 'patients.txt'))
    patient_ids = read_patient_ids(patient_file)
    if not patient_ids:
        sys.exit('[FATAL] Patient list is empty')

    whatsapp = cfg.get('whatsapp', {})
    return {
        'base_url': cfg['base_url'],
        'patient_ids': patient_ids,
        'interval': int(cfg.get('check_every_sec', 600)),
        'tz': ZoneInfo(cfg.get('timezone', 'UTC')),
        'whatsapp': {
            'enabled': bool(whatsapp.get('enabled', False)),
            'recipient': whatsapp.get('recipient'),
            'template': whatsapp.get('template', 'Update detected for patient {id} at {time}'),
            'script': whatsapp.get('script', 'notifier/send_whatsapp.js')
        }
    }

def send_whatsapp(cfg: dict, pid: str, ts: str):
    if not cfg['whatsapp']['enabled']:
        return
    recipient = cfg['whatsapp']['recipient']
    script = cfg['whatsapp']['script']
    template = cfg['whatsapp']['template']
    if not recipient:
        log('[WARN] WhatsApp recipient not configured; skipping notification.')
        return
    msg = template.format(id=pid, time=ts)
    try:
        subprocess.Popen(['node', script, recipient, msg],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        log(f'{pid}: WhatsApp notify triggered.')
    except FileNotFoundError:
        log('[ERROR] Node or script not found; cannot send WhatsApp message.')

def monitor(pid: str, url: str, tz: ZoneInfo, cfg: dict):
    root = patient_dir(pid)
    hash_file = root / 'last_hash.txt'

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        log(f'ERROR – fetch failed for {pid}: {exc}')
        return

    html = resp.text
    digest = sha256(normalize(html))
    prev = hash_file.read_text() if hash_file.exists() else None

    if prev == digest:
        log(f'{pid}: no change.')
        return

    ts = datetime.now(tz).strftime('%Y%m%d_%H%M%S_%Z')
    (root / f'{ts}.html').write_text(html, encoding='utf-8')
    (root / f'{ts}.sha256').write_text(digest)
    hash_file.write_text(digest)

    status = 'first run – baseline' if prev is None else '⚠️  change detected'
    log(f'{pid}: {status}. ↳ snapshot saved as {root / (ts + ".html")}')
    send_whatsapp(cfg, pid, ts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config', type=pathlib.Path,
                    default=pathlib.Path(__file__).with_name('config.yml'))
    args = ap.parse_args()

    cfg = load_config(args.config)
    urls = {pid: cfg['base_url'].format(id=pid) for pid in cfg['patient_ids']}

    log(f'Monitoring {len(urls)} patient(s) every {cfg["interval"]} s – Ctrl‑C to stop.\n')
    try:
        while True:
            for pid, url in urls.items():
                monitor(pid, url, cfg['tz'], cfg)
            time.sleep(cfg['interval'])
    except KeyboardInterrupt:
        log('Stopped by user')

if __name__ == '__main__':
    main()
