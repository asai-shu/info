"""AI関連の最新情報を RSS / Atom フィードから集めて、1枚の HTML ページにまとめる。

外部ライブラリや API は使わず、Python の標準機能だけで動く。
    python collector/collect.py
"""

from __future__ import annotations

import email.utils
import gzip
import hashlib
import html
import json
import re
import shutil
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import themes

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "feeds.toml"
DATA_PATH = ROOT / "data" / "items.json"
CURATED_PATH = ROOT / "data" / "curated.json"  # Claude Code（/curate）が選んで日本語で要約した注目記事
TEMPLATE_PATH = ROOT / "collector" / "template.html"
OUTPUT_PATH = ROOT / "docs" / "index.html"
STATIC_DIR = ROOT / "collector" / "static"  # アイコンなど、ページと一緒に公開するファイル

# 一部のサイトはブラウザ以外からのアクセスを拒否するため、一般的なブラウザ名を名乗る
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 ai-info-collector/1.0"
)
SUMMARY_LENGTH = 280
# 同じサイトへ続けて取りに行くときの間隔（秒）。Reddit は短い間隔だと拒否される
HOST_DELAY = {"www.reddit.com": 30}
DEFAULT_DELAY = 6

# filter = true のフィードで、これらのどれかを含む記事だけを残す
KEYWORDS = [
    "LLM", "GPT", "ChatGPT", "OpenAI", "Anthropic", "Claude", "Gemini", "DeepMind",
    "Llama", "Mistral", "DeepSeek", "Qwen", "Copilot", "Grok", "Perplexity",
    "Hugging Face", "Stable Diffusion", "Midjourney", "Sora", "transformer",
    "machine learning", "deep learning", "neural", "artificial intelligence",
    "agent", "RAG", "prompt", "chatbot", "NVIDIA",
    "生成AI", "人工知能", "機械学習", "深層学習", "エージェント", "プロンプト", "大規模言語モデル",
]
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS), re.IGNORECASE)
# 「AI」は単語として現れたときだけ一致させる（"maintain" などを拾わないため）
AI_WORD_RE = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])")


def local(tag: str) -> str:
    """名前空間を除いたタグ名を返す。"""
    return tag.rsplit("}", 1)[-1]


def child(elem: ET.Element, *names: str) -> ET.Element | None:
    for c in elem:
        if local(c.tag) in names:
            return c
    return None


def child_text(elem: ET.Element, *names: str) -> str:
    c = child(elem, *names)
    return "".join(c.itertext()).strip() if c is not None else ""


def clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > SUMMARY_LENGTH:
        text = text[:SUMMARY_LENGTH].rstrip() + "…"
    return text


def parse_date(raw: str) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def entry_link(entry: ET.Element) -> str:
    for c in entry:
        if local(c.tag) != "link":
            continue
        href = c.get("href")
        if href is None:
            # RSS 形式: <link>URL</link>
            if (c.text or "").strip():
                return c.text.strip()
            continue
        if c.get("rel", "alternate") == "alternate":
            return href.strip()
    guid = child(entry, "guid")
    if guid is not None and (guid.text or "").startswith("http"):
        return guid.text.strip()
    return ""


def parse_xml(xml_bytes: bytes) -> ET.Element:
    if xml_bytes[:2] == b"\x1f\x8b":
        xml_bytes = gzip.decompress(xml_bytes)
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError:
        # 書式が少し崩れたフィード（エスケープされていない & や制御文字など）を補正して読み直す
        text = xml_bytes.decode("utf-8", errors="replace").lstrip("\ufeff \t\r\n")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        text = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text)
        text = re.sub(r"^<\?xml[^>]*\?>", "", text)
        return ET.fromstring(text)


def parse_feed(xml_bytes: bytes) -> list[dict]:
    root = parse_xml(xml_bytes)
    entries = [e for e in root.iter() if local(e.tag) in ("item", "entry")]
    results = []
    for e in entries:
        title = clean_text(child_text(e, "title"))
        link = entry_link(e)
        if not title or not link:
            continue
        summary = clean_text(child_text(e, "description", "summary", "content", "encoded"))
        date = parse_date(child_text(e, "pubDate", "published", "updated", "date"))
        # Google ニュースなどは <source> に元の媒体名が入り、タイトル末尾にも " - 媒体名" が付く
        publisher = clean_text(child_text(e, "source"))
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3]
        if publisher and summary.startswith(title):
            summary = ""
        results.append({"title": title, "link": link, "summary": summary, "date": date, "publisher": publisher})
    return results


def is_ai_related(item: dict) -> bool:
    text = f"{item['title']} {item['summary']}"
    return bool(KEYWORD_RE.search(text) or AI_WORD_RE.search(text))


def title_key(title: str) -> str:
    return re.sub(r"\W+", "", title).lower()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.read()
        except urllib.error.HTTPError as exc:
            # 404 などは何度試しても同じなので、混雑（429）とサーバー側の一時的な不調（5xx）だけやり直す
            if attempt == 2 or not (exc.code == 429 or exc.code >= 500):
                raise
            wait = exc.headers.get("Retry-After", "")
            time.sleep(min(int(wait), 30) if wait.isdigit() else 10 * (attempt + 1))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)


