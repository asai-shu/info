"""記事を「AI技術の進歩」「大学生の収益化のヒント」「ツール・ガジェット」の3つのテーマで採点し、短い要約を付ける。

AI の API は使わず、キーワードの一致と取得元の分類で判定する。
判定の基準を変えたいときは、下の TECH / MONEY / GEAR のキーワードを編集する。
"""

from __future__ import annotations

import re

# (表示する理由のラベル, 点数, キーワード)
TECH = [
    ("新モデル・新機能", 2, [
        "new model", "model release", "launches", "launched", "unveil", "introduces", "introducing",
        "rolls out", "announces", "now available", "新モデル", "新機能", "発表", "リリース", "公開",
        "提供開始", "アップデート", "搭載",
    ]),
    ("研究・論文", 2, [
        "paper", "research", "arxiv", "researchers", "study finds", "論文", "研究", "開発に成功",
    ]),
    ("性能向上", 2, [
        "benchmark", "state-of-the-art", "SOTA", "outperform", "breakthrough", "faster", "accuracy",
        "reasoning", "ベンチマーク", "精度", "性能", "高速", "推論", "ブレイクスルー", "最高", "世界初",
    ]),
    ("オープンソース", 2, [
        "open source", "open-source", "open weights", "open-weight", "オープンソース", "オープンモデル",
    ]),
    ("エージェント", 1, ["agent", "agentic", "computer use", "MCP", "エージェント"]),
    ("画像・動画・音声", 1, [
        "image generation", "video generation", "text-to-video", "text-to-image", "multimodal",
        "speech", "voice", "画像生成", "動画生成", "音声", "マルチモーダル",
    ]),
    ("ロボット・半導体", 1, ["robot", "humanoid", "GPU", "chip", "ロボット", "半導体", "チップ"]),
    ("主要AI企業", 2, [
        "OpenAI", "Anthropic", "DeepMind", "Meta AI", "Mistral", "DeepSeek", "NVIDIA", "xAI",
        "GPT", "Claude", "Gemini", "Llama", "Qwen",
    ]),
]

MONEY = [
    ("副業・稼ぎ方", 3, [
        "副業", "稼ぐ", "稼げる", "稼いだ", "収益化", "収益", "マネタイズ", "月収", "不労所得",
        "side hustle", "make money", "monetize", "monetization", "passive income", "earn",
    ]),
    ("学生向け", 2, ["大学生", "学生", "インターン", "奨学", "学割", "students", "college students", "internship"]),
    ("コンテスト・賞金", 3, [
        "ハッカソン", "コンテスト", "賞金", "アワード", "hackathon", "competition", "prize", "bounty",
        "grant", "Kaggle",
    ]),
    ("起業・スタートアップ", 1, [
        "起業", "スタートアップ", "資金調達", "創業", "startup", "founder", "raises", "funding",
        "seed round", "Series A", "Y Combinator", "indie hacker", "bootstrapped", "ARR", "MRR",
        "revenue",
    ]),
    ("個人開発", 2, [
        "個人開発", "作ってみた", "作りました", "リリースしました", "ノーコード", "ローコード",
        "no-code", "nocode", "side project", "I built", "I made", "SaaS", "solo",
    ]),
    ("仕事・案件", 2, [
        "フリーランス", "案件", "受託", "クラウドソーシング", "ランサーズ", "クラウドワークス", "ココナラ",
        "freelance", "Upwork", "Fiverr",
    ]),
    ("無料で使える", 1, ["無料", "無償", "free tier", "free credits", "for free", "discount"]),
    ("効率化・活用術", 1, [
        "業務効率化", "効率化", "自動化", "活用術", "活用法", "使い方", "時短", "automation",
        "productivity", "how to use", "tips",
    ]),
    ("スキル・キャリア", 1, [
        "資格", "スキル", "キャリア", "就活", "転職", "求人", "career", "hiring", "jobs", "course",
    ]),
]

# 新しいブラウザ・AIサービス・ハードウェア・ガジェット・アプリ
GEAR = [
    ("ブラウザ", 3, [
        "browser", "Chrome", "Firefox", "Safari", "Brave", "Vivaldi", "Microsoft Edge", "Arc browser",
        "Dia browser", "ChatGPT Atlas", "Perplexity Comet", "Opera Neon", "ブラウザ", "拡張機能",
    ]),
    ("AIデバイス", 3, [
        "AI device", "AI PC", "Copilot+ PC", "AI glasses", "smart glasses", "AI phone", "AIデバイス",
        "AIスマホ", "AIグラス", "スマートグラス",
    ]),
    ("ハードウェア", 3, [
        "smartphone", "iPhone", "Pixel", "Galaxy", "iPad", "MacBook", "laptop", "wearable", "headset",
        "Vision Pro", "earbuds", "smartwatch", "Snapdragon", "RTX", "NPU", "スマホ", "スマートフォン",
        "ノートPC", "パソコン", "タブレット", "ウェアラブル", "イヤホン", "スマートウォッチ",
    ]),
    ("ガジェット", 3, [
        "gadget", "camera", "drone", "game console", "PlayStation", "Xbox", "Nintendo Switch", "Steam Deck",
        "e-reader", "Kindle", "smart home", "robot vacuum", "keyboard", "gaming monitor", "4K monitor",
        "smart speaker", "Bluetooth speaker", "headphones",
        "power bank", "charger", "action camera", "GoPro", "Meta Quest", "ガジェット", "カメラ", "ドローン",
        "ゲーム機", "電子書籍リーダー", "スマートホーム", "スマート家電", "ロボット掃除機", "キーボード",
        "モニター", "スピーカー", "ヘッドホン", "モバイルバッテリー", "充電器", "家電",
    ]),
    ("面白ITグッズ", 3, [
        "USB hub", "docking station", "desk setup", "desk gadget", "desk display", "便利ガジェット", "面白ガジェット",
        "USBハブ", "ドッキングステーション", "ガジェットポーチ", "トラッカー", "AirTag", "スマートリング",
        "smart ring", "ボイスレコーダー", "AIレコーダー", "翻訳機", "プロジェクター", "projector", "電子ペーパー",
        "小型PC", "ミニPC", "mini PC", "マウス", "mechanical keyboard",
    ]),
    # クラファンの記事は機器以外（映画・グッズなど）も多いので、これだけでは「ガジェットの記事」とみなさない
    ("クラウドファンディング", 1, [
        "crowdfunding", "Kickstarter", "Indiegogo", "クラウドファンディング", "クラファン", "Makuake", "マクアケ",
        "GREEN FUNDING", "CAMPFIRE",
    ]),
    ("新しいアプリ・サービス", 2, [
        "app", "new feature", "beta", "waitlist", "now available", "available now", "extension",
        "アプリ", "ベータ", "提供開始", "サービス開始", "新サービス", "新機能",
    ]),
    ("レビュー・使ってみた", 1, ["review", "hands-on", "tested", "レビュー", "使ってみた", "試してみた", "実機"]),
]

