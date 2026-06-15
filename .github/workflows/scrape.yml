#!/usr/bin/env python3
"""
Luxury USED Car Price Tracker — MarketCheck API
================================================
Tracks the 5 LOWEST used-car prices (model year 2025+) across the US market.

Set MARKETCHECK_API_KEY (GitHub secret) to use the API.
If a car returns no data, the script auto-prints MarketCheck's real model
names for that make so the exact string can be filled in below.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ─── Car configuration ────────────────────────────────────────────────────────
# `make` / `model` must match MarketCheck's taxonomy. `hint` is only used for the
# auto-diagnostic (lists matching model names when a car returns nothing).
CARS = [
    {"id": "porsche_cayenne",      "name": "Porsche Cayenne",          "name_zh": "保时捷 卡宴",       "make": "Porsche",       "model": "Cayenne",          "hint": "Cayenne"},
    {"id": "aston_martin_dbx",     "name": "Aston Martin DBX",         "name_zh": "阿斯顿马丁 DBX",    "make": "Aston Martin",  "model": "DBX",              "hint": "DBX"},
    {"id": "aston_martin_vantage", "name": "Aston Martin Vantage",     "name_zh": "阿斯顿马丁 Vantage","make": "Aston Martin",  "model": "Vantage",          "hint": "Vantage"},
    {"id": "lamborghini_urus",     "name": "Lamborghini Urus",         "name_zh": "兰博基尼 Urus",     "make": "Lamborghini",   "model": "Urus",             "hint": "Urus"},
    {"id": "mercedes_gls_maybach", "name": "Mercedes-Benz GLS Maybach","name_zh": "奔驰 GLS 迈巴赫",   "make": "Mercedes-Benz", "model": "GLS", "trim": "Maybach", "hint": "GLS"},
    {"id": "mercedes_amg_gls63",   "name": "Mercedes-Benz AMG GLS 63", "name_zh": "奔驰 AMG GLS 63",  "make": "Mercedes-Benz", "model": "GLS", "trim": "AMG GLS 63", "hint": "GLS"},
    {"id": "mercedes_amg_gt",      "name": "Mercedes-Benz AMG GT",     "name_zh": "奔驰 AMG GT",      "make": "Mercedes-Benz", "model": "AMG GT Coupe",     "hint": "GT"},
    {"id": "mercedes_sl",          "name": "Mercedes-Benz SL-Class",   "name_zh": "奔驰 SL",          "make": "Mercedes-Benz", "model": "SL",               "hint": "SL"},
    {"id": "mercedes_g",           "name": "Mercedes-Benz G-Class",    "name_zh": "奔驰 G级",         "make": "Mercedes-Benz", "model": "G-Class",          "hint": "G"},
    {"id": "range_rover",          "name": "Land Rover Range Rover",   "name_zh": "路虎 揽胜",        "make": "Land Rover",    "model": "Range Rover",      "hint": "Range"},
    {"id": "bentley_bentayga",     "name": "Bentley Bentayga",         "name_zh": "宾利 添越",        "make": "Bentley",       "model": "Bentayga",         "hint": "Bentayga"},
    {"id": "ferrari_roma",         "name": "Ferrari Roma",             "name_zh": "法拉利 罗马",      "make": "Ferrari",       "model": "Roma",             "hint": "Roma"},
]

YEARS = "2025,2026,2027"
API_KEY = os.environ.get("MARKETCHECK_API_KEY", "").strip()
MARKETCHECK_URL = "https://api.marketcheck.com/v2/search/car/active"

# Top US metros to cover the whole country (free tier caps each search at ~100mi,
# so we query several cities and merge). Edit this list freely.
CITIES = [
    ("New York, NY",     "10001"),
    ("Los Angeles, CA",  "90012"),
    ("Chicago, IL",      "60601"),
    ("Houston, TX",      "77002"),
    ("Phoenix, AZ",      "85004"),
    ("Philadelphia, PA", "19103"),
    ("San Antonio, TX",  "78205"),
    ("San Diego, CA",    "92101"),
    ("Dallas, TX",       "75201"),
    ("San Jose, CA",     "95113"),
    ("Atlanta, GA",      "30303"),
    ("Miami, FL",        "33101"),
    ("Seattle, WA",      "98101"),
    ("Las Vegas, NV",    "89101"),
    ("Denver, CO",       "80202"),
]
RADIUS = "100"          # free-tier maximum, in miles
ROWS_PER_CITY = "20"    # cheapest-N pulled from each city before merging

# Delay between API calls to stay under the free tier's 5 req/sec limit (avoids 429)
API_DELAY = 2.5


def _api_get(params: dict):
    """GET MarketCheck and return parsed JSON, or None on error."""
    url = MARKETCHECK_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    time.sleep(API_DELAY)
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:200]
        print(f"     ⚠ API HTTP {e.code}: {body}")
    except Exception as e:
        print(f"     ⚠ API error: {e}")
    return None


def fetch_marketcheck(car: dict) -> list[dict]:
    """Query the cheapest used 2025+ listings across all CITIES, merge them,
    dedupe by VIN, and return the 5 lowest-priced nationwide.
    For a car with alt_makes, the correct make is resolved on the first city
    that returns data, then reused for the rest."""
    makes = [car["make"]] + car.get("alt_makes", [])
    chosen_make = None
    pool: dict = {}          # vin/key -> cheapest listing seen

    for cname, zipc in CITIES:
        candidates = [chosen_make] if chosen_make else makes
        for mk in candidates:
            params = {
                "api_key":    API_KEY,
                "car_type":   "used",
                "make":       mk,
                "model":      car["model"],
                "year":       YEARS,
                "zip":        zipc,
                "radius":     RADIUS,
                "sort_by":    "price",
                "sort_order": "asc",
                "rows":       ROWS_PER_CITY,
                "start":      "0",
            }
            if car.get("trim"):           # e.g. Maybach is a trim of model "GLS"
                params["trim"] = car["trim"]
            data = _api_get(params)
            parsed = _parse_listings(data)
            if parsed:
                chosen_make = mk
                for l in parsed:
                    key = l.get("vin") or f'{l["price"]}-{l.get("miles")}'
                    if key not in pool or l["price"] < pool[key]["price"]:
                        pool[key] = l
                break        # got data for this city; next city

    return sorted(pool.values(), key=lambda x: x["price"])[:5]


def _parse_listings(data) -> list[dict]:
    if not data:
        return []
    out, seen = [], set()
    for lst in data.get("listings", []) or []:
        try:
            price = int(float(lst.get("price")))
        except (TypeError, ValueError):
            continue
        if not (10_000 < price < 5_000_000):
            continue
        vin = lst.get("vin") or lst.get("id") or f"{price}"
        if vin in seen:
            continue
        seen.add(vin)
        build = lst.get("build", {}) or {}
        dealer = lst.get("dealer", {}) or {}
        out.append({
            "price": price,
            "vin":   lst.get("vin"),
            "year":  build.get("year"),
            "trim":  build.get("trim") or build.get("version"),
            "miles": lst.get("miles"),
            "city":  dealer.get("city"),
            "state": dealer.get("state"),
            "url":   lst.get("vdp_url"),
        })
        if len(out) >= 5:
            break
    return out


def suggest_models(car: dict):
    """When a car returns nothing, list MarketCheck's real model names for that
    make (used, 2025+) that contain the hint keyword — so we can fix the config."""
    hint = car["hint"].lower()
    for mk in [car["make"]] + car.get("alt_makes", []):
        data = _api_get({
            "api_key":  API_KEY,
            "car_type": "used",
            "make":     mk,
            "year":     YEARS,
            "country":  "US",
            "rows":     "0",
            "facets":   "model|0|300|1",
        })
        if not data:
            continue
        facets = (data.get("facets", {}) or {}).get("model", []) or []
        if not facets:
            continue
        matches = [f for f in facets if hint in str(f.get("item", "")).lower()]
        if matches:
            names = ", ".join(f'"{f["item"]}" ({f.get("count","?")})' for f in matches[:12])
            print(f"        ↳ make='{mk}' 中含 '{car['hint']}' 的车型名: {names}")
            return
        sample = ", ".join(f'"{f["item"]}"' for f in facets[:12])
        print(f"        ↳ make='{mk}' 部分车型: {sample}")
        return


def record_result(results, existing, car, listings, utc_now):
    cid = car["id"]
    if listings:
        prices = [l["price"] for l in listings]
        print(f"     ✅  {[f'${p:,}' for p in prices]}")
        results[cid] = {
            "name": car["name"], "name_zh": car["name_zh"],
            "listings": listings, "prices": prices,
            "last_success": utc_now.isoformat(), "stale": False,
        }
    elif cid in existing and existing[cid].get("prices"):
        print("     📌  Using cached data")
        results[cid] = {**existing[cid], "stale": True}
    else:
        print("     ❌  No 2025+ used listings found")
        if API_KEY:
            suggest_models(car)   # auto-diagnostic: print real model names
        results[cid] = {
            "name": car["name"], "name_zh": car["name_zh"],
            "listings": [], "prices": [],
            "last_success": None, "stale": False,
        }


def main():
    utc_now = datetime.now(timezone.utc)
    print("=" * 64)
    print("  🚗  Luxury USED-Car Price Tracker  (model year 2025+)")
    print(f"  ⏰  {utc_now.strftime('%Y-%m-%d  %H:%M:%S  UTC')}")
    print(f"  🔌  Source: {'MarketCheck API' if API_KEY else 'no API key'}")
    print("=" * 64)

    if not API_KEY:
        print("❌  No MARKETCHECK_API_KEY set. Add it as a GitHub secret.")
        sys.exit(1)

    data_path = "data/prices.json"
    existing = {}
    try:
        with open(data_path, encoding="utf-8") as f:
            existing = json.load(f).get("cars", {})
        print("📂  Loaded existing data\n")
    except Exception:
        print("📂  Starting fresh\n")

    results = {}
    for car in CARS:
        print(f"🔍  {car['name']}  ({car['name_zh']})")
        listings = fetch_marketcheck(car)
        record_result(results, existing, car, listings, utc_now)

    # ── Persist ────────────────────────────────────────────────────────────────
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/history", exist_ok=True)
    payload = {
        "updated_at": utc_now.isoformat(),
        "market": "used",
        "year_min": 2025,
        "source": f"MarketCheck · {len(CITIES)} US metros merged",
        "cars": results,
    }
    # 1) latest snapshot — what the website reads
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 2) full timestamped snapshot — one file per run, for historical analysis
    stamp = utc_now.strftime("%Y-%m-%dT%H%M")
    snap_path = f"data/history/{stamp}.json"
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 3) compact long-term index — one tiny row per run (date + 5 prices per car).
    #    Easy to load for trend charts without opening every snapshot.
    index_path = "data/history/index.json"
    try:
        with open(index_path, encoding="utf-8") as f:
            hist = json.load(f)
    except Exception:
        hist = {"runs": []}
    hist["runs"].append({
        "date": utc_now.isoformat(),
        "prices": {cid: d.get("prices", []) for cid, d in results.items()},
    })
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    print(f"  🗂  Snapshot → {snap_path}  |  history index has {len(hist['runs'])} run(s)")


    # ── Summary ────────────────────────────────────────────────────────────────
    ok    = sum(1 for c in results.values() if c.get("prices") and not c.get("stale"))
    stale = sum(1 for c in results.values() if c.get("stale"))
    fail  = len(CARS) - ok - stale
    print(f"\n{'='*64}")
    print(f"  📊  {ok} updated  |  {stale} cached  |  {fail} no-data")
    for cid, d in results.items():
        icon = "✅" if (d.get("prices") and not d.get("stale")) else ("📌" if d.get("stale") else "❌")
        pp = "  ".join(f"${p:,}" for p in d.get("prices", []))
        print(f"  {icon}  {d['name']:<32} {pp or '—'}")
    print(f"\n  💾  Saved → {data_path}")
    print("=" * 64)


if __name__ == "__main__":
    main()
