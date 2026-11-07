"""保存した記事の HTML から、本文（見出し・段落・箇条書き）だけを取り出して表示する。

ブックマークした記事の本文を訳すときに使う（/translate スキル）。
使い方: python3 -I collector/article_text.py ページ.html [最大文字数]
"""
import sys
from html.parser import HTMLParser

SKIP = {"script", "style", "noscript", "nav", "footer", "aside", "form", "svg", "button", "header", "iframe"}
BLOCK = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "p": "", "li": "- ", "blockquote": "> ", "pre": ""}


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.scope = {"article": [], "main": [], "body": []}
        self.inside = {"article": 0, "main": 0, "body": 0}
        self.block = None
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        if tag in self.inside:
            self.inside[tag] += 1
        if tag in BLOCK and not self.skip:
            self.flush()
            self.block = tag
        if tag == "br" and self.block:
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self.skip:
            self.skip -= 1
        if tag == self.block:
            self.flush()
        if tag in self.inside and self.inside[tag]:
            self.inside[tag] -= 1

    def handle_data(self, data):
        if self.block and not self.skip:
            self.buf.append(data)

    def flush(self):
        if self.block:
            text = " ".join("".join(self.buf).split())
            if text:
                line = BLOCK[self.block] + text
                for name, depth in self.inside.items():
                    if depth:
                        self.scope[name].append(line)
        self.block = None
        self.buf = []


def extract(html: str) -> str:
    p = Extractor()
    p.feed(html)
    p.flush()
    # 本文らしい範囲（article → main → body）のうち、十分な長さがある最初のものを使う
    for name in ("article", "main", "body"):
        text = "\n\n".join(p.scope[name])
        if len(text) > 500:
            return text
    return "\n\n".join(p.scope["body"])


if __name__ == "__main__":
    html = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    print(extract(html)[:limit])
