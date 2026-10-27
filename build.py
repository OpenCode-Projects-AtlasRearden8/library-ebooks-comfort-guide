#!/usr/bin/env python3
"""Build the static HTML site for The Library Ebooks Comfort Guide.

Standard library only: no installs, no network, no API keys, works offline.
Output is deterministic — rebuilds are byte-identical (no timestamps).

Usage:
  python3 build.py                    build docs/ into site/
  python3 build.py --out DIR          build somewhere else
  python3 build.py --check            lint docs (links, anchors, policy)
  python3 build.py --from-md FILE     print one Markdown file as HTML
  python3 build.py --serve [PORT]     build, then preview at localhost

Markdown subset (house style, see docs/):
  headings (#/##/###), paragraphs, **bold**, *italic*, `code`,
  [links](other-chapter.md) with optional #anchors, https links,
  bullet lists (- item), numbered lists (N.), checkbox lists (- [ ]),
  tables (| a | b | with | --- | separator), blockquotes (> text),
  definition lists (term on one line, then ": definition" lines),
  fenced code blocks (```), horizontal rules (---).
"""

from __future__ import annotations

import argparse
import html
import http.server
import re
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DEFAULT_OUT = ROOT / "site"

BOOK_TITLE = "The Library Ebooks Comfort Guide"
BOOK_TAGLINE = "Free library books on any device, without the headache"
BOOK_OWNER = "Asdale Dynamics, LLC"
HUB_URL = "https://dylanasdale.github.io/"
COMPANION = "Free Reading for Less"

FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
    "%3Crect width='100' height='100' rx='18' fill='%230e6f5f'/%3E"
    "%3Crect x='18' y='28' width='64' height='44' rx='4' fill='none' "
    "stroke='%23fbf9f4' stroke-width='6'/%3E"
    "%3Cpath d='M50 28v44M32 40h14M32 48h14M56 40h12M56 48h12' "
    "stroke='%23fbf9f4' stroke-width='4' fill='none'/%3E"
    "%3C/svg%3E"
)

FOOTER = (
    "Explained like a friend would: plain English, no condescension. Built "
    "and maintained by Asdale Dynamics, LLC — MIT licensed. No accounts, no "
    f"tracking, no network needed once built. More beginner guides at "
    f"<a href=\"{HUB_URL}\">dylanasdale.github.io</a>."
)

# One-line blurb per chapter, shown on chapter pages and the landing page,
# and used as the per-page meta description. Keys are docs/ filenames.
SUMMARIES = {
    "00-start-here.md": (
        "The quick truth about free library reading, what this guide "
        "covers, and how the pieces fit together."),
    "01-your-library-card.md": (
        "Getting a card four different ways, what the number and PIN are "
        "for, and keeping them safe."),
    "02-libby-step-by-step.md": (
        "Install Libby, sign in, borrow, read, manage the shelf — the whole "
        "app, one walk-through."),
    "03-hoopla-step-by-step.md": (
        "The no-waiting service: instant borrows, monthly allowances, Flex, "
        "BingePasses, and KIDS mode."),
    "04-send-to-kindle.md": (
        "The library-loan route to a Kindle, why it's U.S.-only, and the "
        "re-delivery fix for every \"it won't show up\" moment."),
    "05-holds-and-waitlists-honestly.md": (
        "Why lines exist, why they lurch, what's under your control, and "
        "what quietly shortens every wait."),
    "06-renewals-and-multiple-cards.md": (
        "Renewing without stress, returning early, and stacking legitimate "
        "cards from more than one library."),
    "07-audiobooks-magazines-and-more.md": (
        "Audiobook controls that save commutes, current magazines, comics, "
        "music, and hoopla's streaming extras."),
    "08-when-things-go-wrong.md": (
        "A symptom-to-fix table for the small failures — plus what to say "
        "when you call the library."),
    "09-reading-comfortably.md": (
        "Large text, OpenDyslexic, line spacing, dark mode, audio speeds: "
        "comfort settings on every reader."),
    "10-device-checklists.md": (
        "Printable, checkbox setup lists for phone, tablet, Kindle, Kobo, "
        "laptop, TV, car, and rescue phones."),
    "11-glossary.md": (
        "Every term in the book, defined plainly, from BingePass to "
        "Waitlist."),
}