# 取得元の分類（feeds.toml の category）による加点
CATEGORY_BONUS = {
    "tech": {"論文": ("研究・論文", 1), "公式発表": ("公式発表", 3)},
    "money": {"ツール": ("新ツール・サービス", 1), "ビジネス": ("起業・スタートアップ", 1)},
    "gear": {"ツール": ("新しいアプリ・サービス", 1), "新製品": ("新製品", 1)},
}
# feeds.toml で theme = "money" などと指定した取得元への加点
FEED_THEME_BONUS = 2
# この点数以上の記事をテーマのページに載せる
THRESHOLD = 3

DIGEST_LENGTH = 140


def compile_keyword(keyword: str) -> re.Pattern:
    if not keyword.isascii():
        return re.compile(re.escape(keyword))
    # 英語は単語全体で一致させる（"intern" が "international" に一致しないように）。複数形などの語尾は許す
    pattern = r"(?<![A-Za-z])" + re.escape(keyword) + r"(?:s|es|d|ed|ing)?(?![A-Za-z])"
    flags = 0 if keyword.isupper() and len(keyword) <= 4 else re.IGNORECASE
    return re.compile(pattern, flags)


def compile_groups(groups):
    return [(label, points, [compile_keyword(k) for k in keywords]) for label, points, keywords in groups]


THEMES = {"tech": compile_groups(TECH), "money": compile_groups(MONEY), "gear": compile_groups(GEAR)}

# 要約から除く定型文
NOISE_RES = [
    re.compile(r"^arXiv:\S+\s+Announce Type:\s*\S+\s*(Abstract:)?\s*", re.IGNORECASE),
    re.compile(r"submitted by\s+/u/\S+.*$", re.IGNORECASE),
    re.compile(r"\[link\]|\[comments\]"),
    re.compile(r"The post .* appeared first on .*$"),
    re.compile(r"Continue reading.*$", re.IGNORECASE),
]
SENTENCE_RE = re.compile(r"(?<=[。！？!?])\s*|(?<=[a-z0-9)]\.)\s+")


def score(item: dict, theme: str, feed_theme: str | None) -> tuple[int, list[str]]:
    text = f"{item['title']} {item['summary']}"
    total, reasons = 0, []
    for label, points, patterns in THEMES[theme]:
        if any(p.search(text) for p in patterns):
            total += points
            reasons.append(label)
    bonus = CATEGORY_BONUS[theme].get(item["category"])
    if bonus:
        total += bonus[1]
        if bonus[0] not in reasons:
            reasons.append(bonus[0])
    if feed_theme == theme:
        total += FEED_THEME_BONUS
    return total, reasons


def digest(item: dict) -> str:
    text = item["summary"].rstrip("…")
    for r in NOISE_RES:
        text = r.sub("", text).strip()
    if text.startswith(item["title"]):
        text = text[len(item["title"]):].lstrip(" :：-–—")
    if not text:
        return ""
    result = ""
    for sentence in SENTENCE_RE.split(text):
        if result and len(result) + len(sentence) > DIGEST_LENGTH:
            break
        result = f"{result} {sentence}".strip() if result and sentence[:1].isascii() else result + sentence
        if len(result) >= 60:
            break
    if len(result) > DIGEST_LENGTH:
        result = result[:DIGEST_LENGTH].rstrip() + "…"
    return result


def is_gear_related(item: dict) -> bool:
    """「ツール・ガジェット」のキーワード（アプリ・サービスとレビューを除く）を含むか。"""
    text = f"{item['title']} {item['summary']}"
    return any(
        p.search(text)
        for label, _, patterns in THEMES["gear"] if label in ("ブラウザ", "AIデバイス", "ハードウェア", "ガジェット", "面白ITグッズ")
        for p in patterns
    )


def annotate(item: dict, feed_themes: dict[str, str]) -> dict:
    """ページに表示するための採点結果と要約を付けた記事を返す。"""
    out = dict(item)
    feed_theme = feed_themes.get(item["source"])
    out["themes"] = {}
    for theme in THEMES:
        points, reasons = score(item, theme, feed_theme)
        if points >= THRESHOLD:
            out["themes"][theme] = {"score": points, "reasons": reasons}
    out["digest"] = digest(item)
    return out
