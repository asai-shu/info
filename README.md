# AI情報まとめ

AIに関する最新情報を、日本と海外の約70か所から自動で集めて、1枚のWebページにまとめるツールです。

- **2時間ごと＋毎日深夜0時に自動で更新**されます。パソコンを起動しておく必要はありません（GitHub が代わりに動かします）。
- 記事集めには、AIのAPIなどの有料サービスを使っていません。各サイトが公開している「RSS」（新着記事の一覧）を読み込むだけです。
- 記事選び・翻訳・要約、需要リサーチ、おすすめは、**Claude が GitHub の上で自動で**行います（下の「Claudeによる更新」を参照。最初に Claude の鍵の登録が必要です）。

## 集めている情報

| 分類 | 主な取得元 |
| --- | --- |
| ニュース（日本） | Googleニュース、ITmedia AI+、GIGAZINE、Publickey、AINOW |
| ニュース（海外） | Google News（米国・英国）、TechCrunch、The Verge、WIRED、Ars Technica、MIT Technology Review など |
| ニュース（その他の国） | 台湾、中国、韓国、ドイツ、フランス、中南米のニュース |
| 公式発表 | OpenAI、Google、DeepMind、Microsoft、NVIDIA、AWS、Apple、Hugging Face |
| 専門家 | Simon Willison、Ethan Mollick、Latent Space、Import AI など |
| 技術記事 | Zenn、Qiita、note |
| 話題 | はてなブックマーク、Hacker News、Reddit、Lobsters |
| ビジネス | AIスタートアップ・資金調達のニュース |
| ツール | Product Hunt、GitHub で人気のプロジェクト |
| 新製品 | Googleニュース（AIブラウザ・ガジェット）、The Verge、Engadget、9to5Google、9to5Mac、Chrome・Firefoxの公式ブログ、ギズモード・ジャパン、ITmedia Mobile・PC USER、家電Watch、AV Watch、GetNavi web、ROOMIE、Yanko Design |
| 面白ITグッズ | クラウドファンディング（Makuake・Kickstarter など）や便利グッズのニュース |
| 論文 | arXiv、Hugging Face Daily Papers |
| 需要の種 | Reddit（r/SomebodyMakeThis・r/smallbusiness・r/Entrepreneur・r/SaaS）、Ask HN、Googleニュース（人手不足・中小企業の困りごと・個人開発の売上）、note（個人開発） |

## ページの見方

- **技術の進歩**タブ：新しいAIモデル・研究成果・性能向上などの記事を、注目度の高い順に表示します
- **収益化のヒント**タブ：副業・個人開発・起業・学生向けコンテストなど、大学生がAIで収益につなげるヒントになりそうな記事を表示します
- **ツール・ガジェット**タブ：新しいブラウザ、AIサービス、アプリ、スマホやパソコン、イヤホン・カメラ・ゲーム機などのガジェットの情報を表示します
- **すべての記事**タブ：集めたすべての記事を新しい順に表示します
- **おすすめ**（右上のボタン）：**PC**・**ガジェット**（AIグラスやAI搭載USBハブなどの「面白ITグッズ」も）・**ソフトウェア**（AIサービス・アプリ）・**その他**（充電器・SSD・ルーター）の4ページで、それぞれ「最高性能（予算度外視）」と「大学生向け（手の届く価格）」に分けて紹介します。価格と根拠のリンク付きで、毎月1日にClaudeが調べ直します
- **需要リサーチ**（右上のボタン）：Webサービスで収益を上げるための調査ページです。「**稼げる分野**」（今お金が流れている分野）・「**需要の種**」（困っている人がいそうな所）・「**嗅ぎつけ方**」（需要を見つける・確かめる方法）・「**本**」の4つのタブがあり、根拠のリンク付きです。毎週月曜に Claude が調べ直します。右上の「調べ直す」からすぐ調べ直すこともできます
- テーマのタブの一番上には「**Claudeが選んだ注目記事**」が、日本語のタイトル・要約・ポイント（収益化のヒントでは「活かし方」、ツール・ガジェットでは「使いどころ」）付きで表示されます
- その下の「キーワードで選んだその他の記事」は、キーワードによる自動判定です。基準は `collector/themes.py` で変更できます
- **検索**：上の入力欄にキーワードを入れると絞り込めます（例：`画像生成`、`Claude`）
- **分類ボタン**：「ニュース」「公式発表」などで絞り込めます
- **言語**：「日本語のみ」「海外（日本語以外）」などに切り替えられます
- **NEW**：前回ページを開いてから増えた記事に付きます
- **日本語に翻訳して読む**：海外の記事は、このリンクから Google 翻訳で日本語にして読めます

## Claudeによる更新（パソコン不要）

注目記事・需要リサーチ・おすすめは、Claude が GitHub の上で自動で調べて更新します（`.github/workflows/claude.yml`）。パソコンを起動しておく必要はありません。

