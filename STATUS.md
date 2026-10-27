# STATUS.md — The Library Ebooks Comfort Guide

**Project:** A plain-English manual for borrowing free library ebooks and
audiobooks on any device — library cards, Libby, hoopla, send-to-Kindle,
holds/waitlists, renewals/multi-card, audiobooks & magazines, sync-trouble
fixes, large-print/dyslexia comfort settings, device-by-device checklists,
and a glossary. Built by **Asdale Dynamics, LLC**.
**Companion project:** *Free Reading for Less* (covers the *where*; this
guide covers the *how* — no duplicated directory content).

**Date:** 2026-10-27 · **Version:** 1.0.0 · **License:** MIT

## What was built

| Path | Purpose |
| --- | --- |
| `docs/` | 12 Markdown chapters (~81 KB, ~13k words): start-here, library card, Libby step-by-step, hoopla step-by-step, send-to-Kindle, holds/waitlists honestly, renewals & multiple cards, audiobooks/magazines/comics, sync & failure fixes, comfortable reading (large text, OpenDyslexic, dark mode, audio speeds), device-by-device checklists, glossary. |
| `build.py` | Standard-library-only site builder (no installs, offline, deterministic byte-identical output): per-chapter pages with "On this page" section nav and prev/next pagers, landing page, single-page `book.html` (print/Ctrl+F edition), external stylesheet. Also a `--check` docs linter and `--serve` preview server. |
| `tests/test_all.py` | 43-test `unittest` suite (stdlib only): markdown-subset renderer units, docs policy lint (banned condescension phrases, no tracking/affiliate links, host allowlist, no secrets/PII-shaped text, balanced markup), cross-page link/anchor resolution over the built site, tag-balance audit, byte-identical rebuild check, repo-file checks (exact LICENSE line, README commands). |
| `README.md` | Usage, maintenance workflow, design promises, credit to Asdale Dynamics, LLC. |
| `LICENSE` | MIT — `Copyright (c) 2026 Asdale Dynamics, LLC`. |
| `.gitignore` | `site/`, `__pycache__/`, OS cruft. |
| `site/` | Generated (built locally; not committed): 12 chapter pages + `index.html` + `book.html` + `style.css` (15 files, ~246 KB). |

## How to run it

```bash
python3 build.py                     # build site/ (Python 3.9+, stdlib only)
python3 build.py --serve [PORT]      # build, then preview at localhost:8000
python3 build.py --check             # lint docs (links, anchors, policy)
python3 -m unittest discover -s tests   # run the test suite
```

Then open `site/index.html` in any browser — works from `file://`, fully
offline. Chapter 10 (`site/device-checklists.html`) is the printable
checklist page; `site/book.html` is the whole book on one page.

## Verification results (2026-10-27)

- `python3 -m unittest discover -s tests` → **43/43 tests OK** (0 failures,
  0 errors).
- `python3 build.py --check` → **CHECK-OK**: 12 chapters; chapter links,
  cross-page anchors, summaries, link-policy (allowlist, no affiliate/
  tracking), tone, and secrets/PII scans all clean.
- `python3 build.py` → **Built 12 chapter pages + index + book.html +
  style.css**; rebuild is byte-identical (covered by test).
- Local HTTP smoke: `--serve` at 127.0.0.1 → **15/15 paths returned 200**
  (index, book, all 12 chapters, stylesheet).
- Site hygiene (tested): no external resources loaded (favicon is an inline
  data URI, stylesheet local), no tracking/affiliate markers, every external
  link on an allowlist of official help pages, tag-balance audit clean on
  all 15 pages, every page carries the Asdale Dynamics, LLC credit.
- Fixed during verification: server-handler bug in `--serve` (was
  non-launchable), cross-chapter Markdown links not rewritten to `.html`
  hrefs, and several prose/typo defects (garbled sentences, a stray
  Cyrillic word, unbalanced em-dash constructions) caught by reading built
  output.

## Fact-checking

Key claims were verified against official/live sources before writing
(October 2026): Libby's Kindle flow (Shelf → Loans → Read With… → Kindle →
Get Library Book; U.S.-only; Fire tablets read in Libby), Amazon's
re-delivery fix via Content & Devices, hoopla's Instant/Flex license types
and BingePass mechanics (incl. the Magazines BingePass), Libby's
OpenDyslexic Book Design option and "Include accessibility sizes", and
Kobo's built-in OverDrive support (supported models, U.S./Canada, no
audiobooks/magazines on device). Volatile UI details are hedged in the text
itself; loan lengths/allowances are attributed to per-library settings.

## Known gaps / honest limits

- **Factual drift:** Libby/hoopla UIs move; the docs hedge ("wording
  varies", "as of October 2026") rather than pin screenshots. Recheck the
  Kindle re-delivery and hoopla allowance numbers when revisiting.
- **No screenshots or videos** — deliberately text-only to stay offline,
  small, and maintainable; screenshots would rot faster than prose.
- **Loan-period values** (21/14/7 days) are typicals; some libraries
  configure different values — always noted in the text as library-set.
- **The glossary's "Content & Devices" path** is written for
  `amazon.com` (U.S.); other Amazon locales differ.
- **Search**: intentionally omitted (single-page `book.html` + browser
  Ctrl+F covers it).
- Nothing is committed beyond the local repo; nothing published remotely.