STYLE = """\
:root {
  --paper: #fbf9f4; --panel: #ffffff; --ink: #232a31; --muted: #67707a;
  --line: #e3ddd0; --accent: #0e6f5f; --accent-soft: #e4f0ec;
  --gold: #a26d1e; --code-bg: #2a2621; --code-ink: #f3ece1;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; color: var(--ink); background: var(--paper);
  font: 17px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        Helvetica, Arial, sans-serif;
}
a { color: var(--accent); text-underline-offset: 2px; }
a:hover { text-decoration-thickness: 2px; }
.wrap { max-width: 46rem; margin: 0 auto; padding: 0 1.2rem; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas,
               "Liberation Mono", monospace;
  font-size: 0.88em; background: #efeadf; padding: .1em .35em;
  border-radius: .3em;
}
pre {
  background: var(--code-bg); color: var(--code-ink); padding: 1rem 1.2rem;
  border-radius: .6rem; overflow-x: auto; line-height: 1.5;
}
pre code { background: none; color: inherit; padding: 0; font-size: .92em; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: .8rem; top: .8rem; background: #fff; padding: .5rem .8rem;
  border-radius: .4rem; z-index: 10; }
header.site { background: var(--accent); color: #fff; padding: .9rem 0; }
header.site .wrap { display: flex; gap: 1rem; align-items: baseline;
  flex-wrap: wrap; }
header.site .brand { color: #fff; font-weight: 700; text-decoration: none;
  letter-spacing: -.01em; }
header.site .brand:hover { text-decoration: underline; }
header.site nav { margin-left: auto; display: flex; gap: 1rem; }
header.site nav a { color: #eef7f4; font-size: .92rem; }
main { padding: 2rem 0 3rem; }
h1 { font-size: 1.9rem; line-height: 1.25; letter-spacing: -.02em;
  margin: 0 0 .4rem; }
.kicker { color: var(--gold); font-size: .85rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: .07em; margin: 0 0 .4rem; }
.intro-muted { color: var(--muted); font-size: 1.02rem; margin-top: .1rem;
  max-width: 42rem; }
h2 { font-size: 1.35rem; margin: 2.2rem 0 .6rem; letter-spacing: -.01em; }
h3 { font-size: 1.08rem; margin: 1.6rem 0 .4rem; }
p { margin: .7rem 0; }
blockquote {
  margin: 1.2rem 0; padding: .85rem 1.1rem; background: var(--accent-soft);
  border-left: 4px solid var(--accent); border-radius: 0 .5rem .5rem 0;
}
blockquote p { margin: .25rem 0; }
ul, ol { margin: .7rem 0; padding-left: 1.4rem; }
li { margin: .3rem 0; }
ul.checklist { list-style: none; padding-left: .2rem; }
ul.checklist li { padding-left: 1.7rem; position: relative; }
ul.checklist li::before {
  content: "\\2610"; position: absolute; left: .1rem; font-size: 1.15rem;
  color: var(--accent);
}
table { border-collapse: collapse; width: 100%; margin: 1.1rem 0;
  font-size: .95rem; }
th, td { border: 1px solid var(--line); padding: .45rem .6rem;
  text-align: left; vertical-align: top; }
th { background: var(--accent-soft); }
tbody tr:nth-child(even) { background: #fdfcf9; }
hr { border: 0; border-top: 1px solid var(--line); margin: 2rem 0; }
dl { margin: 1rem 0; }
dt { font-weight: 700; margin-top: 1.1rem; }
dd { margin: .15rem 0 0 0; }
.pager { display: flex; justify-content: space-between; gap: 1rem;
  margin-top: 2.6rem; border-top: 1px solid var(--line); padding-top: 1rem; }
.pager a { text-decoration: none; font-weight: 600; font-size: .95rem; }
.pager .disabled { color: var(--muted); }
.pager .label { display: block; color: var(--muted); font-size: .78rem;
  font-weight: 400; }
section.onpage { margin: 1.5rem 0 0; padding: .8rem 1rem;
  background: var(--panel); border: 1px solid var(--line);
  border-radius: .6rem; }
section.onpage h2 { margin: 0 0 .4rem; font-size: .8rem; color: var(--muted);
  text-transform: uppercase; letter-spacing: .07em; }
section.onpage ul { list-style: none; margin: 0; padding: 0;
  columns: 2; column-gap: 1.4rem; }
section.onpage li { margin: .15rem 0; }
footer.site { border-top: 1px solid var(--line); background: #f4f1ea;
  color: var(--muted); font-size: .88rem; }
footer.site .wrap { padding: 1.3rem 1.2rem 2rem; }
.hero { background: var(--accent); color: #fff; padding: 2.6rem 0 2.4rem; }
.hero h1 { color: #fff; font-size: 2.1rem; margin: .2rem 0 .6rem; }
.hero p { margin: .3rem 0; max-width: 42rem; opacity: .95; }
.hero .badge { display: inline-block; background: rgba(255,255,255,.15);
  border-radius: 999px; padding: .18rem .75rem; font-size: .8rem;
  margin-top: .9rem; }
.cards { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 1rem; margin: 1.4rem 0 .6rem; }
.card { background: var(--panel); border: 1px solid var(--line);
  border-radius: .7rem; padding: 1rem 1.1rem; display: flex;
  flex-direction: column; gap: .4rem; text-decoration: none;
  color: var(--ink); }
.card:hover { border-color: var(--accent); box-shadow: 0 2px 10px
  rgba(14, 111, 95, .12); }
.card .num { color: var(--gold); font-size: .78rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; }
.card h2 { margin: 0; font-size: 1.06rem; color: var(--accent); }
.card p { margin: 0; color: var(--muted); font-size: .92rem; }
.jump { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: .7rem; margin: 1.1rem 0; }
.jump a { background: var(--accent-soft); border: 1px solid #cfe2dc;
  color: var(--accent); border-radius: .55rem; padding: .6rem .8rem;
  font-size: .95rem; font-weight: 600; text-decoration: none; }
.jump a:hover { border-color: var(--accent); }
h2.rule { border-top: 1px solid var(--line); padding-top: 1.6rem; }
.toc ol { padding-left: 1.3rem; }
.muted { color: var(--muted); font-size: .88rem; }
body.book .chapter { border-top: 2px solid var(--line); margin-top: 3rem;
  padding-top: 1.6rem; }
body.book .chapter:first-of-type { border-top: 0; margin-top: 1rem;
  padding-top: 0; }
@media (max-width: 40rem) {
  section.onpage ul { columns: 1; }
  h1 { font-size: 1.55rem; }
}
@media print {
  header.site, footer.site, .hero, .pager, .skip { display: none; }
  body { background: #fff; font-size: 12pt; }
  a { color: inherit; }
  blockquote, table, li { break-inside: avoid; }
}
"""

