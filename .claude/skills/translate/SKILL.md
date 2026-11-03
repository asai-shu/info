---
name: translate
description: 集めた外国語（英語・中国語・韓国語など）の記事のタイトルと要約を、自然な日本語に訳して data/translations.json に保存し、GitHub に反映する。ユーザーが「/translate」「英語の記事を訳して」と言ったときや、毎晩の定期実行で使う。
---

# 外国語の記事の翻訳

記事一覧（https://asai-shu.github.io/info/）には、海外の記事が毎日1,000件ほど入る。機械翻訳では意味が分かりにくいので、あなた（Claude）がタイトルと要約を日本語に訳す。
訳は `data/translations.json` に保存し、ページでは訳したタイトルを見出しにして、原文のタイトルを小さく添えて表示する（「Claude訳」の印が付く）。

読み手は **AIに詳しくない日本の大学生**。

## 手順

1. 最新のデータを取り込む
   ```sh
   git pull --rebase origin ccr-9eb32590-esny4k
   ```
2. まだ訳していない記事を一覧にする（「技術の進歩」に載りやすい記事 → 新しい記事の順。1行に1記事の JSON）
   ```sh
   python3 collector/curation.py untranslated --limit 300
   ```
   使用量を控えたい日は `--limit` を減らしてよい（例：150）。訳しきれなかった記事は次の回に回る。
3. 1件ずつ訳す
   - `title`：日本語のタイトル。直訳ではなく、意味が一目で分かる自然な日本語にする。製品名・会社名・モデル名は原文のまま（例：Claude、GPT-6.1 Terra）。50字程度まで
   - `summary`：要約を日本語で1〜2文に。原文の要約が途中で切れていても、書かれている範囲だけを訳す。**原文にないことを足さない**。要約が空の記事は空文字 `""` にする
   - 専門用語は短く言い換えるか、かっこで補う（例：「オープンウェイト（中身が公開されたモデル）」）
   - Reddit などの投稿で、宣伝・質問だけ・意味のない投稿も、内容のとおりに短く訳す（勝手に省かない）
4. `data/translations.json` に追記する。形は次のとおりで、**1件1行**にする（既存の訳は消さない）
   ```json
   {
   "items": {
   "9f8f59b5f3951029": {"title": "…", "summary": "…"},
   "6c7aed5397a854e1": {"title": "…", "summary": "…"}
   }
   }
   ```
   追記は Python で行うと安全（`json.load` → 辞書に足す → `curation.py` の `dump_translations` で書き出す）。
5. 書式を確かめる（保存期間を過ぎて消えた記事の訳も、ここで自動で捨てられる）
   ```sh
   python3 collector/curation.py check-translations
   ```
6. GitHub に送る（ページは数分後に自動で作り直される）
   ```sh
   git add data/translations.json
   git commit -m "外国語の記事を翻訳（Claude による翻訳）"
   git pull --rebase origin ccr-9eb32590-esny4k
   git push origin HEAD:ccr-9eb32590-esny4k
   ```
7. 訳した件数と、まだ訳していない件数を1行で報告する

## 守ること

- `data/translations.json` 以外のファイルは変更しない
- AI の API や外部の翻訳サービスは使わない（訳すのはあなた自身）
- 記事の本文を取りに行かない（タイトルと要約だけを訳す）
