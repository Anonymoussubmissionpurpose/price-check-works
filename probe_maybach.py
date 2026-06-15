#!/usr/bin/env python3
"""
Maybach GLS probe — run manually to find how MarketCheck stores the car.
Usage (local):   MARKETCHECK_API_KEY=你的key  python probe_maybach.py
Or in GitHub Actions: temporarily change the workflow's run line to
                      'python probe_maybach.py' and Run once, read the log.
"""
import os, json, time, urllib.parse, urllib.request, urllib.error

KEY = os.environ.get("MARKETCHECK_API_KEY", "").strip()
URL = "https://api.marketcheck.com/v2/search/car/active"
ZIP, RADIUS = "33101", "100"   # Miami — biggest luxury used-car hub

def get(params, label):
    params = {"api_key": KEY, **params}
    full = URL + "?" + urllib.parse.urlencode(params)
    time.sleep(1.2)
    try:
        with urllib.request.urlopen(urllib.request.Request(full, headers={"Accept":"application/json"}), timeout=40) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"   [{label}] HTTP {e.code}: {e.read().decode('utf-8','ignore')[:160]}")
    except Exception as e:
        print(f"   [{label}] error: {e}")
    return None

if not KEY:
    raise SystemExit("❌ 没设置 MARKETCHECK_API_KEY")

print("="*60)
print("  迈巴赫 GLS 探查  (Miami 100mi, 二手, 2025+)")
print("="*60)

# ── 1) 列出 Mercedes-Benz 名下所有含 'GLS' 或 'Maybach' 的车型名 ──
print("\n① Mercedes-Benz 名下、二手2025+、含 GLS/Maybach 的车型名:")
d = get({"car_type":"used","make":"Mercedes-Benz","year":"2025,2026,2027",
         "zip":ZIP,"radius":RADIUS,"rows":"0","facets":"model|0|400|1"}, "facets-model")
if d:
    models = (d.get("facets",{}) or {}).get("model",[]) or []
    hits = [m for m in models if "gls" in str(m.get("item","")).lower() or "maybach" in str(m.get("item","")).lower()]
    for m in (hits or []):
        print(f'     "{m["item"]}"  ({m.get("count")} 台)')
    if not hits:
        print("     （没有含 GLS/Maybach 的车型）")

# ── 2) 直接搜 model='GLS'，看 trim 里有没有 Maybach ──
print("\n② model='GLS' 的车，列出 trim（看是否有 Maybach 字样）:")
d = get({"car_type":"used","make":"Mercedes-Benz","model":"GLS","year":"2025,2026,2027",
         "zip":ZIP,"radius":RADIUS,"rows":"0","facets":"trim|0|100|1"}, "facets-trim")
if d:
    trims = (d.get("facets",{}) or {}).get("trim",[]) or []
    for t in trims[:25]:
        print(f'     "{t["item"]}"  ({t.get("count")} 台)')
    if not trims:
        print("     （无 trim 返回）")

# ── 3) 几种可能的 make/model 组合，各试一次，看哪个真有车 ──
print("\n③ 逐一尝试可能的 make / model 组合（显示命中数 + 最低价示例）:")
combos = [
    ("Mercedes-Benz",   "Maybach GLS 600"),
    ("Mercedes-Benz",   "Maybach GLS"),
    ("Mercedes-Benz",   "Mercedes-Maybach GLS"),
    ("Mercedes-Maybach","GLS 600"),
    ("Mercedes-Maybach","GLS"),
    ("Maybach",         "GLS 600"),
    ("Maybach",         "GLS"),
]
for mk, md in combos:
    d = get({"car_type":"used","make":mk,"model":md,"year":"2025,2026,2027",
             "zip":ZIP,"radius":RADIUS,"sort_by":"price","sort_order":"asc","rows":"3"}, f"{mk}/{md}")
    if d is None:
        continue
    n = d.get("num_found", 0)
    lst = d.get("listings", []) or []
    ex = ""
    if lst:
        p = lst[0].get("price"); b = lst[0].get("build",{}) or {}
        ex = f'  → 最低 ${int(float(p)):,}  ({b.get("year")} {b.get("trim","")})' if p else ""
    flag = "✅" if n else "  "
    print(f'   {flag} make="{mk}"  model="{md}"   命中 {n} 台{ex}')

print("\n" + "="*60)
print("  看 ③ 里哪一行 ✅ 命中 >0，就把那组 make/model 填回 scraper.py")
print("  若全是 0，说明全美暂无 2025+ 二手迈巴赫 GLS（市场现实）")
print("="*60)
