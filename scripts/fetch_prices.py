"""Fetch prices for the desk clock and write prices.json.

Run with --loop to keep refreshing every 60 seconds while the US market is open.
"""
import json
import sys
import time
import datetime
import subprocess
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

INDEX = {"VIX": "^VIX", "SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI", "TA35": "TA35.TA"}
NY = ZoneInfo("America/New_York")
MAX_MINUTES = 330  # stay under GitHub's 6-hour job limit


def market_open(now=None):
    now = (now or datetime.datetime.now(NY)).astimezone(NY)
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    return 9 * 60 + 25 <= mins < 16 * 60 + 5


def fetch():
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
            quotes[sym] = {"price": price, "chg": price - prev,
                           "pct": (price - prev) / prev * 100 if prev else 0}
        except Exception as e:
            print(f"{sym}: {e}")
    return quotes


def save(quotes):
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "quotes": quotes}
    with open("prices.json", "w") as f:
        json.dump(out, f, indent=1)


def commit():
    run = lambda *a: subprocess.run(a, check=False, capture_output=True, text=True)
    run("git", "add", "prices.json")
    if run("git", "diff", "--cached", "--quiet").returncode == 0:
        return
    run("git", "commit", "-m", "Update prices")
    for _ in range(3):
        run("git", "pull", "--rebase", "-X", "theirs", "origin", "main")
        if run("git", "push", "origin", "main").returncode == 0:
            return
        time.sleep(3)


def main():
    loop = "--loop" in sys.argv
    start = time.time()
    while True:
        q = fetch()
        if q:
            save(q)
            commit()
        if not loop or not market_open() or (time.time() - start) / 60 > MAX_MINUTES:
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
