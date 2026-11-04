"""Fetch Israeli news feeds for the desk clock and write news.json."""
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = {
    "ynet": "https://www.ynet.co.il/Integration/StoryRss2.xml",
    "toi": "https://www.timesofisrael.com/feed/",
    "ynetnews": "https://www.ynetnews.com/Integration/StoryRss3082.xml",
}

out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "feeds": {}}
for key, url in FEEDS.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (desk-clock)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            root = ET.fromstring(r.read())
        items = []
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            if not title:
                continue
            date = None
            try:
                date = parsedate_to_datetime(it.findtext("pubDate")).astimezone(datetime.timezone.utc).isoformat()
            except Exception:
                pass
            items.append({"title": title, "date": date})
        items.sort(key=lambda i: i["date"] or "", reverse=True)
        out["feeds"][key] = items[:12]
        print(f"{key}: {len(items)} items")
    except Exception as e:
        print(f"{key}: {e}")

if out["feeds"]:
    with open("news.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
else:
    raise SystemExit("No feeds fetched")
