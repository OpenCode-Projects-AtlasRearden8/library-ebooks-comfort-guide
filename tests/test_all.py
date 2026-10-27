"""Test suite for The Library Ebooks Comfort Guide.

Standard library only (unittest). Runs offline; never fetches or builds
anything into the repo's real site/ dir.

Run:  python3 -m unittest discover -s tests
  or: python3 tests/test_all.py
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

DOCS = build.DOCS
MD_LINKS_RE = re.compile(
    r"\[[^\]]+\]\((\d{2}-[a-z0-9-]+\.md)(#[^)\s]*)?\)")


def build_to(tmp: Path) -> list:
    docs = build.build(tmp, build.DOCS)
    return docs


def read_chapter_html(dir_path: Path, doc: dict) -> str:
    return (dir_path / f"{doc['slug']}.html").read_text(encoding="utf-8")


def build_test_registry(reg: dict) -> dict:
    """A small registry for renderer unit tests."""
    out = dict(reg)
    for v in out.values():
        v.setdefault("title", "test")
        v.setdefault("num", 0)
    return out


class MarkdownTester(unittest.TestCase):
    """Unit checks for the markdown subset renderer."""

    def parse(self, md: str):
        return build.parse_blocks(md)

    def test_heading_slugs_and_outline(self):
        blocks = self.parse("## Libby's Shelf\n\ntext\n\n## A Pause, Then")
        html, outline = build.render_blocks(blocks, {})
        self.assertIn('id="libbys-shelf"', html)
        self.assertIn('id="a-pause-then"', html)
        kinds = [(lvl, a, t) for lvl, a, t in outline]
        self.assertEqual(kinds[0][2], "Libby's Shelf")
        self.assertEqual(kinds[0][0], 2)

    def test_anchor_dedup(self):
        blocks = self.parse("## Same\n\n## Same\n")
        html, _ = build.render_blocks(blocks, {})
        self.assertIn('id="same"', html)
        self.assertIn('id="same-2"', html)

    def test_inline_markup(self):
        html, _ = build.render_blocks(
            self.parse("One **bold**, *it*, `code`, plain \"quote\""), {})
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>it</em>", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn("\"quote\"", html)

    def test_html_escaped_first(self):
        html, _ = build.render_blocks(self.parse("a < b & c <d>"), {})
        self.assertIn("a &lt; b &amp; c &lt;d&gt;", html)
        self.assertNotIn("<d>", html)

    GLOSSARY_REG = {
        "11-glossary.md": {"slug": "glossary",
                           "_text": "Borrow\n:   To check out a title.\n"},
    }

    def test_links(self):
        html, _ = build.render_blocks(
            self.parse("See [Glossary](11-glossary.md#borrow)."),
            build_test_registry(self.GLOSSARY_REG))
        self.assertIn('href="glossary.html#borrow"', html)
        html, _ = build.render_blocks(
            self.parse("Read [docs](https://example.org/guide) online"), {})
        self.assertIn('href="https://example.org/guide"', html)

    def test_broken_internal_link_raises(self):
        with self.assertRaises(build.BuildError):
            build.render_blocks(self.parse("[x](42-nope.md)"), {})

    def test_broken_anchor_raises(self):
        with self.assertRaises(build.BuildError):
            build.render_blocks(self.parse("[x](11-glossary.md#monster)"),
                                self.GLOSSARY_REG)

    def test_checklist_block(self):
        html, _ = build.render_blocks(
            self.parse("- [ ] Install Libby\n- [ ] Sign in\n"), {})
        self.assertIn('<ul class="checklist">', html)
        self.assertIn("<li>Install Libby</li>", html)
        self.assertNotIn("[ ]", html)

    def test_bullets_and_numbered(self):
        html, _ = build.render_blocks(
            self.parse("- one\n- two\n\n3. step\n4. step\n"), {})
        self.assertIn("<ul>", html)
        self.assertIn('<ol start="3">', html)

    def test_table(self):
        html, _ = build.render_blocks(
            self.parse("| a | b |\n| --- | --- |\n| 1 | 2 |\n"), {})
        self.assertIn("<table>", html)
        self.assertIn("<th>a</th>", html)
        self.assertIn("<td>1</td>", html)
        self.assertNotIn("|", html)

    def test_blockquote(self):
        html, _ = build.render_blocks(
            self.parse("> **Note:** honest limits."), {})
        self.assertIn("<blockquote><p>", html)
        self.assertIn("<strong>Note:</strong>", html)

    def test_definition_list(self):
        blocks = self.parse("Borrow\n:   To check out a title. Fine.\n")
        html, outline = build.render_blocks(blocks, {})
        self.assertIn('<dt id="borrow">Borrow</dt>', html)
        self.assertIn("<dd>", html)
        self.assertIn(("borrow", "Borrow"), [(a, t) for _, a, t in outline])

    def test_fence_and_hr(self):
        html, _ = build.render_blocks(
            self.parse("```bash\npython3 build.py --check\n```\n\n---\n"), {})
        self.assertIn("<pre><code>", html)
        self.assertIn("python3 build.py --check", html)
        self.assertIn("<hr>", html)

    def test_unbalanced_fence_raises(self):
        with self.assertRaises(build.BuildError):
            build.parse_blocks("```\nnope")

    def test_empty_paragraph_omitted(self):
        html, _ = build.render_blocks(self.parse("start\n\nend\n"), {})
        self.assertEqual(html.count("<p>"), 2)


class DocsTester(unittest.TestCase):
    """The docs themselves: naming, summaries, policy, tone."""

    @classmethod
    def setUpClass(cls):
        docs = build.load_docs(build.DOCS)
        num = 0
        for idx, doc in enumerate(docs):
            num += 1
        # sanity export
        cls.docs = docs

    def test_numbering_sequential(self):
        self.assertEqual([d["num"] for d in self.docs],
                         list(range(len(self.docs))))

    def test_summary_matches_docs(self):
        self.assertEqual({d["file"] for d in self.docs}, set(build.SUMMARIES))

    def test_nonempty_chapters(self):
        for doc in self.docs:
            self.assertGreater(len(doc["text"]), 1500,
                               f"{doc['file']} is too thin to be a chapter")

    def test_glossary_terms_have_dt_ids(self):
        gloss = next(d for d in self.docs if d["file"] == "11-glossary.md")
        html, _ = build.render_blocks(build.parse_blocks(gloss["text"]), {})
        ids = re.findall(r'<dt id="([^"]+)"', html)
        self.assertGreater(len(ids), 20)
        self.assertEqual(len(ids), len(set(ids)))

    def test_policy_no_banned_phrases_or_pii(self):
        for doc in self.docs:
            problems = []
            build.lint_doc(doc, build.registry_from_docs(self.docs),
                           problems)
            self.assertEqual(problems, [])

    def test_docs_mention_companion_and_devices(self):
        all_text = "\n".join(d["text"] for d in self.docs)
        self.assertIn("Free Reading for Less", all_text)
        self.assertIn("OpenDyslexic", all_text)
        self.assertIn("hoopla", all_text.lower())

    def test_docs_never_use_md_links_without_anchor_check(self):
        reg = build.registry_from_docs(self.docs)
        for doc in self.docs:
            for m in MD_LINKS_RE.finditer(doc["text"]):
                self.assertIn(m.group(1), reg)
                if m.group(2):
                    frag = m.group(2)[1:]
                    self.assertIn(
                        frag, build.collect_anchors(reg[m.group(1)]["_text"]),
                        f"{doc['file']}: anchor {frag} missing in {m.group(1)}")


class SiteTester(unittest.TestCase):
    """Build the site to a temp dir and assert its shape and hygiene."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name) / "site"
        cls.docs = build_to(tmp)
        cls.tmp = tmp

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_expected_files(self):
        expected = ["index.html", "book.html", build.CSS_FILENAME]
        expected += [f"{d['slug']}.html" for d in self.docs]
        self.assertEqual(
            sorted(p.name for p in self.tmp.iterdir()),
            sorted(expected))

    def test_chapter_pages_have_pager_and_title(self):
        for idx, doc in enumerate(self.docs):
            html_text = read_chapter_html(self.tmp, doc)
            self.assertIn(f"<h1>{build.inline(doc['title'])}</h1>", html_text)
            self.assertIn("class=\"pager\"", html_text)
            if idx > 0:
                self.assertIn(f'href="{self.docs[idx - 1]["slug"]}.html"',
                              html_text)
            if idx < len(self.docs) - 1:
                self.assertIn(f'href="{self.docs[idx + 1]["slug"]}.html"',
                              html_text)
            self.assertTrue(re.search(r"<title>[^<]+" +
                                      re.escape(build.BOOK_TITLE),
                                      html_text), doc["file"])

    def test_index_lists_all_chapters(self):
        html_text = (self.tmp / "index.html").read_text(encoding="utf-8")
        for doc in self.docs:
            self.assertIn(f'href="{doc["slug"]}.html"', html_text)
            self.assertIn(doc["title"], html_text)
        self.assertIn(build.BOOK_TITLE, html_text)
        self.assertIn(build.BOOK_OWNER, html_text)

    def test_book_contains_every_chapter(self):
        html_text = (self.tmp / "book.html").read_text(encoding="utf-8")
        for doc in self.docs:
            self.assertIn(f'id="chapter-{doc["slug"]}"', html_text)
            self.assertIn(doc["title"], html_text)

    def test_no_md_hrefs_remain(self):
        for p in self.tmp.glob("*.html"):
            self.assertNotIn(".md#", p.read_text(encoding="utf-8"), p.name)
            self.assertNotIn('href="0', p.read_text(encoding="utf-8"), p.name)

    def test_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as t2:
            second = Path(t2) / "site"
            build_to(second)
            for name in ("index.html", "book.html", build.CSS_FILENAME):
                a = (self.tmp / name).read_bytes()
                b = (second / name).read_bytes()
                self.assertEqual(a, b, name)
            for doc in self.docs:
                a = read_chapter_html(self.tmp, doc)
                b = (second / f"{doc['slug']}.html").read_text(
                    encoding="utf-8")
                self.assertEqual(a, b, doc["file"])

    def test_all_internal_links_resolve(self):
        pages = {}
        for p in self.tmp.glob("*.html"):
            pages[p.name] = p.read_text(encoding="utf-8")
        ids_by_page = {}
        for name, text in pages.items():
            ids_by_page[name] = set(re.findall(r'id="([^"]+)"', text))
        for name, text in pages.items():
            for m in re.finditer(r'href="([^"#]+)(#([^"]+))?"', text):
                href, frag = m.group(1), m.group(3)
                if href.startswith(("http", "data:", "style.css")):
                    continue
                target = href if "/" not in href else href.split("/")[-1]
                self.assertIn(target, pages, f"{name} -> {href}")
                if frag:
                    self.assertIn(frag, ids_by_page[target],
                                  f"{name} -> {href}")

    def test_tag_balance_on_built_pages(self):
        void = {"br", "hr", "img", "link", "meta", "input", "source",
                "base", "area", "embed", "wbr", "col", "path", "rect"}
        tags = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>!]*?(/?)>")
        for p in self.tmp.glob("*.html"):
            text = p.read_text(encoding="utf-8")
            stack = []
            for m in tags.finditer(text):
                closing, name, self_closing = m.groups()
                name = name.lower()
                if name in void or self_closing:
                    continue
                if closing:
                    self.assertTrue(stack and stack[-1] == name,
                                    f"{p.name}: </{name}> closes nothing")
                    stack.pop()
                else:
                    stack.append(name)
            self.assertFalse(stack, f"{p.name}: unclosed tags {stack}")

    def test_no_external_resources_loaded(self):
        resource_re = re.compile(
            r"<(?:link|script|img|iframe|source|embed|track|object|audio|"
            r"video)[^>]+(?:src|href)=\"(http[^\"']+)")
        for p in self.tmp.glob("*.html"):
            self.assertEqual(resource_re.findall(p.read_text(
                encoding="utf-8")), [], p.name)

    def test_no_tracking_or_affiliate_markers(self):
        bad = ["utm_", "?ref=", "&ref=", "?tag=", "&tag=", "affiliate",
               "doubleclick", "googletagmanager", "facebook.com",
               "analytics.js"]
        for p in self.tmp.glob("*.html"):
            text = p.read_text(encoding="utf-8").lower()
            for marker in bad:
                self.assertNotIn(marker, text, f"{p.name}: {marker}")

    def test_external_links_use_allowlisted_hosts(self):
        allow = ("https://help.libbyapp.com", "https://www.libbyapp.com",
                 "https://libbyapp.com", "https://www.hoopladigital.com",
                 "https://help.kobo.com", "https://www.kobo.com",
                 "https://www.amazon.com/sendtokindle",
                 "https://opendyslexic.org", "https://libby.overdrive.com",
                 build.HUB_URL)
        for p in self.tmp.glob("*.html"):
            for href in re.findall(r'href="(http[^"]+)"',
                                   p.read_text(encoding="utf-8")):
                self.assertTrue(
                    href.startswith(allow),
                    f"{p.name}: off-allowlist link {href}")

    def test_owner_credit_on_every_page(self):
        for p in self.tmp.glob("*.html"):
            self.assertIn(build.BOOK_OWNER, p.read_text(encoding="utf-8"))

    def test_receipts_in_key_chapters(self):
        checklist = (self.tmp / "device-checklists.html").read_text(
            encoding="utf-8")
        self.assertIn("checklist", checklist)
        kindle = (self.tmp / "send-to-kindle.html").read_text(
            encoding="utf-8")
        self.assertIn("Get Library Book", kindle)
        self.assertIn("Content &amp; Devices", kindle)
        glossary = (self.tmp / "glossary.html").read_text(encoding="utf-8")
        self.assertIn("BingePass", glossary)


