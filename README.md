# The Library Ebooks Comfort Guide

A plain-English, step-by-step manual for borrowing **free library ebooks,
audiobooks, and magazines on any device** — written the way a friend would
explain it: no condescension, no affiliate links, honest about the parts
other guides skip (waitlists, renewals, two-different-"send-to-Kindle"s,
and the small glitches that lose your page).

Built and maintained by **Asdale Dynamics, LLC**, the beginner-friendly
education project of author Dylan Asdale
([dylanasdale.github.io](https://dylanasdale.github.io/)).

## What's inside

- **docs/** — the manual itself, one Markdown file per chapter:
  `00` start-here · `01` your library card · `02` Libby step by step ·
  `03` hoopla step by step · `04` send-to-Kindle without confusion ·
  `05` holds and waitlists, explained honestly · `06` renewals and
  multiple cards · `07` audiobooks, magazines, comics and more ·
  `08` sync/trouble fixes (a symptom-to-fix table) · `09` reading
  comfortably (large print, OpenDyslexic, dark mode, audio speeds) ·
  `10` printable device-by-device checklists · `11` glossary.
- **build.py** — a standard-library-only static site builder: one polished
  HTML page per chapter, a landing page, a single-page `book.html`
  (print/Ctrl+F edition), plus a `--check` docs linter (links, anchors,
  policy, tone, secrets) and a `--serve` preview.
- **tests/** — a `unittest` suite (42 tests): renderer units, docs policy
  (no tracking/affiliate links, no PII-shaped text, balanced markup),
  link/anchor resolution across the built site, byte-identical rebuilds.
- **site/** — the generated site (built locally, not committed).

## How to read it

```bash
python3 build.py            # build site/ (Python 3.9+, nothing else)
open site/index.html        # any browser, works offline from file://
```

Prefer the whole book on one page (also great printed/Ctrl+F):
open `site/book.html`. Checkbox lists in chapter 10 are the
print-the-fridge-page device checklists.

## How to maintain it

1. Edit the chapters in `docs/` (Markdown subset documented in `build.py`).
2. Run `python3 -m unittest discover -s tests` and
   `python3 build.py --check`. Fix anything flagged.
3. Rebuild with `python3 build.py` — output is deterministic
   (byte-identical rebuilds, no timestamps), so diffs stay clean.

Preview locally with `python3 build.py --serve` (http://127.0.0.1:8000).

## Design promises

- **Local-first:** after building, the site needs no network — zero
  external requests, no analytics, no cookies, no accounts.
- **Complementary:** this guide covers the *how* of free library reading;
  the companion project **Free Reading for Less** covers the *where*
  (big-city cards open to non-residents, public-domain collections, open
  textbooks). No duplicated content between them.
- **Honest:** UI steps are hedged where apps drift; limits (U.S.-only
  Kindle loans, hoopla allowances, Kobo not playing audiobooks) are stated
  plainly.
- **No secrets or personal data:** the test suite scans for key-shaped or
  PII-shaped text on every run.

## Credits

Created and maintained by **Asdale Dynamics, LLC** — beginner-friendly AI
education, books, and practical tools.

## License

MIT — see `LICENSE` (Copyright (c) 2026 Asdale Dynamics, LLC).
