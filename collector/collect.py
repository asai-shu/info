"""AI関連の最新情報を RSS / Atom フィードから集めて、1枚の HTML ページにまとめる。

外部ライブラリや API は使わず、Python の標準機能だけで動く。
    python collector/collect.py
"""

from __future__ import annotations

import email.utils
import hashlib
import html
import json
import re
import sys
import tomllib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "feeds.toml"
DATA_PATH = ROOT / "data" / "items.json"
TEMPLATE_PATH = ROOT / "collector" / "template.html"
OUTPUT_PATH = ROOT / "docs" / "index.html"

USER_AGENT = "Mozilla/5.0 (compatible; ai-info-collector/1.0; +https://github.com/asai-shu/info)"
SUMMARY_LENGTH = 280

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


def parse_feed(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    entries = [e for e in root.iter() if local(e.tag) in ("item", "entry")]
    results = []
    for e in entries:
        title = clean_text(child_text(e, "title"))
        link = entry_link(e)
        if not title or not link:
            continue
        summary = clean_text(child_text(e, "description", "summary", "content", "encoded"))
        date = parse_date(child_text(e, "pubDate", "published", "updated", "date"))
        results.append({"title": title, "link": link, "summary": summary, "date": date})
    return results


def is_ai_related(item: dict) -> bool:
    text = f"{item['title']} {item['summary']}"
    return bool(KEYWORD_RE.search(text) or AI_WORD_RE.search(text))


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def collect_feed(feed: dict, now: datetime) -> tuple[list[dict], str | None]:
    url = urllib.parse.quote(feed["url"], safe=":/?&=%")
    try:
        entries = parse_feed(fetch(url))
    except Exception as exc:  # 1つのフィードが失敗しても全体は止めない
        return [], f"{type(exc).__name__}: {exc}"

    if feed.get("filter"):
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
            "category": feed["category"],
            "lang": feed["lang"],
        })
    return items, None


def load_existing() -> dict[str, dict]:
    if not DATA_PATH.exists():
        return {}
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["items"]}


def render(items: list[dict], statuses: list[dict], updated: datetime) -> str:
    payload = {
        "updated": updated.isoformat(timespec="seconds"),
        "items": items,
        "statuses": statuses,
    }
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE_PATH.read_text(encoding="utf-8").replace("/*__DATA__*/null", blob)


def main() -> int:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    settings = config.get("settings", {})
    feeds = config["feeds"]
    now = datetime.now(timezone.utc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda f: collect_feed(f, now), feeds))

    items = load_existing()
    statuses = []
    for feed, (new_items, error) in zip(feeds, results):
        added = 0
        for item in new_items:
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
        json.dumps({"updated": now.isoformat(timespec="seconds"), "items": kept}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render(kept, statuses, now), encoding="utf-8")

    ok = sum(s["ok"] for s in statuses)
    print(f"\n{ok}/{len(statuses)} フィード成功、保存 {len(kept)}件 → {OUTPUT_PATH.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
