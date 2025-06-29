#!/usr/bin/env python3
"""
lab_report_to_json.py

Usage examples
--------------
# Read directly from the public URL and just print JSON:
python lab_report_to_json.py \
    http://115.241.194.20/LIS/Reports/Patient_Report.aspx/20250335112

# Read from the same URL and write to a file:
python lab_report_to_json.py \
    http://115.241.194.20/LIS/Reports/Patient_Report.aspx/20250335112 \
    -o report_20250335112.json

# Parse a local HTML file:
python lab_report_to_json.py lab.html -o report.json
"""

import argparse
import json
from pathlib import Path
from typing import Union

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def load_html(src: Union[str, Path]) -> str:
    """Return raw HTML from a URL or a local file path."""
    src = str(src)
    if src.startswith(("http://", "https://")):
        r = requests.get(src, timeout=30)
        r.raise_for_status()
        return r.text
    return Path(src).read_text(encoding="utf-8")


def parse_lab_report(html: str):
    """
    Parse a KGH / LIS “Patient_Report.aspx” document.

    Returns
    -------
    patient_df : pandas.DataFrame (1 row)
    results_df : pandas.DataFrame (one row per individual parameter)
    """
    soup = BeautifulSoup(html, "html.parser")

    # ───── personal details ─────
    def _txt(css_id):
        tag = soup.select_one(css_id)
        return tag.get_text(strip=True) if tag else None

    patient = {
        "registration_no": _txt("#lblRegno"),
        "patient_name": _txt("#lblName"),
        "age": _txt("#lblAge"),
        "sex": _txt("#lblSex"),
    }
    patient_df = pd.DataFrame([patient])

    # ───── main grid ─────
    results = []
    # skip the header row (index 0)
    for row in soup.select("#GView > tbody > tr")[1:]:
        tds = row.find_all("td", recursive=False)
        if len(tds) < 4:         # safety check
            continue

        bill_no   = tds[0].get_text(strip=True)
        bill_date = tds[1].get_text(strip=True)
        test_name = tds[2].get_text(strip=True)

        # each expandable row owns *one* sibling <div id="GView_PnlChild_*">
        child_panel = row.find("div", id=lambda x: x and x.startswith("GView_PnlChild"))
        detail_tbl  = child_panel and child_panel.find("table")

        if detail_tbl:
            for drow in detail_tbl.select("tbody > tr")[1:]:  # skip header
                cells = [c.get_text(strip=True) for c in drow.find_all("td")]
                if not cells or "No Tests found" in cells[0]:
                    continue

                slno, param, value, units, ref_range = cells
                results.append(
                    {
                        "bill_no": bill_no,
                        "bill_date": bill_date,
                        "test_name": test_name,
                        "slno": slno,
                        "parameter": param,
                        "result": value,
                        "units": units,
                        "reference_range": ref_range,
                    }
                )
        else:
            # fallback when there is no nested table (e.g. Blood-group report)
            results.append(
                {
                    "bill_no": bill_no,
                    "bill_date": bill_date,
                    "test_name": test_name,
                    "slno": None,
                    "parameter": "—",
                    "result": "No detailed table",
                    "units": "",
                    "reference_range": "",
                }
            )

    results_df = pd.DataFrame(results)
    return patient_df, results_df


def build_json(patient_df, results_df) -> dict:
    """Convert DataFrames → nested dict ready for json.dumps."""
    return {
        "patient": patient_df.iloc[0].to_dict(),
        "results": results_df.to_dict(orient="records"),
    }


# ────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Turn a KGH LIS Patient_Report.aspx page into JSON."
    )
    parser.add_argument(
        "source",
        help="URL or path to local HTML file (e.g. lab.html)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write JSON to this file instead of stdout",
    )
    args = parser.parse_args()

    html = load_html(args.source)
    patient_df, results_df = parse_lab_report(html)
    report_json = build_json(patient_df, results_df)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(report_json, indent=2, ensure_ascii=False))
        print(f"✓ JSON saved to {out_path.resolve()}")
    else:
        print(json.dumps(report_json, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
