# AI情報まとめ

AIに関する最新情報を、日本と海外の約70か所から自動で集めて、1枚のWebページにまとめるツールです。

- **2時間ごと＋毎日深夜0時に自動で更新**されます。パソコンを起動しておく必要はありません（GitHub が代わりに動かします）。
- AIのAPIなど、料金のかかるサービスは使っていません。各サイトが公開している「RSS」（新着記事の一覧）を読み込むだけです。

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
| 論文 | arXiv、Hugging Face Daily Papers |

## ページの見方

- **技術の進歩**タブ：新しいAIモデル・研究成果・性能向上などの記事を、注目度の高い順に表示します
- **収益化のヒント**タブ：副業・個人開発・起業・学生向けコンテストなど、大学生がAIで収益につなげるヒントになりそうな記事を表示します
- **すべての記事**タブ：集めたすべての記事を新しい順に表示します
- テーマのタブでは、記事の要点を短く抜き出した要約と、選ばれた理由（「新モデル・新機能」「副業・稼ぎ方」など）を表示します。
  判定はAIではなくキーワードで行っています。基準は `collector/themes.py` で変更できます
- **検索**：上の入力欄にキーワードを入れると絞り込めます（例：`画像生成`、`Claude`）
- **分類ボタン**：「ニュース」「公式発表」などで絞り込めます
- **言語**：「日本語のみ」「海外（日本語以外）」などに切り替えられます
- **NEW**：前回ページを開いてから増えた記事に付きます
- **日本語に翻訳して読む**：海外の記事は、このリンクから Google 翻訳で日本語にして読めます

## ページを公開する設定（最初に1回だけ）

1. https://github.com/asai-shu/info/settings/pages を開く
2. 「Build and deployment」の **Source** を「**GitHub Actions**」に変える
3. https://github.com/asai-shu/info/actions を開き、左の「AI情報を収集」→ 右の **Run workflow** ボタン →緑の **Run workflow** を押す
4. 3〜5分ほど待ってから **https://asai-shu.github.io/info/** を開く

あとは2時間ごとに自動で新しい記事が追加されます。スマホのホーム画面に追加しておくと便利です。

## 取得元を増やす・減らす

`feeds.toml` を編集します（GitHub の画面上で鉛筆マークを押せば編集できます）。書き方はファイルの先頭に書いてあります。

---

### 開発者向けメモ

- `collector/collect.py`：収集プログラム（Python 3.11 以上、標準ライブラリのみ）。`python3 collector/collect.py` で `docs/index.html` が生成されます
- `collector/template.html`：ページのデザイン
- `data/items.json`：集めた記事（直近14日分）。自動実行のたびに更新されてコミットされます
- `.github/workflows/collect.yml`：2時間ごとの自動実行。Pages が未設定でも収集・保存は成功します
- 同じサイトへは6秒（Redditは30秒）間隔で取得し、429・5xx のときだけ再試行します
