from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "tvde-news.json"
try:
    LISBON = ZoneInfo("Europe/Lisbon")
except ZoneInfoNotFoundError:
    LISBON = datetime.now().astimezone().tzinfo or timezone.utc
GOOGLE_NEWS_SEARCH = "https://news.google.com/search?q=TVDE%20Portugal&hl=pt-PT&gl=PT&ceid=PT:pt-150"

RSS_QUERIES = [
    ("TVDE Portugal", "mercado TVDE"),
    ("Uber Portugal motorista", "Uber Portugal"),
    ("Bolt Portugal TVDE", "Bolt Portugal"),
    ("motoristas TVDE Portugal", "motoristas TVDE"),
]


@dataclass
class NewsItem:
    title: str
    summary: str
    url: str
    source: str
    topic: str
    published_dt: datetime


def build_rss_url(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=pt-PT&gl=PT&ceid=PT:pt-150"


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def trim_summary(text: str, limit: int = 180) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def extract_direct_link(description: str) -> str | None:
    match = re.search(r'href="([^"]+)"', description or "")
    if not match:
        return None
    url = html.unescape(match.group(1))
    if "news.google.com" in url:
        return None
    return url


def parse_pubdate(value: str) -> datetime | None:
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LISBON)


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def parse_feed(query: str, topic: str) -> list[NewsItem]:
    data = fetch_feed(build_rss_url(query))
    root = ET.fromstring(data)
    items: list[NewsItem] = []

    for item in root.findall("./channel/item"):
        title = clean_text(item.findtext("title", ""))
        if not title:
            continue
        description = item.findtext("description", "")
        summary = trim_summary(description or title)
        source = clean_text(item.findtext("source", "")) or "Google News"
        link = extract_direct_link(description) or clean_text(item.findtext("link", "")) or GOOGLE_NEWS_SEARCH
        published = parse_pubdate(item.findtext("pubDate", ""))
        if not published:
            continue

        items.append(
            NewsItem(
                title=title,
                summary=summary,
                url=link,
                source=source,
                topic=topic,
                published_dt=published,
            )
        )

    return items


def select_items(items: list[NewsItem]) -> tuple[list[NewsItem], str]:
    now = datetime.now(LISBON)
    yesterday = (now - timedelta(days=1)).date()

    previous_day = [item for item in items if item.published_dt.date() == yesterday]
    if previous_day:
        previous_day.sort(key=lambda item: item.published_dt, reverse=True)
        return previous_day[:6], f"noticias de {yesterday.strftime('%d/%m/%Y')}"

    recent = [item for item in items if item.published_dt >= now - timedelta(days=3)]
    recent.sort(key=lambda item: item.published_dt, reverse=True)
    return recent[:6], "ultimas 72 horas"


def dedupe_items(items: list[NewsItem]) -> list[NewsItem]:
    seen = set()
    deduped: list[NewsItem] = []
    for item in items:
        key = (item.title.lower(), item.source.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def format_display_date(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")


def main() -> None:
    fetched: list[NewsItem] = []
    for query, topic in RSS_QUERIES:
        try:
            fetched.extend(parse_feed(query, topic))
        except Exception:
            continue

    fetched = dedupe_items(fetched)
    selected, window_label = select_items(fetched)

    payload = {
        "source": "google-news-rss",
        "search_url": GOOGLE_NEWS_SEARCH,
        "updated_at": datetime.now(LISBON).strftime("%d/%m/%Y %H:%M"),
        "window_label": window_label,
        "featured": None,
        "posts": [],
    }

    if selected:
        featured = selected[0]
        payload["featured"] = {
            "title": featured.title,
            "summary": featured.summary,
            "url": featured.url,
            "source": featured.source,
            "topic": featured.topic,
            "published_at": format_display_date(featured.published_dt),
        }
        payload["posts"] = [
            {
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
                "source": item.source,
                "topic": item.topic,
                "published_at": format_display_date(item.published_dt),
            }
            for item in selected
        ]

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Notícias guardadas em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