| 更新するもの | 自動で動く時間（日本時間） | 手順の中身 |
| --- | --- | --- |
| 注目記事（技術の進歩・収益化のヒント・ツール・ガジェット） | 毎朝 7:23 | `.claude/skills/curate/SKILL.md` |
| 需要リサーチ（稼げる分野・需要の種・嗅ぎつけ方・本） | 毎週月曜 6:37 | `.claude/skills/demand/SKILL.md` |
| おすすめ（PC・ガジェット・ソフトウェア・その他） | 毎月1日 10:41 | `.claude/skills/gear-guide/SKILL.md` |

**最初に1回だけ：Claude の鍵を登録する**

どちらか1つを登録します。

- **APIキー（スマホのブラウザだけでできる）**：https://console.anthropic.com でAPIキーを作り、使った分だけ料金がかかります。金額は調べる量で変わり、毎日の注目記事も含めると月に数千円になることもあります。Console で月の上限額を設定しておくと安心です
- **Pro・Max プランのトークン（追加料金なし、プランの使用量の範囲内）**：Claude Code が入ったパソコンで一度だけ `claude setup-token` を実行して、表示されたトークンを使います

登録のしかた：

1. https://github.com/asai-shu/info/settings/secrets/actions を開く
2. **New repository secret** を押す
3. Name に `ANTHROPIC_API_KEY`（APIキーの場合）または `CLAUDE_CODE_OAUTH_TOKEN`（トークンの場合）、Secret に鍵を貼り付けて保存する

**今すぐ更新したいとき**

需要リサーチのページ右上の「**調べ直す**」を押す（または https://github.com/asai-shu/info/actions/workflows/claude.yml を開く）→ **Run workflow** → 更新するもの（demand / curate / gear-guide）を選んで緑の **Run workflow** を押します。10〜30分ほどでページに反映されます。

Claude Code（デスクトップ版など）で `/curate`・`/demand`・`/gear-guide` と頼んでも、同じ手順で更新できます。

## ページを公開する設定（最初に1回だけ）

1. https://github.com/asai-shu/info/settings/pages を開く
2. 「Build and deployment」の **Source** を「**GitHub Actions**」に変える
3. https://github.com/asai-shu/info/actions を開き、左の「AI情報を収集」→ 右の **Run workflow** ボタン →緑の **Run workflow** を押す
4. 3〜5分ほど待ってから **https://asai-shu.github.io/info/** を開く

あとは2時間ごとに自動で新しい記事が追加されます。スマホのホーム画面に追加しておくと便利です。

### スマホのホーム画面にアイコンを置く

記事一覧（青いアイコン）と需要リサーチ（緑のアイコン）を、別々のアイコンとして置けます。

- **iPhone（Safari）**：開きたいページ（記事一覧は https://asai-shu.github.io/info/ 、需要リサーチは https://asai-shu.github.io/info/demand.html ）を開く → 下の共有ボタン（□に↑）→「ホーム画面に追加」→「追加」
- **Android（Chrome）**：同じページを開く → 右上の︙ →「ホーム画面に追加」（または「アプリをインストール」）→「追加」。記事一覧のアイコンを長押しすると「需要リサーチ」「おすすめ」へ直接飛ぶこともできます

## 取得元を増やす・減らす

`feeds.toml` を編集します（GitHub の画面上で鉛筆マークを押せば編集できます）。書き方はファイルの先頭に書いてあります。

---

### 開発者向けメモ

- `collector/collect.py`：収集プログラム（Python 3.11 以上、標準ライブラリのみ）。`python3 collector/collect.py` で `docs/index.html` が生成されます
- `collector/template.html`：ページのデザイン
- `data/items.json`：集めた記事（直近14日分）。自動実行のたびに更新されてコミットされます
- `data/gear_guide.json`：おすすめ機材ページのデータ。Claude Code（`/gear-guide`）が Web 検索で価格を確認して更新し、`collector/gear_template.html` から区分ごとに `docs/gear-pc.html` などが作られます
- `data/demand.json`：需要リサーチページのデータ。Claude Code（`/demand`）が Web 検索と分類「需要の種」の記事をもとに更新し、`collector/demand_template.html` から `docs/demand.html` が作られます。書式チェックは `python3 collector/curation.py check-demand`
- `data/curated.json`：Claude Code（`/curate`）が選んだ注目記事と日本語要約。`collector/curation.py` で候補の一覧化（1つの取得元から最大8件）と書式チェックを行います
- `.github/workflows/claude.yml`：Claude による更新（claude-code-action）。各 SKILL.md の手順どおりに data/ のファイルを更新して push し、そのあと collect.yml を動かしてページを作り直します
- `.github/workflows/collect.yml`：2時間ごとの自動実行。Pages が未設定でも収集・保存は成功します
- 同じサイトへは6秒（Redditは30秒）間隔で取得し、429・5xx のときだけ再試行します
