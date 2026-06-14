#!/usr/bin/env python3
"""
Luxury USED Car Price Tracker — Scraper
========================================
Tracks the 5 LOWEST used-car prices (model year 2025+) across the US market
for 11 luxury models.

Data source priority:
  1. MarketCheck API  (RECOMMENDED — reliable from CI, aggregates 53,000+ US
     dealers / 6.2M used listings). Set the MARKETCHECK_API_KEY env var /
     GitHub secret to enable it.
  2. Best-effort Playwright scrape of Cars.com used listings — used ONLY when
     no API key is set. NOTE: Cars.com / CarGurus run enterprise anti-bot
     (DataDome / Cloudflare) that frequently block datacenter IPs such as
     GitHub Actions runners, so this path is unreliable by design. The API
     path is strongly recommended.

Output: data/prices.json
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

import urllib.request
import urllib.parse
import urllib.error

# ─── Car configuration ────────────────────────────────────────────────────────
# `make` / `model` use the strings MarketCheck expects. If a model returns no
# data, adjust the `model` string here (taxonomy occasionally differs, e.g.
# "Maybach GLS" vs "Maybach GLS 600").
CARS = [
    {"id": "porsche_cayenne",      "name": "Porsche Cayenne",          "name_zh": "保时捷 卡宴",      "make": "Porsche",       "model": "Cayenne",      "cars_slug": "porsche-cayenne"},
    {"id": "aston_martin_dbx",     "name": "Aston Martin DBX",         "name_zh": "阿斯顿马丁 DBX",   "make": "Aston Martin",  "model": "DBX",          "cars_slug": "aston_martin-dbx"},
    {"id": "aston_martin_vantage", "name": "Aston Martin Vantage",     "name_zh": "阿斯顿马丁 Vantage","make": "Aston Martin", "model": "Vantage",      "cars_slug": "aston_martin-vantage"},
    {"id": "lamborghini_urus",     "name": "Lamborghini Urus",         "name_zh": "兰博基尼 Urus",    "make": "Lamborghini",   "model": "Urus",         "cars_slug": "lamborghini-urus"},
    {"id": "mercedes_gls_maybach", "name": "Mercedes-Benz GLS Maybach","name_zh": "奔驰 GLS 迈巴赫",  "make": "Mercedes-Benz", "model": "Maybach GLS",  "cars_slug": "mercedes_benz-maybach_gls"},
    {"id": "mercedes_amg_gt",      "name": "Mercedes-Benz AMG GT",     "name_zh": "奔驰 AMG GT",     "make": "Mercedes-Benz", "model": "AMG GT",       "cars_slug": "mercedes_benz-amg_gt"},
    {"id": "mercedes_sl",          "name": "Mercedes-Benz SL-Class",   "name_zh": "奔驰 SL",         "make": "Mercedes-Benz", "model": "SL-Class",     "cars_slug": "mercedes_benz-sl_class"},
    {"id": "mercedes_g",           "name": "Mercedes-Benz G-Class",    "name_zh": "奔驰 G级",        "make": "Mercedes-Benz", "model": "G-Class",      "cars_slug": "mercedes_benz-g_class"},
    {"id": "range_rover",          "name": "Land Rover Range Rover",   "name_zh": "路虎 揽胜",       "make": "Land Rover",    "model": "Range Rover",  "cars_slug": "land_rover-range_rover"},
    {"id": "bentley_bentayga",     "name": "Bentley Bentayga",         "name_zh": "宾利 添越",       "make": "Bentley",       "model": "Bentayga",     "cars_slug": "bentley-bentayga"},
    {"id": "ferrari_roma",         "name": "Ferrari Roma",             "name_zh": "法拉利 罗马",     "make": "Ferrari",       "model": "Roma",         "cars_slug": "ferrari-roma"},
]

# Model years considered (2025 and newer)
YEARS = "2025,2026,2027"
API_KEY = os.environ.get("MARKETCHECK_API_KEY", "").strip()
MARKETCHECK_URL = "https://api.marketcheck.com/v2/search/car/active"


# ─── MarketCheck API path (recommended) ───────────────────────────────────────
def fetch_marketcheck(car: dict) -> list[dict]:
    """Return up to 5 cheapest used listings (2025+) for one car via the API."""
    params = {
        "api_key":    API_KEY,
        "car_type":   "used",          # USED market only
        "make":       car["make"],
        "model":      car["model"],
        "year":       YEARS,           # 2025+
        "country":    "US",            # US-wide
        "sort_by":    "price",
        "sort_order": "asc",           # cheapest first
        "rows":       "30",
        "start":      "0",
    }
    url = MARKETCHECK_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:200]
        print(f"     ⚠ API HTTP {e.code}: {body}")
        return []
    except Exception as e:
        print(f"     ⚠ API error: {e}")
        return []

    listings = data.get("listings", []) or []
    out, seen = [], set()
    for lst in listings:
        price = lst.get("price")
        try:
            price = int(float(price))
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


# ─── Playwright fallback (best-effort, frequently blocked from CI) ─────────────
async def scrape_cars_com(page, car: dict) -> list[dict]:
    """Best-effort scrape of Cars.com used listings. May be blocked."""
    q = urllib.parse.urlencode({
        "stock_type": "used",
        "year_min":   "2025",
        "sort":       "list_price_asc",
        "maximum_distance": "all",
        "zip":        "10001",
        "page_size":  "20",
    })
    # makes[]/models[] need bracket params appended raw
    url = (f"https://www.cars.com/shopping/results/?{q}"
           f"&makes[]={car['cars_slug'].split('-')[0]}"
           f"&models[]={car['cars_slug']}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await asyncio.sleep(2)
        prices = []
        for sel in [".primary-price", "[class*='PrimaryPrice']", "spark-badge"]:
            els = await page.query_selector_all(sel)
            for el in els[:20]:
                try:
                    txt = await el.inner_text()
                    digits = re.sub(r"[^\d]", "", txt)
                    if digits and 5 <= len(digits) <= 7:
                        p = int(digits)
                        if 10_000 < p < 5_000_000:
                            prices.append(p)
                except Exception:
                    pass
            if prices:
                break
        prices = sorted(set(prices))[:5]
        return [{"price": p, "year": None, "trim": None, "miles": None,
                 "city": None, "state": None, "url": None} for p in prices]
    except Exception as e:
        print(f"     ⚠ Scrape error: {e}")
        return []


async def run_scrape_fallback(results, existing, utc_now):
    from playwright.async_api import async_playwright
    print("⚠  No MARKETCHECK_API_KEY set — using best-effort Cars.com scrape.")
    print("   (Datacenter IPs are often blocked; set the API key for reliability.)\n")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
            viewport={"width": 1920, "height": 1080}, locale="en-US",
        )
        page = await ctx.new_page()
        for car in CARS:
            print(f"🔍  {car['name']}  ({car['name_zh']})")
            listings = await scrape_cars_com(page, car)
            record_result(results, existing, car, listings, utc_now)
            await asyncio.sleep(3)
        await browser.close()


# ─── Shared result recording ──────────────────────────────────────────────────
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
        results[cid] = {
            "name": car["name"], "name_zh": car["name_zh"],
            "listings": [], "prices": [],
            "last_success": None, "stale": False,
        }


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    utc_now = datetime.now(timezone.utc)
    print("=" * 64)
    print("  🚗  Luxury USED-Car Price Tracker  (model year 2025+)")
    print(f"  ⏰  {utc_now.strftime('%Y-%m-%d  %H:%M:%S  UTC')}")
    print(f"  🔌  Source: {'MarketCheck API' if API_KEY else 'Cars.com scrape (fallback)'}")
    print("=" * 64)

    data_path = "data/prices.json"
    existing = {}
    try:
        with open(data_path, encoding="utf-8") as f:
            existing = json.load(f).get("cars", {})
        print("📂  Loaded existing data\n")
    except Exception:
        print("📂  Starting fresh\n")

    results = {}

    if API_KEY:
        for car in CARS:
            print(f"🔍  {car['name']}  ({car['name_zh']})")
            listings = fetch_marketcheck(car)
            record_result(results, existing, car, listings, utc_now)
    else:
        try:
            asyncio.run(run_scrape_fallback(results, existing, utc_now))
        except ImportError:
            print("❌  Playwright not installed and no API key set. Nothing to do.")
            sys.exit(1)

    # ── Persist ────────────────────────────────────────────────────────────────
    os.makedirs("data", exist_ok=True)
    payload = {
        "updated_at": utc_now.isoformat(),
        "market": "used",
        "year_min": 2025,
        "source": "MarketCheck (53k+ US dealers)" if API_KEY else "Cars.com (best-effort scrape)",
        "cars": results,
    }
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

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
