"""Keeps prices.json and news.json fresh for the desk clock.

Runs in a loop for up to ~5h45m, then the workflow starts the next run:
- prices: every minute while the US market is open, every 5 minutes otherwise on weekdays,
  hourly on weekends
- news: every 5 minutes
"""
import json
import time
import datetime
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

YAHOO = {"VIX": "^VIX", "SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI",
         "TA35": "TA35.TA", "USDILS": "ILS=X", "EURILS": "EURILS=X", "BTC": "BTC-USD"}
FEEDS = {
    "ynet": "https://www.ynet.co.il/Integration/StoryRss2.xml",
    "toi": "https://www.timesofisrael.com/feed/",
    "ynetnews": "https://www.ynetnews.com/Integration/StoryRss3082.xml",
}
NY = ZoneInfo("America/New_York")
RUN_MINUTES = 345
UA = {"User-Agent": "Mozilla/5.0 (desk-clock)"}


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return r.read()


def market_open():
    n = datetime.datetime.now(NY)
    m = n.hour * 60 + n.minute
    return n.weekday() < 5 and 9 * 60 + 25 <= m < 16 * 60 + 5


def fetch_prices():
    with open("tickers.json") as f:
        tickers = json.load(f)
    quotes = {}
    for sym in tickers:
        y = YAHOO.get(sym, sym)
        try:
            j = json.loads(get("https://query1.finance.yahoo.com/v8/finance/chart/"
                               + urllib.parse.quote(y) + "?interval=1d&range=1d"))
            meta = j["chart"]["result"][0]["meta"]
            price = meta["regularMarketPrice"]
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            quotes[sym] = {"price": price, "chg": price - prev,
                           "pct": (price - prev) / prev * 100 if prev else 0}
        except Exception as e:
            print(f"price {sym}: {e}")
    if quotes:
        with open("prices.json", "w") as f:
            json.dump({"updated": now_utc().isoformat(), "quotes": quotes}, f, indent=1)
    return bool(quotes)


def fetch_news():
    feeds = {}
    for key, url in FEEDS.items():
        try:
            root = ET.fromstring(get(url))
            items = []
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                if not title:
                    continue
                try:
                    d = parsedate_to_datetime(it.findtext("pubDate")).astimezone(
                        datetime.timezone.utc).isoformat()
                except Exception:
                    d = None
                items.append({"title": title, "date": d})
            items.sort(key=lambda i: i["date"] or "", reverse=True)
            feeds[key] = items[:12]
        except Exception as e:
            print(f"news {key}: {e}")
    if feeds:
        with open("news.json", "w") as f:
            json.dump({"updated": now_utc().isoformat(), "feeds": feeds}, f,
                      ensure_ascii=False, indent=1)
    return bool(feeds)


def run(*args):
    return subprocess.run(args, capture_output=True, text=True)


def commit():
    run("git", "add", "prices.json", "news.json")
    if run("git", "diff", "--cached", "--quiet").returncode == 0:
        return
    run("git", "commit", "-q", "-m", "Update prices and news")
    for _ in range(3):
        run("git", "pull", "-q", "--rebase", "-X", "theirs", "origin", "main")
        if run("git", "push", "-q", "origin", "main").returncode == 0:
            return
        time.sleep(3)
    print("push failed")


def main():
    start = time.time()
    last_price = last_news = 0.0
    while (time.time() - start) / 60 < RUN_MINUTES:
        t = time.time()
        weekday = datetime.datetime.now(NY).weekday() < 5
        price_every = 60 if market_open() else (300 if weekday else 3600)
        changed = False
        if t - last_price >= price_every:
            changed |= fetch_prices()
            last_price = t
        if t - last_news >= 300:
            changed |= fetch_news()
            last_news = t
        if changed:
            commit()
        time.sleep(max(5, 60 - (time.time() - t)))


if __name__ == "__main__":
    main()
