---
name: demand
description: 需要リサーチのページ（data/demand.json）を最新の情報に更新する。「稼げる分野」「需要の種」「嗅ぎつけ方」「本」の4つのタブを、集めた記事（分類「需要の種」）と Web 検索で調べ直し、GitHub に反映する。ユーザーが「/demand」「需要リサーチを更新して」「稼げる分野を調べ直して」などと言ったときや、定期実行で使う。
---

# 需要リサーチの更新

アプリの「需要リサーチ」ページ（demand.html）は `data/demand.json` から作られる。タブは4つ。
- 稼げる分野（markets）：今どんな分野にお金が流れているか。category は「海外の個人開発」「日本」など
- 需要の種（seeds）：困っている人がいそうな所。大学生が一人で作れる規模のサービスの仮説
- 嗅ぎつけ方（methods）：需要を見つける方法（category「見つける」）と、本物か確かめる方法（category「確かめる」）
- 本（books）：需要の見つけ方・確かめ方を学べる本。category「まず読む」「次に読む」など、読む順に並べる

あなた（Claude）の仕事は、新しい情報を調べて内容を正確で新しく保つこと。読み手は、Webサービスで収益を上げたい日本の大学生。専門用語は避けるか、短く言い換える。

## いちばん大事なこと：推測で書かない

- 数字・書名・出版社・発売年・URL は、**この作業中に Web 検索や記事データで確認できたものだけ**を書く。記憶やURLの形からの推測は禁止
- 本は、著者・出版社・日本語版の有無を検索で確かめてから載せる。確かめられないときは載せない
- まとめ記事や宣伝目的の記事の数字は、`caution` に「検証されていない」ことを書く。政府統計や調査会社の一次情報があればそちらを優先する
- 需要の種は「仮説」として書き、根拠にした記事・投稿を `sources` に入れる

## 手順

1. `git pull --rebase origin ccr-9eb32590-esny4k`
2. 現在の `data/demand.json` を読む
3. 集めた「需要の種」の記事・投稿を一覧にする（Reddit の「こんなツールがほしい」、Ask HN、人手不足・中小企業の課題のニュース、個人開発の売上の記事など）
   ```sh
   python3 collector/curation.py candidates --category 需要の種 --hours 336 --limit 200 --per-source 25
   ```
   収益化のヒントの記事も参考にする
   ```sh
   python3 collector/curation.py candidates --category 収益化 --hours 168 --limit 80
   ```
4. 一覧から、繰り返し出ている困りごと・「お金を払ってでもほしい」という声・売上が出ている事例を拾う。必要なら WebFetch で本文を確認してよい（全体で10件程度まで）
5. WebSearch で調べ直す（standard で足りなければ extended）。最低でも次を調べる
   - 海外の個人開発・小さなSaaSで今稼げている分野（例：「micro SaaS trends 月 年」「bootstrapped SaaS profitable niche 年」）
   - 日本の需要（例：「中小企業白書 最新」「人手不足 業種 調査 最新」「個人開発 収益 事例 年」）
   - 需要の見つけ方・確かめ方の新しい方法やツール
   - 本：新刊、日本語版の発売、評価の高い本（例：「顧客インタビュー 本」「ニーズ 発見 本 新刊」）
6. `data/demand.json` を更新する（書式は今のファイルと同じ）
   - `updated` を今日の日付（YYYY-MM-DD）に、`overview` を今回のまとめ（3〜4文）に書き換える
   - 各項目：`section`（markets / seeds / methods / books）、`category`、`title`、`sub`（一言の補足。本は「著者、出版社（年）」）、`body`（2〜4文）、`notes`（`label` と `text` の組。markets は「大学生の勝ち筋」、seeds は「誰が困っている」「作るなら」「確かめ方」、methods は「やり方」など、books は「読みどころ」）、`caution`（注意点。なければ空文字）、`sources`（確認に使ったページ。title と url。1項目に1〜3件）
   - 目安の件数：markets 6〜10件、seeds 5〜10件、methods 6〜10件、books 4〜8冊
   - 古くなった情報は消すか書き換える。根拠が新しい情報で否定されたものは残さない
   - 需要の種は、前回からの入れ替えを恐れない。ただし、根拠が今も有効な種は残してよい
   - `changes` の先頭に `{"date": "今日", "summary": "何を足し・消し・直したか（1文）"}` を足す。古いものは10件まで残す
7. 書式を確認する。NG が出たら直して、OK になるまで繰り返す
   ```sh
   python3 collector/curation.py check-demand
   ```
8. GitHub に送る（ページは数分後に自動で更新される）
   ```sh
   git add data/demand.json
   git commit -m "需要リサーチを更新（Claude による調査）"
   git pull --rebase origin ccr-9eb32590-esny4k
   git push origin HEAD:ccr-9eb32590-esny4k
   ```
9. `overview` と、新しく入れた需要の種・本だけを短く報告する

## 守ること

- `data/demand.json` 以外のファイルは変更しない
- AI の API や有料サービスは使わない
- 宣伝やアフィリエイトのリンクは付けない
- 「誰でも簡単に月100万円」のような怪しい情報は載せない
