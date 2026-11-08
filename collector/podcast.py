"""ポッドキャストの文字起こしを取ってきて、Claude Code が訳しやすい形に分ける補助ツール。

    python3 collector/podcast.py check                  # 新しい回を探して data/podcasts.json に記録する
    python3 collector/podcast.py todo                   # 今晩やる作業（訳す部分）を一覧にする
    python3 collector/podcast.py fetch ID --out DIR     # 文字起こしを取ってきて、部分（約15〜20分）ごとのファイルに分ける
    python3 collector/podcast.py update ID ...          # 進み具合を記録する（--parts-done、--folder など）

Claude Code の /podcast コマンド（.claude/skills/podcast/SKILL.md）から使う。
文字起こしや訳はリポジトリに保存しない（公開されるため）。訳は Google ドライブにだけ保存する。
data/podcasts.json には、回のタイトル・リンク・進み具合だけを記録する。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "podcasts.json"
USER_AGENT = "ai-info-podcast/1.0 (+https://github.com/asai-shu/info)"

SHOWS = {
    "practical-ai": {
        "name": "Practical AI",
        "feed": "https://changelog.com/practicalai/feed",
    },
    "latent-space": {
        "name": "Latent Space",
        "feed": "https://podcast.latent.space/feed.xml",
        # 文字起こしのファイルが読めないときは、ブログ記事の中の文字起こしを探す
        "article_feed": "https://www.latent.space/feed",
    },
}

PART_WORDS = 3000  # 1部分あたりの英語の語数（話す速さにより、約15〜20分）
NIGHT_PARTS = 3  # 1晩に訳す部分の数（約1時間分）
GIVE_UP_DAYS = 7  # 文字起こしや Spotify の配信が出るのを、公開から何日待つか

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


# ---------- 共通 ----------

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.read()
        except urllib.error.HTTPError as exc:
            # 403（ロボット確認など）や 404 は何度試しても同じなので、すぐあきらめる
            if attempt == 2 or not (exc.code == 429 or exc.code >= 500):
                raise
            time.sleep(10 * (attempt + 1))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)
    raise RuntimeError("unreachable")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"since": datetime.now(timezone.utc).date().isoformat(), "drive": {}, "episodes": {}}


def save_state(state: dict) -> None:
    state["episodes"] = dict(sorted(state["episodes"].items(), key=lambda kv: kv[1]["published"]))
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def parse_date(text: str) -> datetime:
    dt = parsedate_to_datetime(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def duration_minutes(text: str | None) -> int | None:
    if not text:
        return None
    nums = [int(n) for n in text.strip().split(":") if n.isdigit()]
    if not nums:
        return None
    seconds = 0
    for n in nums:
        seconds = seconds * 60 + n
    return round(seconds / 60)


def clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


# ---------- 新しい回を探す ----------

def check(state: dict) -> list[dict]:
    since = datetime.fromisoformat(state["since"]).replace(tzinfo=timezone.utc)
    added = []
    for show_id, show in SHOWS.items():
        try:
            root = ET.fromstring(fetch(show["feed"]))
        except Exception as exc:  # noqa: BLE001
            print(f"[{show['name']}] 新着一覧を読めませんでした: {exc}", file=sys.stderr)
            continue
        for item in root.iter("item"):
            if item.find("enclosure") is None:
                continue  # 音声のない投稿（ブログ記事だけ）は対象外
            published = parse_date(item.findtext("pubDate") or "")
            if published < since:
                continue
            guid = item.findtext("guid") or item.findtext("link") or item.findtext("title")
            ep_id = hashlib.sha1(f"{show_id}:{guid}".encode()).hexdigest()[:12]
            if ep_id in state["episodes"]:
                continue
            vtt = ""
            for el in item:
                if el.tag.endswith("}transcript") and "vtt" in (el.get("type") or ""):
                    vtt = el.get("url") or ""
            ep = {
                "show": show_id,
                "show_name": show["name"],
                "title": (item.findtext("title") or "").strip(),
                "published": published.astimezone(timezone.utc).isoformat()[:16] + "Z",
                "minutes": duration_minutes(item.findtext("itunes:duration", namespaces=NS)),
                "link": (item.findtext("link") or "").strip(),
                "transcript_url": vtt,
                "status": "new",
                "parts_total": None,
                "parts_done": 0,
                "spotify_url": "",
                "drive_folder_id": "",
                "note": "",
            }
            state["episodes"][ep_id] = ep
            added.append({"id": ep_id, **ep})
    return added


def expire(state: dict) -> list[dict]:
    """文字起こしや Spotify の配信が、公開から GIVE_UP_DAYS 日たっても出ない回はあきらめる。"""
    now = datetime.now(timezone.utc)
    given_up = []
    for ep_id, ep in state["episodes"].items():
        if ep["status"] != "new" or ep["parts_done"]:
            continue
        published = datetime.fromisoformat(ep["published"].replace("Z", "+00:00"))
        if now - published > timedelta(days=GIVE_UP_DAYS):
            ep["status"] = "skipped"
            ep["note"] = ep["note"] or f"公開から{GIVE_UP_DAYS}日たっても、文字起こしか Spotify の配信が見つかりませんでした"
            given_up.append({"id": ep_id, **ep})
    return given_up


def todo(state: dict, max_parts: int) -> list[dict]:
    """今晩訳す部分。始めた回を先に終わらせ、そのあと古い回から順に。"""
    plan = []
    left = max_parts
    eps = sorted(
        ((i, e) for i, e in state["episodes"].items() if e["status"] in ("new", "active")),
        key=lambda kv: (kv[1]["status"] != "active", kv[1]["published"]),
    )
    for ep_id, ep in eps:
        if left <= 0:
            break
        total = ep["parts_total"]
        first = ep["parts_done"] + 1
        if total is None:
            # 何部分になるかは、文字起こしを取るまでわからない
            parts = list(range(first, first + left))
        else:
            parts = list(range(first, min(total, first + left - 1) + 1))
        if not parts:
            continue
        plan.append({"id": ep_id, "show": ep["show_name"], "title": ep["title"], "parts": parts,
                     "parts_total": total, "needs_summary": ep["parts_done"] == 0,
                     "spotify_url": ep["spotify_url"], "drive_folder_id": ep["drive_folder_id"]})
        left -= len(parts) if total is not None else left
    return plan


# ---------- 文字起こしを取る ----------

def parse_vtt(text: str) -> list[dict]:
    """WebVTT を「時刻・話し手・文」の段落のならびにする。"""
    paragraphs = []
    speaker = ""
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        times = [i for i, ln in enumerate(lines) if "-->" in ln]
        if not times:
            continue
        start = lines[times[0]].split("-->")[0].strip()
        h, m, s = (["0"] + start.split(":"))[-3:]
        seconds = int(h) * 3600 + int(m) * 60 + float(s)
        body = " ".join(lines[times[0] + 1:])
        m_v = re.match(r"<v\s+([^>]+)>", body)
        if m_v:
            speaker = m_v.group(1).strip()
        body = html.unescape(re.sub(r"<[^>]+>", "", body)).strip()
        if body:
            paragraphs.append({"t": seconds, "speaker": speaker, "text": body})
    return merge_short(paragraphs)


def merge_short(paragraphs: list[dict], min_words: int = 40) -> list[dict]:
    """短すぎる段落（同じ話し手）は前の段落につなげて、読みやすくする。"""
    merged: list[dict] = []
    for p in paragraphs:
        if (merged and merged[-1]["speaker"] == p["speaker"]
                and len(merged[-1]["text"].split()) < min_words):
            merged[-1]["text"] += " " + p["text"]
        else:
            merged.append(dict(p))
    return merged


def article_transcript(page_html: str) -> list[dict]:
    """latent.space の記事の「Transcript」見出しの後ろから、時刻つきの段落を取り出す。"""
    i = page_html.rfind(">Transcript<")
    if i < 0:
        return []
    paragraphs = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", page_html[i:], re.S):
        raw = m.group(1)
        stamp = re.match(r"\s*<b>\s*([\d:]+)\s*</b>", raw)
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        text = re.sub(r"\s+", " ", text).strip()
        if not stamp:
            if paragraphs and text:
                paragraphs[-1]["text"] += " " + text
            continue
        nums = [int(n) for n in stamp.group(1).split(":")]
        seconds = 0
        for n in nums:
            seconds = seconds * 60 + n
        text = text[len(stamp.group(1)):].strip()
        if text:
            paragraphs.append({"t": seconds, "speaker": "", "text": text})
    return paragraphs


def title_words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) >= 4}


def find_article(ep: dict, feed_url: str) -> tuple[str, list[dict]]:
    """同じ回のブログ記事（文字起こしつき）を探す。見つからなければ ("", [])。"""
    candidates = []
    if "latent.space/p/" in ep["link"]:
        candidates.append(ep["link"])
    try:
        root = ET.fromstring(fetch(feed_url))
    except Exception:  # noqa: BLE001
        root = None
    want = title_words(ep["title"])
    published = datetime.fromisoformat(ep["published"].replace("Z", "+00:00"))
    if root is not None:
        for item in root.iter("item"):
            when = parse_date(item.findtext("pubDate") or "")
            if abs(when - published) > timedelta(days=10):
                continue
            words = title_words(item.findtext("title") or "")
            overlap = len(want & words) / max(1, min(len(want), len(words)))
            if overlap < 0.4:
                continue
            body = item.findtext("content:encoded", namespaces=NS) or ""
            paras = article_transcript(body)
            if paras:
                return item.findtext("link") or "", paras
            candidates.append(item.findtext("link") or "")
    for url in candidates:
        try:
            paras = article_transcript(fetch(url).decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            continue
        if paras:
            return url, paras
    return "", []


def get_transcript(ep: dict) -> tuple[str, list[dict], list[str]]:
    """(取ってきた場所, 段落, うまくいかなかった理由) を返す。"""
    problems = []
    if ep["transcript_url"]:
        try:
            paras = parse_vtt(fetch(ep["transcript_url"]).decode("utf-8", "replace"))
            if paras:
                return ep["transcript_url"], paras, problems
            problems.append("文字起こしのファイルが空でした")
        except urllib.error.HTTPError as exc:
            reason = "ロボット確認で止められた" if exc.code == 403 else f"エラー {exc.code}"
            problems.append(f"文字起こしのファイルを読めませんでした（{reason}）")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"文字起こしのファイルを読めませんでした（{exc}）")
    else:
        problems.append("新着一覧に文字起こしのファイルが付いていません")
    feed = SHOWS[ep["show"]].get("article_feed")
    if feed:
        url, paras = find_article(ep, feed)
        if paras:
            return url, paras, problems
        problems.append("ブログ記事にも文字起こしが見つかりませんでした")
    return "", [], problems


def split_parts(paragraphs: list[dict], part_words: int) -> list[list[dict]]:
    total = sum(len(p["text"].split()) for p in paragraphs)
    count = max(1, round(total / part_words))
    target = total / count
    parts: list[list[dict]] = [[]]
    words = 0
    for p in paragraphs:
        if words >= target * len(parts) and len(parts) < count:
            parts.append([])
        parts[-1].append(p)
        words += len(p["text"].split())
    return parts


def render(paragraphs: list[dict]) -> str:
    lines = []
    for p in paragraphs:
        who = f" {p['speaker']}:" if p["speaker"] else ""
        lines.append(f"[{clock(p['t'])}]{who} {p['text']}")
    return "\n\n".join(lines) + "\n"


def fetch_episode(state: dict, ep_id: str, out: Path) -> dict:
    ep = state["episodes"][ep_id]
    source, paragraphs, problems = get_transcript(ep)
    if not paragraphs:
        return {"ok": False, "id": ep_id, "problems": problems}
    parts = split_parts(paragraphs, PART_WORDS)
    out.mkdir(parents=True, exist_ok=True)
    (out / "full.txt").write_text(render(paragraphs), encoding="utf-8")
    ranges = []
    for n, part in enumerate(parts, 1):
        (out / f"part-{n}.txt").write_text(render(part), encoding="utf-8")
        end = parts[n][0]["t"] if n < len(parts) else None
        ranges.append({"part": n, "start": clock(part[0]["t"]), "end": clock(end) if end is not None else "最後",
                       "words": sum(len(p["text"].split()) for p in part), "file": str(out / f"part-{n}.txt")})
    if ep["parts_total"] not in (None, len(parts)):
        problems.append(f"部分の数が前回（{ep['parts_total']}）と変わりました。文字起こしが直された可能性があります")
    ep["parts_total"] = len(parts)
    return {"ok": True, "id": ep_id, "source": source, "full": str(out / "full.txt"),
            "words": sum(r["words"] for r in ranges), "parts": ranges, "problems": problems}


# ---------- 入口 ----------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="新しい回を探す")
    p_todo = sub.add_parser("todo", help="今晩やる作業を一覧にする")
    p_todo.add_argument("--max-parts", type=int, default=NIGHT_PARTS)
    p_fetch = sub.add_parser("fetch", help="文字起こしを取って部分に分ける")
    p_fetch.add_argument("id")
    p_fetch.add_argument("--out", required=True, type=Path)
    p_up = sub.add_parser("update", help="進み具合を記録する")
    p_up.add_argument("id")
    p_up.add_argument("--parts-done", type=int)
    p_up.add_argument("--folder")
    p_up.add_argument("--spotify")
    p_up.add_argument("--skip", metavar="理由", help="この回をあきらめる（理由を書く）")
    p_up.add_argument("--note")
    p_drive = sub.add_parser("drive", help="Google ドライブのフォルダーの ID を記録する")
    p_drive.add_argument("key", help="root（ポッドキャスト学習）または番組の ID（practical-ai など）")
    p_drive.add_argument("folder_id")
    args = parser.parse_args()

    state = load_state()
    if args.cmd == "check":
        added = check(state)
        given_up = expire(state)
        save_state(state)
        print(json.dumps({"added": added, "given_up": given_up, "drive": state["drive"]},
                         ensure_ascii=False, indent=1))
    elif args.cmd == "todo":
        print(json.dumps(todo(state, args.max_parts), ensure_ascii=False, indent=1))
    elif args.cmd == "fetch":
        result = fetch_episode(state, args.id, args.out)
        save_state(state)
        print(json.dumps(result, ensure_ascii=False, indent=1))
        if not result["ok"]:
            sys.exit(2)
    elif args.cmd == "update":
        ep = state["episodes"][args.id]
        if args.folder:
            ep["drive_folder_id"] = args.folder
        if args.spotify:
            ep["spotify_url"] = args.spotify
        if args.note is not None:
            ep["note"] = args.note
        if args.parts_done is not None:
            ep["parts_done"] = args.parts_done
            ep["status"] = "done" if ep["parts_total"] and args.parts_done >= ep["parts_total"] else "active"
        if args.skip:
            ep["status"] = "skipped"
            ep["note"] = args.skip
        save_state(state)
        print(json.dumps({"id": args.id, **ep}, ensure_ascii=False, indent=1))
    elif args.cmd == "drive":
        state["drive"][args.key] = args.folder_id
        save_state(state)
        print(json.dumps(state["drive"], ensure_ascii=False))


if __name__ == "__main__":
    main()