def collect_feed(feed: dict, now: datetime) -> tuple[list[dict], str | None]:
    url = urllib.parse.quote(feed["url"], safe=":/?&=%+")
    try:
        entries = parse_feed(fetch(url))
    except Exception as exc:  # 1つのフィードが失敗しても全体は止めない
        return [], f"{type(exc).__name__}: {exc}"

    if feed.get("filter") == "gear":
        # ガジェット系のサイトは記事が多いので、AI関連か、ブラウザ・デバイスの記事だけ残す
        entries = [e for e in entries if is_ai_related(e) or themes.is_gear_related(e)]
    elif feed.get("filter"):
        entries = [e for e in entries if is_ai_related(e)]
    if feed.get("limit"):
        entries = entries[: feed["limit"]]

    items = []
    for e in entries:
        items.append({
            "id": hashlib.sha1(e["link"].encode()).hexdigest()[:16],
            "title": e["title"],
            "link": e["link"],
            "summary": e["summary"],
            "date": (e["date"] or now).isoformat(timespec="seconds"),
            "source": feed["name"],
            "publisher": e["publisher"],
            "category": feed["category"],
            "lang": feed["lang"],
        })
    return items, None


def load_existing() -> dict[str, dict]:
    if not DATA_PATH.exists():
        return {}
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["items"]}


def load_curated(items: list[dict]) -> dict | None:
    """注目記事に、元の記事のリンクや取得元を付けて返す。保存期間を過ぎて消えた記事は除く。"""
    if not CURATED_PATH.exists():
        return None
    curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in items}
    for theme in ("tech", "money", "gear"):
        curated[theme] = [
            {**by_id[e["id"]], **e} for e in curated.get(theme, []) if e.get("id") in by_id
        ]
    return curated


def render(items: list[dict], statuses: list[dict], updated: datetime, feeds: list[dict]) -> str:
    feed_themes = {f["name"]: f["theme"] for f in feeds if f.get("theme")}
    payload = {
        "updated": updated.isoformat(timespec="seconds"),
        "items": [themes.annotate(i, feed_themes) for i in items],
        "curated": load_curated(items),
        "statuses": statuses,
    }
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE_PATH.read_text(encoding="utf-8").replace("/*__DATA__*/null", blob)


def main() -> int:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    settings = config.get("settings", {})
    feeds = config["feeds"]
    now = datetime.now(timezone.utc)

    # 同じサイトへは間隔を空けて1件ずつ取りに行き、サイトどうしは並行して取得する
    by_host = defaultdict(list)
    for index, feed in enumerate(feeds):
        by_host[urllib.parse.urlsplit(feed["url"]).hostname].append(index)

    results: list = [None] * len(feeds)

    def collect_host(host: str, indexes: list[int]) -> None:
        for n, index in enumerate(indexes):
            if n:
                time.sleep(HOST_DELAY.get(host, DEFAULT_DELAY))
            results[index] = collect_feed(feeds[index], now)

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(collect_host, by_host.keys(), by_host.values()))

    items = load_existing()
    # 別の取得元から同じ記事が入るのを防ぐため、タイトルでも重複を判定する
    seen_titles = {title_key(i["title"]): i["id"] for i in items.values()}
    statuses = []
    for feed, (new_items, error) in zip(feeds, results):
        added = 0
        for item in new_items:
            key = title_key(item["title"])
            if seen_titles.setdefault(key, item["id"]) != item["id"]:
                continue
            if item["id"] in items:
                # 既に取得済みなら、最初に見つけた日時を保ったまま内容だけ更新する
                item["date"] = items[item["id"]]["date"]
            else:
                added += 1
            items[item["id"]] = item
        statuses.append({"name": feed["name"], "ok": error is None, "count": len(new_items), "added": added, "error": error})
        mark = "OK " if error is None else "NG "
        print(f"{mark} {feed['name']}: {len(new_items)}件（新規 {added}件）" + (f" {error}" if error else ""))

    cutoff = now - timedelta(days=settings.get("keep_days", 14))
    kept = [i for i in items.values() if datetime.fromisoformat(i["date"]) >= cutoff]
    kept.sort(key=lambda i: (i["date"], i["id"]), reverse=True)
    kept = kept[: settings.get("max_items", 3000)]

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps({"updated": now.isoformat(timespec="seconds"), "statuses": statuses, "items": kept}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render(kept, statuses, now, feeds), encoding="utf-8")
    shutil.copytree(STATIC_DIR, OUTPUT_PATH.parent, dirs_exist_ok=True)
    # ホーム画面のアプリが、新しいデータが出たことに気づいて読み込み直すための小さなファイル
    curated = json.loads(CURATED_PATH.read_text(encoding="utf-8")) if CURATED_PATH.exists() else {}
    (OUTPUT_PATH.parent / "version.json").write_text(
        json.dumps({"updated": now.isoformat(timespec="seconds"), "curated": curated.get("generated")}),
        encoding="utf-8",
    )

    ok = sum(s["ok"] for s in statuses)
    print(f"\n{ok}/{len(statuses)} フィード成功、保存 {len(kept)}件 → {OUTPUT_PATH.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