class CliTester(unittest.TestCase):
    """The CLI paths: check, from-md, build with bad docs."""

    def test_check_mode_clean(self):
        self.assertEqual(build.run_check(build.DOCS), 0)

    def test_from_md_stdout(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = build.main(["--from-md", str(build.DOCS /
                                              "11-glossary.md")])
        self.assertEqual(rc, 0)
        self.assertIn("<dt id=\"bingepass\">BingePass</dt>", buf.getvalue())

    def test_bad_doc_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            docs_dir = Path(t) / "docs"
            docs_dir.mkdir()
            (docs_dir / "not-numbered.md").write_text("# Nope\n")
            with self.assertRaises(build.BuildError):
                build.build(Path(t) / "out", docs_dir)

    def test_check_mode_flags_broken_doc(self):
        with tempfile.TemporaryDirectory() as t:
            docs_dir = Path(t) / "docs"
            docs_dir.mkdir()
            for p in build.DOCS.glob("*.md"):
                (docs_dir / p.name).write_text(p.read_text(encoding="utf-8"))
            (docs_dir / "99-broken.md").write_text(
                "# Broken\n\nHere is a [missing link](42-nope.md).\n")
            self.assertNotEqual(build.run_check(docs_dir), 0)

    def test_build_script_smoke(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "build.py"), "--help"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--check", proc.stdout)


class RepoFilesTester(unittest.TestCase):
    """README/LICENSE hygiene promised by the project brief."""

    def test_license_exact_copyright_line(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Asdale Dynamics, LLC",
                      license_text)
        self.assertIn("MIT", license_text)

    def test_readme_credits_owner_and_documents_commands(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Asdale Dynamics, LLC", readme)
        self.assertIn("python3 build.py", readme)
        self.assertIn("unittest", readme)

    def test_gitignore_covers_site_and_pycache(self):
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("site/", gi)
        self.assertIn("__pycache__", gi)


if __name__ == "__main__":
    unittest.main(verbosity=2)
