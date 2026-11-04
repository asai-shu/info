---
name: translate
description: 集めた外国語（英語・中国語・韓国語など）の記事のタイトルと要約を、自然な日本語に訳して data/translations.json に保存し、GitHub に反映する。あわせて、持ち主がブックマークした記事の本文を日本語に訳して Supabase に保存する。ユーザーが「/translate」「英語の記事を訳して」と言ったときや、毎晩の定期実行で使う。
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

## ブックマークした記事の本文の翻訳（先に行う）

記事一覧の☆でブックマークされた記事は、本文まで日本語に訳す。保存先は Supabase（プロジェクト university-companion、project_id: jmsxajybjtvgxummvpps）の表 `info_bookmarks`。読み書きは Supabase コネクタの execute_sql で行う。ほかの表には触れない。削除や表の作り替えはしない（UPDATE だけ）。

1. まだ訳していないブックマークを、古い順に最大10件読む
   ```sql
   select id, item_id, title, link, source, lang, title_ja from info_bookmarks where translated_at is null order by created_at limit 10;
   ```
2. 1件ずつ、記事の本文を読む（WebFetch。使えなければ web-fetch エージェントに「本文をそのまま抜き出して」と頼む）
3. 本文を日本語に訳す
   - 見出し・段落の区切りを保ち、段落の間は空行にする。広告・関連記事・コメント欄などは除く
   - 長い記事（目安：日本語で6,000字を超える）は、要点を落とさずに縮めた抄訳にしてよい。その場合は translation_note に「長い記事のため抄訳です」と書く
   - 原文にないことを足さない。専門用語は短く言い換えるか、かっこで補う
   - `title_ja` が空なら、タイトルも訳す
4. 保存する（文字列はドル記号の引用 `$t$…$t$` で囲むと、引用符のエスケープがいらない）
   ```sql
   update info_bookmarks set title_ja = coalesce(title_ja, $t$…$t$), translation = $t$…$t$, translation_note = null, translated_at = now() where id = '…';
   ```
   - 日本語の記事：translation は null のまま、translation_note に「日本語の記事のため、翻訳はしていません」と書いて translated_at = now()
   - 本文が読めなかった（会員限定・取得できない・動画だけなど）：translation は null、translation_note に理由（例「会員限定の記事で、本文を読めませんでした」）を書いて translated_at = now()
5. 訳した件数を最後の報告に含める（「ブックマーク○件」）

## 守ること

- リポジトリでは `data/translations.json` 以外のファイルは変更しない（ブックマークの訳は Supabase に保存し、公開ページには載せない）
- AI の API や外部の翻訳サービスは使わない（訳すのはあなた自身）
- 本文を取りに行くのは、ブックマークされた記事だけ（それ以外はタイトルと要約だけを訳す）
