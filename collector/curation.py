"""Claude Code に記事を選んでもらうための補助ツール。

    python3 collector/curation.py candidates   # 候補記事を一覧にして表示する
    python3 collector/curation.py check        # data/curated.json の書式を確かめる
    python3 collector/curation.py check-demand # data/demand.json の書式を確かめる
    python3 collector/curation.py untranslated # まだ日本語に訳していない外国語の記事を一覧にする
    python3 collector/curation.py check-translations # data/translations.json の書式を確かめ、消えた記事の訳を捨てる

Claude Code の /curate・/demand・/translate コマンド（.claude/skills/ の中の SKILL.md）から使う。
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import themes

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "items.json"
CURATED_PATH = ROOT / "data" / "curated.json"
CONFIG_PATH = ROOT / "feeds.toml"
DEMAND_PATH = ROOT / "data" / "demand.json"
TRANSLATIONS_PATH = ROOT / "data" / "translations.json"

# 収益化のヒント・ツール・ガジェットは、需要リサーチ・機材・ソフトガイドのページに役割を移した
THEMES = ("tech",)
ENTRY_FIELDS = ("id", "title_ja", "summary_ja", "point")
DEMAND_FIELDS = ("section", "category", "title", "body")


def load_items() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))["items"]


def candidates(hours: int, limit: int, per_source: int, category: str = "") -> list[dict]:
    feeds = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))["feeds"]
    feed_themes = {f["name"]: f["theme"] for f in feeds if f.get("theme")}
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    picked = []
    for item in load_items():
        if datetime.fromisoformat(item["date"]) < since or (category and item["category"] != category):
            continue
        scores = {t: v["score"] for t, v in themes.annotate(item, feed_themes)["themes"].items()}
        picked.append({
            "id": item["id"],
            "title": item["title"],
            "link": item["link"],
            "summary": item["summary"][:140],
            "source": item["publisher"] or item["source"],
            "category": item["category"],
            "lang": item["lang"],
            "date": item["date"][:16],
            "keyword_scores": scores,
            "feed": item["source"],
        })
    # キーワードの点数が高い記事を優先する
    picked.sort(key=lambda c: (max(c["keyword_scores"].values(), default=0), c["date"]), reverse=True)
    # 似た記事が大量に流れる取得元（note の副業記事など）で候補が埋まらないよう、取得元ごとの件数を制限する
    per_feed: dict[str, int] = {}
    result = []
    for c in picked:
        per_feed[c["feed"]] = per_feed.get(c["feed"], 0) + 1
        if per_feed[c["feed"]] <= per_source:
            result.append(c)
    for c in result:
        del c["feed"]
    return result[:limit]


def check() -> list[str]:
    if not CURATED_PATH.exists():
        return [f"{CURATED_PATH.relative_to(ROOT)} がありません"]
    data = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    ids = {i["id"] for i in load_items()}
    errors = []
    if not isinstance(data.get("overview"), str) or not data["overview"].strip():
        errors.append("overview（今日のまとめ）がありません")
    try:
        datetime.fromisoformat(data.get("generated", ""))
    except (TypeError, ValueError):
        errors.append("generated が ISO 8601 形式の日時ではありません")
    for theme in THEMES:
        entries = data.get(theme)
        if not isinstance(entries, list) or not entries:
            errors.append(f"{theme} の記事がありません")
            continue
        for n, entry in enumerate(entries):
            missing = [f for f in ENTRY_FIELDS if not str(entry.get(f, "")).strip()]
            if missing:
                errors.append(f"{theme}[{n}] に {', '.join(missing)} がありません")
            elif entry["id"] not in ids:
                errors.append(f"{theme}[{n}] の id {entry['id']} は data/items.json にありません")
    return errors


def load_translations() -> dict:
    if not TRANSLATIONS_PATH.exists():
        return {"items": {}}
    return json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))


def untranslated(limit: int) -> list[dict]:
    """訳していない外国語の記事を、「技術の進歩」に載りやすい記事 → 新しい記事の順に返す。"""
    feeds = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))["feeds"]
    feed_themes = {f["name"]: f["theme"] for f in feeds if f.get("theme")}
    done = load_translations()["items"]
    picked = []
    for item in load_items():
        if item["lang"] == "ja" or item["id"] in done:
            continue
        tech = themes.annotate(item, feed_themes)["themes"].get("tech")
        picked.append({
            "id": item["id"],
            "title": item["title"],
            "summary": item["summary"][:400],
            "lang": item["lang"],
            "source": item["publisher"] or item["source"],
            "date": item["date"][:16],
            "tech": bool(tech),
        })
    picked.sort(key=lambda c: (c["tech"], c["date"]), reverse=True)
    return picked[:limit]


def check_translations() -> list[str]:
    """訳の書式を確かめる。保存期間を過ぎて消えた記事の訳は、ここで捨てる。"""
    data = load_translations()
    ids = {i["id"] for i in load_items()}
    kept = {k: v for k, v in data.get("items", {}).items() if k in ids}
    errors = []
    for k, v in kept.items():
        if not str(v.get("title", "")).strip():
            errors.append(f"{k} の title（日本語のタイトル）がありません")
        if "summary" not in v:
            errors.append(f"{k} に summary がありません（要約がない記事は空文字にする）")
    if len(kept) != len(data.get("items", {})):
        data["items"] = kept
        TRANSLATIONS_PATH.write_text(dump_translations(data), encoding="utf-8")
    return errors


def dump_translations(data: dict) -> str:
    """1件1行で書き出す（追加・削除した記事の行だけが差分になるように）。"""
    rows = [json.dumps(k, ensure_ascii=False) + ": " + json.dumps(v, ensure_ascii=False)
            for k, v in data["items"].items()]
    return '{\n"items": {\n' + ",\n".join(rows) + "\n}\n}\n"


def check_checked(data: dict) -> list[str]:
    """毎晩の確認の記録（checked）があれば、日時と結果が書かれているか確かめる。"""
    checked = data.get("checked")
    if checked is None:
        return []
    try:
        datetime.fromisoformat(str(checked.get("at", "")))
    except ValueError:
        return ["checked.at が日時（例 2026-10-31T00:10:00+09:00）ではありません"]
    if not str(checked.get("result", "")).strip():
        return ["checked.result（変更なし・更新あり など）がありません"]
    return []


def check_demand() -> list[str]:
    if not DEMAND_PATH.exists():
        return [f"{DEMAND_PATH.relative_to(ROOT)} がありません"]
    data = json.loads(DEMAND_PATH.read_text(encoding="utf-8"))
    errors = []
    try:
        datetime.strptime(data.get("updated", ""), "%Y-%m-%d")
    except (TypeError, ValueError):
        errors.append("updated が YYYY-MM-DD 形式の日付ではありません")
    if not str(data.get("overview", "")).strip():
        errors.append("overview（今回のまとめ）がありません")
    errors += check_checked(data)
    sections = data.get("sections") or {}
    for key in sections:
        if not any(i.get("section") == key for i in data.get("items", [])):
            errors.append(f"{key} の項目がありません")
    for n, item in enumerate(data.get("items", [])):
        missing = [f for f in DEMAND_FIELDS if not str(item.get(f, "")).strip()]
        if missing:
            errors.append(f"items[{n}] に {', '.join(missing)} がありません")
        elif item["section"] not in sections:
            errors.append(f"items[{n}] の section {item['section']} は sections にありません")
        if not item.get("sources") or any(not str(s.get("url", "")).startswith("http") for s in item["sources"]):
            errors.append(f"items[{n}]（{item.get('title', '')}）の sources がないか、URL が正しくありません")
        if any(not str(x.get("label", "")).strip() or not str(x.get("text", "")).strip() for x in item.get("notes", [])):
            errors.append(f"items[{n}]（{item.get('title', '')}）の notes に label か text がありません")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    cand = sub.add_parser("candidates")
    cand.add_argument("--hours", type=int, default=36, help="何時間前までの記事を候補にするか")
    cand.add_argument("--limit", type=int, default=180, help="候補の最大件数")
    cand.add_argument("--per-source", type=int, default=8, help="1つの取得元から候補にする最大件数")
    cand.add_argument("--category", default="", help="この分類の記事だけを候補にする（例: 需要の種）")
    sub.add_parser("check")
    sub.add_parser("check-demand")
    untr = sub.add_parser("untranslated")
    untr.add_argument("--limit", type=int, default=300, help="一度に訳す最大件数")
    sub.add_parser("check-translations")
    args = parser.parse_args()

    if args.command == "candidates":
        for c in candidates(args.hours, args.limit, args.per_source, args.category):
            print(json.dumps(c, ensure_ascii=False))
        return 0
    if args.command == "untranslated":
        for c in untranslated(args.limit):
            print(json.dumps(c, ensure_ascii=False))
        return 0

    path, errors = {
        "check": (CURATED_PATH, check),
        "check-demand": (DEMAND_PATH, check_demand),
        "check-translations": (TRANSLATIONS_PATH, check_translations),
    }[args.command]
    errors = errors()
    for e in errors:
        print("NG", e)
    if not errors:
        print(f"OK {path.relative_to(ROOT)} は正しい書式です")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
