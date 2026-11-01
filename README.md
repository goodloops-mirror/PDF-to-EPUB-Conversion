# convert-screenplay-to-epub

Convert a screenplay PDF into a reflowable EPUB that reads well on an e-reader.

## ⚠️ Personal use only — respect intellectual property

**This tool is for personal use only.**

Screenplays are often shared with a recipient's name stamped across every page as a
watermark. That watermark exists to protect the author's and production company's
intellectual property. This tool removes the diagonal watermark **solely to make the
resulting EPUB readable** on a small screen; the watermark text is re-added as a
plain footer so the copy stays attributable to you.

- Do **not** distribute, upload, share or publish the converted EPUB.
- Do **not** use this tool to hide who a document was issued to or to evade leak tracing.
- If a client or production company gave you a PDF, honour whatever terms came with it.
  Their material stays theirs.

You are responsible for how you use this software.

## Usage

Requires Python 3 and nothing else; everything (virtual environment, caches) lives inside
this repository.

```bash
cp .env.example .env     # then edit .env, quote values containing spaces
./run.sh src/convert.py
```

The EPUB is written to `OUTPUT_DIR` (default `output/`).

### Configuration (`.env`, gitignored)

| Variable | Purpose |
| --- | --- |
| `INPUT_PDF` | Path to the source PDF (or pass it as the first argument) |
| `OUTPUT_DIR` | Output folder, default `output` |
| `WATERMARK_TERMS` | Comma-separated watermark text; auto-detected if empty |
| `EXCLUDE_PATTERNS` | Regexes for extra lines to drop, separated by `;;` |
| `STRIP_PAGE_NUMBERS` | `true` drops page-number lines |
| `EPUB_TITLE`, `EPUB_AUTHOR` | Override metadata read from the title page |

Names, paths and patterns specific to your documents belong only in `.env`, so the
repository can be published at any time without leaking private information. Inputs and
outputs (`input/`, `output/`) are gitignored too.

## How it works

See [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

## Versioning

[SemVer](https://semver.org/); see [CHANGELOG.md](CHANGELOG.md).

## Support

If this tool saves you time, you can [buy me a coffee](https://www.buymeacoffee.com/hanshafner) ☕. It is optional;
the code stays free under the license above.

## License

Copyleft, GNU AGPL-3.0-or-later (see `LICENSE`). This matches the license of the PyMuPDF
dependency.