CSS_FILENAME = "style.css"
MD_TARGET_RE = re.compile(r'href="([0-9]{2}-[a-z0-9-]+\.md)(#([^"]+))?')


class BuildError(Exception):
    """A problem in the docs that the builder refuses to paper over."""


CODE_FENCE_RE = re.compile(r"^\s*```")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
NUM_LIST_RE = re.compile(r"^(\d+)\.\s+(.*)$")
CHECK_ITEM_RE = re.compile(r"^[-*]\s+\[(?: |x)\]\s+")
BULLET_RE = re.compile(r"^[-*]\s+")
TABLE_SEP_RE = re.compile(r"^\|[\s:|-]*\|?\s*$")
DL_DEF_RE = re.compile(r"^:\s")


# --------------------------------------------------------------------------
# tiny markdown renderer (exactly the subset this manual uses)
# --------------------------------------------------------------------------

def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[\u2019']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def inline(text: str) -> str:
    """Inline markup: escape first, then code, links, bold, italic."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", lambda m: "<code>%s</code>" % m.group(1), out)
    out = re.sub(
        r"\[([^\]]+)\]\(([^()\s]+)\)",
        lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", out)
    return out


def parse_blocks(source: str):
    """Parse the markdown subset into blocks."""
    lines = source.splitlines()
    blocks: list = []
    para: list[str] = []
    i, n = 0, len(lines)

    def flush_para():
        if para:
            blocks.append(("p", " ".join(s.strip() for s in para)))
            para.clear()

    while i < n:
        line = lines[i]
        if not line.strip():
            flush_para()
            i += 1
            continue
        if CODE_FENCE_RE.match(line):
            flush_para()
            buf = []
            i += 1
            while i < n and not CODE_FENCE_RE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            if i >= n:
                raise BuildError("unbalanced ``` fence")
            blocks.append(("pre", "\n".join(buf)))
            i += 1
            continue
        m = HEADING_RE.match(line)
        if m:
            flush_para()
            blocks.append((("h1", "h2", "h3")[len(m.group(1)) - 1],
                           m.group(2).strip()))
            i += 1
            continue
        if re.fullmatch(r"-{3,}", line.strip()) and not para:
            blocks.append(("hr", ""))
            i += 1
            continue
        if line.startswith(">"):
            flush_para()
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            blocks.append(("quote", " ".join(s.strip() for s in buf)))
            continue
        if (line.startswith("|") and i + 1 < n
                and TABLE_SEP_RE.match(lines[i + 1])):
            flush_para()
            rows = []
            while i < n and lines[i].startswith("|"):
                if not TABLE_SEP_RE.match(lines[i]):
                    rows.append([c.strip() for c in
                                 lines[i].strip().strip("|").split("|")])
                i += 1
            blocks.append(("table", rows))
            continue
        if DL_DEF_RE.match(line) and para:
            term = " ".join(s.strip() for s in para)
            para.clear()
            defs = []
            while i < n and (DL_DEF_RE.match(lines[i]) or (
                    lines[i].strip() and not HEADING_RE.match(lines[i])
                    and not BULLET_RE.match(lines[i])
                    and not lines[i].startswith(("|", ">", "```")))):
                if DL_DEF_RE.match(lines[i]):
                    defs.append(DL_DEF_RE.sub("", lines[i]).strip())
                else:
                    defs[-1] += " " + lines[i].strip()
                i += 1
            if not defs:
                raise BuildError("definition list with no definitions")
            blocks.append(("dl", [(term, defs)]))
            continue
        if CHECK_ITEM_RE.match(line):
            flush_para()
            items = []
            while i < n and CHECK_ITEM_RE.match(lines[i]):
                items.append(CHECK_ITEM_RE.sub("", lines[i]).strip())
                i += 1
            blocks.append(("check", items))
            continue
        if BULLET_RE.match(line):
            flush_para()
            items = []
            while i < n and (BULLET_RE.match(lines[i])
                             and not CHECK_ITEM_RE.match(lines[i])):
                items.append(re.sub(r"[-*]\s+", "", lines[i], count=1).strip())
                i += 1
            blocks.append(("ul", items))
            continue
        m = NUM_LIST_RE.match(line)
        if m:
            flush_para()
            items = [(int(m.group(1)), m.group(2).strip())]
            i += 1
            while i < n and (mm := NUM_LIST_RE.match(lines[i])):
                items.append((int(mm.group(1)), mm.group(2).strip()))
                i += 1
            blocks.append(("ol", items))
            continue
        para.append(line)
        i += 1
    flush_para()
    return blocks


# --------------------------------------------------------------------------
# docs + anchors + link rewriting
# --------------------------------------------------------------------------

def load_docs(docs_dir: Path) -> list:
    files = sorted(p for p in docs_dir.glob("*.md") if p.is_file())
    if not files:
        raise BuildError(f"no .md docs found in {docs_dir}")
    docs = []
    for p in files:
        m = re.match(r"^(\d+)-(.*)$", p.stem)
        if not m:
            raise BuildError(f"docs files must be numbered, got: {p.name}")
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            raise BuildError(f"{p.name}: first line must be an H1 title")
        docs.append({
            "file": p.name,
            "num": int(m.group(1)),
            "slug": m.group(2),
            "title": lines[0][2:].strip(),
            "text": "\n".join(lines[1:]).strip(),
        })
    slugs = [d["slug"] for d in docs]
    if len(set(slugs)) != len(slugs):
        raise BuildError("duplicate chapter slugs")
    return docs


def chapter_label(num: int) -> str:
    return "Start here" if num == 0 else f"Chapter {num:02d}"


def collect_anchors(text: str) -> set:
    ids = set()
    for m in re.finditer(r"^#{1,3}\s+(.*)$", text, re.M):
        ids.add(slugify(m.group(1).strip()))
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if DL_DEF_RE.match(line) and idx > 0:
            term = lines[idx - 1].strip()
            if term:
                ids.add(slugify(term))
    return ids


def registry_from_docs(docs: list) -> dict:
    return {d["file"]: {"slug": d["slug"], "title": d["title"],
                        "num": d["num"], "_text": d["text"]} for d in docs}


def id_exists_in_doc(registry: dict, page_file: str, frag: str) -> bool:
    """True if `frag` resolves to a heading/dl anchor in the doc, allowing
    for per-heading suffixes the renderer may have appended."""
    return frag in collect_anchors(registry[page_file]["_text"])


def rewrite_links(rendered: str, registry: dict, *, id_prefix: str) -> str:
    """Rewrite <a href="NN-slug.md[#frag]"> to page URLs, validating
    anchors. Rendered ids carry id_prefix in book.html context."""

    def repl(m):
        fname, frag = m.group(1), (m.group(3) or "")
        if fname not in registry:
            raise BuildError(f"broken chapter link to {fname!r}")
        if frag and not id_exists_in_doc(registry, fname, frag):
            raise BuildError(
                f"anchor #{frag} does not exist in {fname}")
        page = registry[fname]["slug"] + ".html"
        # In the whole-book rendering, the fragment target is the chapter
        # section itself (prefixed ids exist there).
        if id_prefix and frag:
            return f'href="book.html#chapter-{registry[fname]["slug"]}"'
        return f'href="{page}#{frag}"' if frag else f'href="{page}"'

    return MD_TARGET_RE.sub(repl, rendered)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def render_blocks(blocks, registry: dict, *, id_prefix: str = ""):
    """Blocks -> (html, outline [(level, anchor, plain_text)])."""
    out = []
    outline = []
    seen_ids: set = set()

    def anchor_for(text: str) -> str:
        base = id_prefix + slugify(text)
        a, k = base, 2
        while a in seen_ids:
            a, k = f"{base}-{k}", k + 1
        seen_ids.add(a)
        return a

    for kind, payload in blocks:
        if kind in ("h1", "h2", "h3"):
            level = int(kind[1])
            a = anchor_for(payload)
            outline.append((level, a, payload))
            out.append(f'<h{level} id="{html.escape(a)}">{inline(payload)}'
                       "</h{0}>".format(level))
        elif kind == "p":
            out.append(f"<p>{inline(payload)}</p>")
        elif kind == "quote":
            out.append(f"<blockquote><p>{inline(payload)}</p></blockquote>")
        elif kind == "hr":
            out.append("<hr>")
        elif kind == "pre":
            out.append("<pre><code>%s</code></pre>" % html.escape(payload))
        elif kind == "check":
            li = "".join(f"<li>{inline(t)}</li>" for t in payload)
            out.append(f'<ul class="checklist">{li}</ul>')
        elif kind == "ul":
            li = "".join(f"<li>{inline(t)}</li>" for t in payload)
            out.append(f"<ul>{li}</ul>")
        elif kind == "ol":
            items = "".join(f"<li>{inline(t)}</li>" for _, t in payload)
            out.append(f'<ol start="{payload[0][0]}">{items}</ol>')
        elif kind == "table":
            head, body = payload[0], payload[1:]
            thead = "".join(f"<th>{inline(c)}</th>" for c in head)
            trs = "".join(
                "<tr>%s</tr>" % "".join(f"<td>{inline(c)}</td>" for c in r)
                for r in body)
            out.append(f"<table><thead><tr>{thead}</tr></thead>"
                       f"<tbody>{trs}</tbody></table>")
        elif kind == "dl":
            parts = []
            for term, defs in payload:
                a = anchor_for(term)
                outline.append((3, a, term))
                dds = "".join(f"<dd>{inline(d)}</dd>" for d in defs)
                parts.append(f'<dt id="{html.escape(a)}">{inline(term)}</dt>'
                             f"{dds}")
            out.append(f"<dl>{''.join(parts)}</dl>")
        else:  # pragma: no cover
            raise BuildError(f"unknown block kind {kind!r}")

    rendered = "\n".join(out)
    rendered = rewrite_links(rendered, registry, id_prefix=id_prefix)
    return rendered, outline


def doc_html(doc: dict, registry: dict, *, id_prefix: str = ""):
    body, outline = render_blocks(parse_blocks(doc["text"]), registry,
                                  id_prefix=id_prefix)
    h2s = [o for o in outline if o[0] == 2]
    return body, h2s


# --------------------------------------------------------------------------
# page templates
# --------------------------------------------------------------------------

def page_head(title: str, description: str, body_class: str = "") -> str:
    cls = f' class="{body_class}"' if body_class else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"'
        ">\n"
        f"<title>{html.escape(title)}</title>\n"
        f'<meta name="description" content="{html.escape(description)}">\n'
        f'<meta name="author" content="{html.escape(BOOK_OWNER)}">\n'
        f'<link rel="icon" href="{FAVICON}">\n'
        f'<link rel="stylesheet" href="{CSS_FILENAME}">\n'
        "</head>\n"
        f"<body{cls}>\n"
    )


def site_header(active: str = "") -> str:
    nav = []
    for name, href in (("Contents", "index.html"), ("Whole book", "book.html")):
        nav.append(f'<a href="{href}">{name}</a>')
    return (
        '<header class="site"><div class="wrap">'
        f'<a class="brand" href="index.html">{html.escape(BOOK_TITLE)}</a>'
        f"<nav>{''.join(nav)}</nav></div></header>\n"
    )


def site_footer() -> str:
    return '<footer class="site"><div class="wrap">' f"<p>{FOOTER}</p>" \
        "</div></footer>\n</body>\n</html>\n"


SKIP_LINK = '<a class="skip" href="#content">Skip to content</a>\n'


def build_chapter_pages(docs: list, out_dir: Path, registry: dict) -> None:
    for idx, doc in enumerate(docs):
        body, h2s = doc_html(doc, registry)
        desc = SUMMARIES[doc["file"]]
        label = chapter_label(doc["num"])
        parts = [
            page_head(f"{label} — {doc['title']} | {BOOK_TITLE}", desc),
            SKIP_LINK, site_header(),
            '<main id="content"><article><div class="wrap">\n',
            f'<p class="kicker">{label}</p>',
            f"<h1>{inline(doc['title'])}</h1>",
            f'<p class="intro-muted">{inline(desc)}</p>',
        ]
        if h2s:
            links = "".join(
                f'<li><a href="#{a}">{inline(t)}</a></li>'
                for _, a, t in h2s)
            parts.append(
                '<section class="onpage"><h2>On this page</h2>'
                f"<ul>{links}</ul></section>")
        parts.append(body)
        left, right = '<span class="disabled"></span>', \
            '<span class="disabled"></span>'
        if idx > 0:
            prev = docs[idx - 1]
            left = (
                f'<a href="{prev["slug"]}.html"><span class="label">'
                f"Previous</span>{inline(prev['title'])}</a>")
        if idx < len(docs) - 1:
            nxt = docs[idx + 1]
            right = (
                f'<a href="{nxt["slug"]}.html"><span class="label">Next</span>'
                f"{inline(nxt['title'])}</a>")
        parts.append(f'<nav class="pager">{left}{right}</nav>')
        parts.append("</div></article></main>\n")
        parts.append(site_footer())
        (out_dir / f"{doc['slug']}.html").write_text(
            "".join(parts), encoding="utf-8")


def build_index(docs: list, out_dir: Path, registry: dict) -> None:
    cards = "".join(
        f'<a class="card" href="{d["slug"]}.html">'
        f'<span class="num">{chapter_label(d["num"])}</span>'
        f"<h2>{inline(d['title'])}</h2>"
        f"<p>{inline(SUMMARIES[d['file']])}</p></a>"
        for d in docs)
    quick = "".join(
        f'<a href="{docs[i]["slug"]}.html">{inline(docs[i]["title"])}</a>'
        for i in (0, 1, 2, 4, 7, 9))
    kindle = docs[4]
    official = (
        '<h2 class="rule">Official sources worth bookmarking</h2>'
        '<p><a href="https://help.libbyapp.com/">Libby\'s help pages</a> · '
        '<a href="https://www.libbyapp.com/">libbyapp.com</a> '
        "(read in a browser) · "
        '<a href="https://www.hoopladigital.com/">hoopla</a> · '
        '<a href="https://help.kobo.com/">Kobo help</a> · '
        '<a href="https://www.amazon.com/sendtokindle">Amazon\'s Send to '
        "Kindle</a> (for personal files — not library books; that flow is "
        f'<a href="{kindle["slug"]}.html">{chapter_label(kindle["num"])}: '
        f"{inline(kindle['title'])}</a>).</p>"
        f"<p>For <em>where</em> to find genuinely free reading beyond your "
        "own card — big-city library cards open to non-residents, "
        "public-domain collections, open textbooks, and free language "
        f"platforms — see our companion directory, <em>{COMPANION}</em>. "
        "This guide covers the how; that directory covers the where.</p>")
    body = page_head(
        f"{BOOK_TITLE} — {BOOK_TAGLINE}",
        "A plain-English, step-by-step manual for borrowing free library "
        "ebooks and audiobooks on any device: cards, Libby, hoopla, Kindle, "
        "holds, renewals, sync fixes, and comfort settings.")
    body += (
        SKIP_LINK
        + '<header class="hero"><div class="wrap">'
        + f"<h1>{BOOK_TITLE}</h1>"
        + f"<p>{BOOK_TAGLINE}</p>"
        + "<p>Free ebooks, audiobooks, and magazines, straight from your "
        "local library — on your phone, tablet, Kindle, Kobo, laptop, or "
        "TV. The card is the key; this guide is the map: setup, borrowing, "
        "holds, renewals, fixes, and the comfort settings that make reading "
        "genuinely easy on any eyes.</p>"
        + '<span class="badge">Free forever · no accounts · works offline · '
        "MIT licensed</span>"
        + "</div></header>"
        + '<main id="content"><div class="wrap">'
        + f'<section class="jump">{quick}</section>'
        + '<h2 class="rule">The chapters</h2>'
        + f'<div class="cards">{cards}</div>'
        + official
        + "</div></main>\n"
        + site_footer())
    (out_dir / "index.html").write_text(body, encoding="utf-8")


def build_book(docs: list, out_dir: Path, registry: dict) -> None:
    toc = []
    for d in docs:
        toc.append(
            f'<li><a href="#chapter-{d["slug"]}">{inline(d["title"])}</a> '
            f'<span class="muted">({chapter_label(d["num"])})</span></li>')
    sections = []
    for d in docs:
        body, _ = doc_html(d, registry, id_prefix=f'{d["slug"]}-')
        sections.append(
            f'<section class="chapter" id="chapter-{d["slug"]}">'
            f'<p class="kicker">{chapter_label(d["num"])}</p>'
            f"<h1>{inline(d['title'])}</h1>{body}</section>")
    body = page_head(
        f"{BOOK_TITLE} — the whole book",
        "The entire manual on one page, for printing or searching.",
        body_class="book")
    body += (
        SKIP_LINK + site_header("Whole book")
        + '<main id="content"><div class="wrap">'
        + '<p class="kicker">Single-page edition</p>'
        + f"<h1>{BOOK_TITLE}</h1>"
        + "<p>The entire guide on one page — handy for printing (Chapter 10 "
        "is the fridge page) or a quick Ctrl+F.</p>"
        + '<section class="onpage toc"><h2>Contents</h2>'
        + f'<ol>{"".join(toc)}</ol></section>'
        + "<hr>\n" + "\n".join(sections)
        + "</div></main>\n"
        + site_footer())
    (out_dir / "book.html").write_text(body, encoding="utf-8")


# --------------------------------------------------------------------------
# check mode
# --------------------------------------------------------------------------

FORBIDDEN_LINK_PATTERNS = [
    "utm_", "?ref=", "&ref=", "?tag=", "&tag=", "affiliate", "a_id=",
    "/ref/", "?via=", "&cid=", "redirect=", "pixel", "analytics",
]
ALLOWED_EXTERNAL_HOST_PREFIXES = (
    "https://help.libbyapp.com",
    "https://www.libbyapp.com",
    "https://libbyapp.com",
    "https://www.hoopladigital.com",
    "https://help.hoopladigital.com",
    "https://help.kobo.com",
    "https://www.kobo.com",
    "https://www.amazon.com/sendtokindle",
    "https://opendyslexic.org",
    "https://libby.overdrive.com",
    "https://dylanasdale.github.io",
)
BANNED_PHRASES = [
    "obviously", "evidently", "everybody knows", "duh",
    "come on, it's", "how could you not", "total idiot", "click here",
    "todo", "fixme", "lorem ipsum",
]
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{8,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"xox[bap]-[A-Za-z0-9-]{10,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.(?:com|org|net|io|edu)",
    r"\b\d{13,16}\b",
]
MALFORMED_URL_RE = re.compile(
    r"\[[^\]]*\]\((https?://[^)\s]*(?:\s| -)[^)\s]*\))")


def lint_doc(doc: dict, registry: dict, problems: list) -> None:
    fname = doc["file"]

    def bad(msg: str) -> None:
        problems.append(f"{fname}: {msg}")

    try:
        render_blocks(parse_blocks(doc["text"]), registry)
    except BuildError as e:
        bad(str(e))

    raw = doc["text"]
    # internal links
    for m in re.finditer(r"\[[^\]]+\]\(([^()\s]+)\)", raw):
        href = m.group(1)
        if href.startswith(("http://", "https://")):
            if not href.startswith(ALLOWED_EXTERNAL_HOST_PREFIXES):
                bad(f"external link outside the allowlist: {href!r}")
            if any(p in href.lower() for p in FORBIDDEN_LINK_PATTERNS):
                bad(f"tracking/affiliate link: {href!r}")
            continue
        if href.startswith("#"):
            continue
        if re.match(r"^\d{2}-[a-z0-9-]+\.md(#.*)?$", href):
            target = href.split("#")[0]
            frag = href.split("#")[1] if "#" in href else ""
            if target not in registry:
                bad(f"broken chapter link {href!r}")
            elif frag and not id_exists_in_doc(registry, target, frag):
                bad(f"anchor #{frag} missing in {target}")
        else:
            bad(f"unexpected link target {href!r}")

    low = raw.lower()
    for w in BANNED_PHRASES:
        if w in low:
            bad(f"banned phrase {w!r}")
    if MALFORMED_URL_RE.search(raw):
        bad("link contains spaces — URL must be unbroken")
    for pat in SECRET_PATTERNS:
        if re.search(pat, raw):
            bad(f"possible secret/PII matching {pat}")
    if raw.count("**") % 2:
        bad("unbalanced ** bold markers")
    if raw.count("```") % 2:
        bad("unbalanced ``` fences")
    # link text shouldn't carry markup
    for m in re.finditer(r"\[([^\]]*)\]\(", raw):
        label = m.group(1)
        if "**" in label or "`" in label:
            bad(f"link text has markup: [{label}]")


def run_check(docs_dir: Path) -> int:
    problems: list[str] = []
    try:
        docs = load_docs(docs_dir)
    except BuildError as e:
        print(f"CHECK-FAIL: {e}")
        return 1
    registry = registry_from_docs(docs)
    missing = {d["file"] for d in docs} - set(SUMMARIES)
    extra = set(SUMMARIES) - {d["file"] for d in docs}
    for d in docs:
        doc_problems: list = []
        lint_doc(d, registry, doc_problems)
        problems.extend(doc_problems)
    if missing:
        problems.append(f"docs with no summary entry: {sorted(missing)}")
    if extra:
        problems.append(f"summary keys without docs: {sorted(extra)}")
    if problems:
        print("CHECK-FAIL:")
        for p in sorted(set(problems)):
            print(f"  - {p}")
        return 1
    print(f"CHECK-OK: {len(docs)} chapters; links, anchors, summaries, "
          "policy, and tone all clean")
    return 0


# --------------------------------------------------------------------------
# build + serve + CLI
# --------------------------------------------------------------------------

def build(out_dir: Path, docs_dir: Path = DOCS) -> list:
    docs = load_docs(docs_dir)
    registry = registry_from_docs(docs)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / CSS_FILENAME).write_text(STYLE, encoding="utf-8")
    build_chapter_pages(docs, out_dir, registry)
    build_index(docs, out_dir, registry)
    build_book(docs, out_dir, registry)
    return docs


def serve(out_dir: Path, port: int) -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(out_dir), **kw)

        def log_message(self, fmt, *args):  # pragma: no cover
            pass

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler) as srv:
        print(f"Serving {out_dir} at http://127.0.0.1:{port} "
              "(Ctrl+C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the static site")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--docs", type=Path, default=DOCS)
    ap.add_argument("--check", action="store_true",
                    help="lint the docs and exit (builds nothing)")
    ap.add_argument("--from-md", type=Path, metavar="FILE",
                    help="print one docs/*.md file as HTML")
    ap.add_argument("--serve", nargs="?", const=8000, type=int, default=None,
                    help="build, then preview at localhost[:PORT]")
    args = ap.parse_args(argv)

    try:
        if args.from_md:
            docs = load_docs(args.docs)
            registry = registry_from_docs(docs)
            matches = [d for d in docs if d["file"] == args.from_md.name]
            if not matches:
                raise BuildError(
                    f"--from-md: {args.from_md.name} is not a chapter")
            body, _ = render_blocks(parse_blocks(matches[0]["text"]), registry)
            sys.stdout.write(body + "\n")
            return 0
        if args.check:
            return run_check(args.docs)
        docs = build(args.out, args.docs)
        print(f"Built {len(docs)} chapter pages + index + book.html + "
              f"{CSS_FILENAME} into {args.out}")
        if args.serve:
            serve(args.out, args.serve)
        return 0
    except BuildError as e:
        print(f"BUILD ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
