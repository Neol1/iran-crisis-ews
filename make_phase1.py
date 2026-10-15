# Builds phase1.ipynb programmatically (list-of-lines source per Kaggle CLI skill)
import json, os

cells = []

def md(src):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)})

def code(src):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": src.splitlines(keepends=True)})

md("""# 🚨 Iran Crisis Early Warning — Phase 1: Data Ingestion
**هدف:** جمع‌آوری داده از منابع رایگان با فیلتر جغرافیایی ایران (Lat 25-40, Lon 44-63).
هر منبع داخل try/except — خطای یک منبع کل اجرا را متوقف نمی‌کند.
خروجی‌ها در `/kaggle/working/data/` ذخیره می‌شوند.
""")

code("""import os, json, time
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO

pd.set_option("display.max_columns", 50)
DATA_DIR = "/kaggle/working/data"
os.makedirs(DATA_DIR, exist_ok=True)
print("Input mounts:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else [])
""")

md("""## ۱.۱ GDELT — اخبار جهانی (بدون کلید)
محدودیت maxrecords=250 در هر call — برای بازه ۱۴ روز، chunk روزانه می‌زنیم و با rate-limit 0.6s.""")

code("""def fetch_gdelt_iran(days_back=14):
    end_date = datetime.utcnow()
    frames = []
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    for d in range(days_back):
        day_start = end_date - timedelta(days=d + 1)
        day_end = end_date - timedelta(days=d)
        params = {
            "query": '(Iran OR Tehran OR "\\u0627\\u06cc\\u0631\\u0627\\u0646") (crisis OR economy OR protest OR sanction)',
            "mode": "artlist", "maxrecords": 250,
            "startdatetime": day_start.strftime("%Y%m%d%H%M%S"),
            "enddatetime": day_end.strftime("%Y%m%d%H%M%S"),
            "format": "json",
        }
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                arts = r.json().get("articles", [])
                if arts:
                    frames.append(pd.DataFrame(arts))
        except Exception as e:
            print(f"GDELT day -{d+1}: {e}")
        time.sleep(0.6)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["url"])
    print(f"GDELT: {len(df)} unique articles")
    return df

gdelt_df = fetch_gdelt_iran(14)  # فاز ۱: ۱۴ روز برای تست سرعت؛ بعداً افزایش
if not gdelt_df.empty:
    gdelt_df.to_csv(f"{DATA_DIR}/gdelt_articles.csv", index=False)
""")

md("""## ۱.۲ USGS — زلزله‌ها (بدون کلید)، فیلتر مختصات ایران""")

code("""def fetch_usgs_iran(starttime="2020-01-01", min_magnitude=4.0):
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {"format": "geojson", "starttime": starttime,
              "minmagnitude": min_magnitude,
              "minlatitude": 25, "maxlatitude": 40,
              "minlongitude": 44, "maxlongitude": 63}
    try:
        r = requests.get(url, params=params, timeout=60)
        feats = r.json().get("features", [])
        records = []
        for f in feats:
            p, c = f["properties"], f["geometry"]["coordinates"]
            records.append({"time": p.get("time"), "magnitude": p.get("mag"),
                            "place": p.get("place"), "lon": c[0], "lat": c[1], "depth": c[2]})
        df = pd.DataFrame(records)
        print(f"USGS: {len(df)} earthquakes since {starttime}")
        return df
    except Exception as e:
        print(f"USGS error: {e}")
        return pd.DataFrame()

usgs_df = fetch_usgs_iran()
if not usgs_df.empty:
    usgs_df.to_csv(f"{DATA_DIR}/usgs_earthquakes.csv", index=False)
""")

md("""## ۱.۳ Open-Meteo — آب‌وهوای ۶ شهر بزرگ (بدون کلید)
شامل precipitation و max wind — مرتبط با بحران‌های محیطی. شروع از 2022 برای حجم منطقی.""")

code("""CITIES = {"Tehran": (35.6892, 51.3890), "Mashhad": (36.2605, 59.6168),
          "Isfahan": (32.6546, 51.6680), "Shiraz": (29.5918, 52.5837),
          "Tabriz": (38.0800, 46.2919), "Ahvaz": (31.3183, 48.6706)}

def fetch_weather_iran(start="2022-01-01"):
    all_data = []
    for city, (lat, lon) in CITIES.items():
        try:
            params = {"latitude": lat, "longitude": lon,
                      "start_date": start, "end_date": datetime.now().strftime("%Y-%m-%d"),
                      "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                      "timezone": "Asia/Tehran"}
            r = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=60)
            df = pd.DataFrame(r.json()["daily"])
            df["city"] = city
            all_data.append(df)
        except Exception as e:
            print(f"Weather {city}: {e}")
    df = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    print(f"Weather: {len(df)} records / {len(CITIES)} cities")
    return df

weather_df = fetch_weather_iran()
if not weather_df.empty:
    weather_df.to_csv(f"{DATA_DIR}/weather_cities.csv", index=False)
""")

