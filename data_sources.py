"""Official no-key data feeds for the South Korea international-finance dashboard.

CLI: python data_sources.py --save
The snapshot is written only after all six series have been retrieved and validated.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent / "data"
SNAPSHOT = DATA_DIR / "snapshot.json"
VERIFY = DATA_DIR / "verification.csv"
START_YEAR = 2000
TIMEOUT = 35

SERIES = {
    "fx": dict(title="USD/KRW exchange rate", source="Federal Reserve H.10 via FRED", code="DEXKOUS", frequency="Daily (business days)", units="KRW per USD", kind="fred", group="Market pressure", detail="Higher KRW per USD means a weaker won; New York noon buying rate.", url="https://fred.stlouisfed.org/series/DEXKOUS"),
    "yield10": dict(title="Korea 10-year government bond yield", source="OECD via FRED", code="IRLTLT01KRM156N", frequency="Monthly", units="% per annum", kind="fred", group="Market pressure", detail="OECD monthly benchmark government bond yield; not a daily trading yield.", url="https://fred.stlouisfed.org/series/IRLTLT01KRM156N"),
    "gdp": dict(title="Real GDP growth", source="World Bank WDI", code="NY.GDP.MKTP.KD.ZG", frequency="Annual", units="% year over year", kind="worldbank", group="Domestic fundamentals", detail="Published annual real GDP growth rate; no additional calculation.", url="https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=KR"),
    "cpi": dict(title="Consumer price inflation", source="World Bank WDI", code="FP.CPI.TOTL.ZG", frequency="Annual", units="% year over year", kind="worldbank", group="Domestic fundamentals", detail="Published annual consumer-price inflation rate; no additional calculation.", url="https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=KR"),
    "current_account": dict(title="Current account balance", source="World Bank WDI / IMF balance-of-payments data", code="BN.CAB.XOKA.GD.ZS", frequency="Annual", units="% of GDP", kind="worldbank", group="External buffers", detail="Current account surplus (+) or deficit (−) relative to GDP.", url="https://data.worldbank.org/indicator/BN.CAB.XOKA.GD.ZS?locations=KR"),
    "reserves": dict(title="Foreign exchange reserves (total reserves including gold)", source="World Bank WDI / IMF", code="FI.RES.TOTL.CD", frequency="Annual", units="USD billions", kind="worldbank", group="External buffers", detail="World Bank total reserves INCLUDING gold, converted from current USD to USD billions (÷ 1 billion); not the narrower FX-only definition.", url="https://data.worldbank.org/indicator/FI.RES.TOTL.CD?locations=KR"),
}

HEADERS = {"User-Agent": "SouthKoreaResilienceCourseDashboard/1.0 (public statistical data)"}


def download_fred(session: requests.Session, code: str):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    response = session.get(url, params={"id": code, "cosd": f"{START_YEAR}-01-01"}, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    text = response.text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) < 2:
        raise ValueError(f"Unexpected FRED CSV headers for {code}: {reader.fieldnames}")
    date_field = next((x for x in reader.fieldnames if x.strip().lower() in ("date", "observation_date")), None)
    value_field = next((x for x in reader.fieldnames if x.strip().upper() == code.upper()), None)
    if date_field is None or value_field is None:
        raise ValueError(f"Expected DATE and {code} columns, got {reader.fieldnames}")
    result = []
    for row in reader:
        raw = (row.get(value_field) or "").strip()
        if raw in ("", ".", "NaN"):
            continue
        date = (row.get(date_field) or "").strip()
        datetime.strptime(date, "%Y-%m-%d")
        result.append({"date": date, "value": float(raw)})
    return result


def download_worldbank(session: requests.Session, code: str):
    url = f"https://api.worldbank.org/v2/country/KOR/indicator/{code}"
    response = session.get(url, params={"format": "json", "per_page": 1000, "date": f"{START_YEAR}:{datetime.now(timezone.utc).year}"}, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
        raise ValueError(f"Unexpected World Bank response for {code}: {str(payload)[:180]}")
    if payload[0].get("pages", 1) > 1:
        raise ValueError(f"World Bank unexpectedly paginated {code}; increase per_page")
    rows = []
    for r in payload[1]:
        if r.get("value") is None:
            continue
        if r.get("indicator", {}).get("id") != code or r.get("countryiso3code") != "KOR":
            raise ValueError(f"Unexpected World Bank country/series for {code}")
        year = str(r.get("date", ""))
        if not (year.isdigit() and len(year) == 4):
            raise ValueError(f"Unexpected World Bank year {year!r}")
        rows.append({"date": year, "value": float(r["value"])})
    return rows


def validate_rows(key: str, rows: list[dict]):
    if len(rows) < 5:
        raise ValueError(f"{key}: fewer than 5 real observations")
    dates = [r["date"] for r in rows]
    if dates != sorted(set(dates)):
        raise ValueError(f"{key}: dates not unique and sorted")
    if any(not math.isfinite(r["value"]) for r in rows):
        raise ValueError(f"{key}: invalid numeric value")
    if key in ("fx", "reserves") and any(r["value"] <= 0 for r in rows):
        raise ValueError(f"{key}: non-positive monetary value")
    if key == "yield10" and not all(-10 < r["value"] < 40 for r in rows):
        raise ValueError("Yield out of plausible range; check feed")
    if key in ("fx", "yield10"):
        latest = datetime.strptime(rows[-1]["date"], "%Y-%m-%d").date()
        if (datetime.now(timezone.utc).date() - latest).days > 400:
            raise ValueError(f"{key}: latest daily/monthly observation seems stale ({latest})")
    else:
        if datetime.now(timezone.utc).year - int(rows[-1]["date"]) > 4:
            raise ValueError(f"{key}: World Bank observations seem stale")


def retrieve_all():
    session = requests.Session()
    dataset = {}
    for key, spec in SERIES.items():
        rows = download_fred(session, spec["code"]) if spec["kind"] == "fred" else download_worldbank(session, spec["code"])
        # World Bank response is newest-first; both feeds are normalized oldest-first.
        rows = sorted(rows, key=lambda r: r["date"])
        if key == "reserves":
            for row in rows:
                row["value"] /= 1_000_000_000
        validate_rows(key, rows)
        dataset[key] = {**spec, "observations": rows, "latest_observation_date": rows[-1]["date"], "latest_value": rows[-1]["value"]}
    return {"last_successful_refresh_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "series": dataset}


def _write_atomic(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, path)


def save_snapshot(data: dict):
    """Write valid snapshot and a *blank* independent-source verification worksheet."""
    _write_atomic(SNAPSHOT, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    columns = ["Indicator", "Source", "Code", "Observation date", "Dashboard value (full precision)", "Units", "Original source value (enter independently)", "Match? (yes/no)", "Check date", "Source URL / evidence", "Notes"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for key, s in data["series"].items():
        writer.writerow([s["title"], s["source"], s["code"], s["latest_observation_date"], s["latest_value"], s["units"], "", "", "", s["url"], ""])
    # Generated worksheet is intentionally refreshed each run; save completed checks elsewhere.
    _write_atomic(VERIFY, output.getvalue())


def load_snapshot():
    if not SNAPSHOT.exists():
        return None
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if set(data.get("series", {})) != set(SERIES):
        raise ValueError("Snapshot does not have exactly the six required series")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="Fetch all official series and write validated local snapshot")
    args = parser.parse_args()
    data = retrieve_all()
    if args.save:
        save_snapshot(data)
    print(json.dumps({"result": "SUCCESS", "last_successful_refresh_utc": data["last_successful_refresh_utc"], "latest_observations": {k: s["latest_observation_date"] for k, s in data["series"].items()}}, indent=2))
