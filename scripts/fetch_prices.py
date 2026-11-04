"""Fetch latest prices for the desk clock and write prices.json."""
import json
import datetime
import urllib.parse
import urllib.request

INDEX = {"VIX": "^VIX", "SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI", "TA35": "TA35.TA"}

with open("tickers.json") as f:
    tickers = json.load(f)

quotes = {}
for sym in tickers:
    y = INDEX.get(sym, sym)
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(y) + "?interval=1d&range=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            meta = json.load(r)["chart"]["result"][0]["meta"]
        price = meta["regularMarketPrice"]
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        quotes[sym] = {
            "price": price,
            "chg": price - prev,
            "pct": (price - prev) / prev * 100 if prev else 0,
        }
    except Exception as e:  # keep going if one symbol fails
        print(f"{sym}: {e}")

if quotes:
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "quotes": quotes}
    with open("prices.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"Saved {len(quotes)} quotes")
else:
    raise SystemExit("No quotes fetched")
