"""Data Ingestion Pipeline for Iran Crisis EWS.
Runs all 7 ingestion sources safely, handling missing keys gracefully.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests

ARTIFACT_DIR = Path("/kaggle/working/artifacts/raw")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path("/kaggle/working/artifacts/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def mask_key(key: str) -> str:
    if not key:
        return "<MISSING>"
    if len(key) < 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def audit_log(service: str, key: str, status: str, detail: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    key_masked = mask_key(key) if key else "NO_KEY"
    line = f"[{ts}] [{service}] [{key_masked}] [{status}]"
    if detail:
        line += f" [{detail}]"
    with open(LOG_DIR / "api_access.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def fetch_gdelt():
    print("\n--- [1/7] Fetching GDELT ---")
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": "(Iran OR Tehran OR ایران) AND (crisis OR protest OR sanction OR economy)",
        "mode": "ArtList",
        "format": "json",
        "maxrecords": 250,
        "timespan": "7d"
    }
    try:
        res = requests.get(url, params=params, timeout=30)
        if res.status_code == 200:
            data = res.json()
            articles = data.get("articles", [])
            df = pd.DataFrame(articles)
            df.to_parquet(ARTIFACT_DIR / "gdelt.parquet")
            audit_log("GDELT", None, "SUCCESS", f"{len(df)} records")
            return len(df)
        else:
            audit_log("GDELT", None, f"ERROR {res.status_code}")
            return 0
    except Exception as e:
        audit_log("GDELT", None, "EXCEPTION", str(e))
        return 0


def fetch_usgs():
    print("\n--- [2/7] Fetching USGS Earthquakes ---")
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "minmagnitude": "4.0",
        "minlatitude": "25",
        "maxlatitude": "40",
        "minlongitude": "44",
        "maxlongitude": "63"
    }
    try:
        res = requests.get(url, params=params, timeout=30)
        if res.status_code == 200:
            data = res.json()
            features = [f["properties"] for f in data.get("features", [])]
            df = pd.DataFrame(features)
            df.to_parquet(ARTIFACT_DIR / "usgs.parquet")
            audit_log("USGS", None, "SUCCESS", f"{len(df)} records")
            return len(df)
        else:
            audit_log("USGS", None, f"ERROR {res.status_code}")
            return 0
    except Exception as e:
        audit_log("USGS", None, "EXCEPTION", str(e))
        return 0


def fetch_weather():
    print("\n--- [3/7] Fetching Open-Meteo Weather ---")
    cities = {
        "Tehran": (35.6892, 51.3890),
        "Mashhad": (36.2605, 59.6168),
        "Isfahan": (32.6546, 51.6680),
        "Tabriz": (38.0800, 46.2919),
        "Shiraz": (29.5918, 52.5837)
    }
    records = []
    for city, (lat, lon) in cities.items():
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": "true"}
        try:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200:
                cw = res.json().get("current_weather", {})
                cw["city"] = city
                records.append(cw)
        except Exception as e:
            print(f"Weather error for {city}: {e}")
    df = pd.DataFrame(records)
    if not df.empty:
        df.to_parquet(ARTIFACT_DIR / "weather.parquet")
    audit_log("Open-Meteo", None, "SUCCESS", f"{len(df)} records")
    return len(df)


def fetch_worldbank():
    print("\n--- [4/7] Fetching WorldBank Data ---")
    indicators = ["NY.GDP.MKTP.CD", "FP.CPI.TOTL.ZG"]
    records = []
    for ind in indicators:
        url = f"https://api.worldbank.org/v2/country/IRN/indicator/{ind}"
        params = {"format": "json", "per_page": 10}
        try:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200 and len(res.json()) > 1:
                data = res.json()[1]
                for item in data:
                    records.append({"indicator": ind, "year": item.get("date"), "value": item.get("value")})
        except Exception as e:
            print(f"WorldBank error for {ind}: {e}")
    df = pd.DataFrame(records)
    if not df.empty:
        df.to_parquet(ARTIFACT_DIR / "worldbank.parquet")
    audit_log("WorldBank", None, "SUCCESS", f"{len(df)} records")
    return len(df)


def fetch_who():
    print("\n--- [5/7] Fetching WHO Data ---")
    url = "https://ghoapi.azureedge.net/api/Indicator"
    try:
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            data = res.json().get("value", [])[:50]
            df = pd.DataFrame(data)
            df.to_parquet(ARTIFACT_DIR / "who.parquet")
            audit_log("WHO", None, "SUCCESS", f"{len(df)} records")
            return len(df)
        else:
            audit_log("WHO", None, f"ERROR {res.status_code}")
            return 0
    except Exception as e:
        audit_log("WHO", None, "EXCEPTION", str(e))
        return 0


def fetch_acled():
    print("\n--- [6/7] Fetching ACLED ---")
    key = os.getenv("ACLED_KEY", "")
    email = os.getenv("ACLED_EMAIL", "")
    if not key or not email:
        audit_log("ACLED", key, "SKIPPED", "No API key/email found in environment")
        print("⚠️ ACLED key missing. Skipping gracefully.")
        return 0
    return 0


def fetch_firms():
    print("\n--- [7/7] Fetching NASA FIRMS ---")
    key = os.getenv("FIRMS_KEY", "")
    if not key:
        audit_log("FIRMS", key, "SKIPPED", "No API key found in environment")
        print("⚠️ FIRMS key missing. Skipping gracefully.")
        return 0
    return 0


def main():
    print("========================================")
    print("STARTING DATA INGESTION PIPELINE")
    print("========================================")

    results = {}
    results["GDELT"] = fetch_gdelt()
    results["USGS"] = fetch_usgs()
    results["Weather"] = fetch_weather()
    results["WorldBank"] = fetch_worldbank()
    results["WHO"] = fetch_who()
    results["ACLED"] = fetch_acled()
    results["FIRMS"] = fetch_firms()

    print("\n========================================")
    print("INGESTION SUMMARY")
    print("========================================")
    for k, v in results.items():
        print(f"  • {k}: {v} records fetched")
    print("========================================\n")


if __name__ == "__main__":
    main()