md("""## ۱.۴ World Bank — شاخص‌های کلان اقتصادی ایران""")

code("""def fetch_worldbank_iran():
    indicators = {"NY.GDP.MKTP.CD": "GDP", "FP.CPI.TOTL.ZG": "Inflation",
                  "SL.UEM.TOTL.ZS": "Unemployment",
                  "GC.DOD.TOTL.GD.ZS": "Debt", "BN.CAB.XOKA.CD": "CurrentAccount"}
    all_data = []
    for code, name in indicators.items():
        try:
            url = f"https://api.worldbank.org/v2/country/IRN/indicator/{code}"
            r = requests.get(url, params={"format": "json", "per_page": 100}, timeout=30)
            data = r.json()
            if len(data) > 1 and data[1]:
                all_data += [{"indicator": name, "year": it["date"], "value": it["value"]}
                             for it in data[1] if it["value"] is not None]
        except Exception as e:
            print(f"WB {name}: {e}")
    df = pd.DataFrame(all_data)
    print(f"World Bank: {len(df)} records")
    return df

economy_df = fetch_worldbank_iran()
economy_df.to_csv(f"{DATA_DIR}/worldbank_economy.csv", index=False)
""")

md("""## ۱.۵ NASA FIRMS — نقاط آتش‌سوزی (کلید رایگان از Kaggle Secrets)
اگر کلید موجود نباشد، منبع skip می‌شود و بقیه ادامه می‌یابند.""")

code("""def fetch_firms_iran():
    try:
        from kaggle_secrets import UserSecretsClient
        FIRMS_KEY = UserSecretsClient().get_secret("FIRMS_KEY")
    except Exception:
        print("FIRMS: کلید در Secrets نیست — skip")
        return pd.DataFrame()
    try:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_KEY}/VIIRS_SNPP_NRT/44,25,63,40/7"
        r = requests.get(url, timeout=60)
        df = pd.read_csv(StringIO(r.text))
        print(f"FIRMS: {len(df)} fire points (7 days)")
        return df
    except Exception as e:
        print(f"FIRMS error: {e}")
        return pd.DataFrame()

firms_df = fetch_firms_iran()
if not firms_df.empty:
    firms_df.to_csv(f"{DATA_DIR}/firms_fires.csv", index=False)
""")

md("""## ۱.۶ WHO GHO — شاخص‌های سلامت ایران (بدون کلید)""")

code("""def fetch_who_iran():
    all_data = []
    try:
        r = requests.get("https://ghoapi.azureedge.net/api/Indicator", timeout=30)
        indicators = r.json()["value"]
        relevant = [i for i in indicators if "outbreak" in i["IndicatorName"].lower()][:5]
        for ind in relevant:
            try:
                u = (f"https://ghoapi.azureedge.net/api/{ind['IndicatorCode']}"
                     f"\\u0024filter=SpatialDim eq 'IRN'")
                rr = requests.get(u, timeout=30)
                all_data += rr.json().get("value", [])
            except Exception as e:
                print(f"WHO {ind['IndicatorCode']}: {e}")
    except Exception as e:
        print(f"WHO: {e}")
    df = pd.DataFrame(all_data)
    print(f"WHO: {len(df)} records")
    return df

who_df = fetch_who_iran()
who_df.to_csv(f"{DATA_DIR}/who_health.csv", index=False)
""")

code("""# ===== خلاصه فاز ۱ =====
summary = {"gdelt": len(gdelt_df), "usgs": len(usgs_df), "weather": len(weather_df),
           "worldbank": len(economy_df), "firms": len(firms_df), "who": len(who_df)}
print(json.dumps(summary, indent=2))
with open(f"{DATA_DIR}/phase1_summary.json", "w") as f:
    json.dump(summary, f)
for fname in sorted(os.listdir(DATA_DIR)):
    p = os.path.join(DATA_DIR, fname)
    print(f"{fname:30s} {os.path.getsize(p)//1024} KB")
""")

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python", "version": "3.11"}},
      "nbformat": 4, "nbformat_minor": 4}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase1.ipynb")
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False)
print("written", out)
