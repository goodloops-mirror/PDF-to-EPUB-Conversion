# How the conversion works

Implementation: [`src/convert.py`](../src/convert.py).

## 1. Reading the PDF

The PDF is opened with PyMuPDF and each page's text is read as positioned lines
(text, left x, top y, height, direction, font size). Screenplay PDFs exported from
screenwriting software carry real text, so no OCR is involved.

## 2. Watermark handling

The only intended content change.

1. **Detect** overlay lines: text that is not horizontal (rotated) or set at a very large
   font size. Overlay texts that appear on at least half the pages are the watermark.
   `WATERMARK_TERMS` overrides detection.
2. **Remove** those overlay lines, and any ordinary header/footer line that equals the
   watermark text.
3. **Re-add** the watermark text as a plain footer at the end of the title page and every
   scene chapter. If the PDF already contained the text as a header/footer, that is the
   footer; otherwise it is created from the overlay. EPUB is reflowable and has no fixed
   pages, so a per-chapter footer is the closest equivalent.

### Why no configuration is usually needed

The watermark is auto-detected, so a typical run needs only `INPUT_PDF` in `.env`:

- Overlay lines are found by their style (rotated, or font size of 40pt or more), and
  text repeated on at least half the pages is taken as the watermark. The text itself is
  read from the PDF at run time and is never stored in the repository.
- `EXCLUDE_PATTERNS` is empty by default, so no lines are dropped except the watermark.
- Screenplay structure comes from layout (indents, `INT.`/`EXT.` prefixes), not from
  document-specific names or patterns.

Set `WATERMARK_TERMS` in `.env` when auto-detection does not fit:

- The watermark is horizontal, small or faint. Nothing is detected and the run stops with
  "No watermark detected; set WATERMARK_TERMS in .env".
- Other large text, such as a title repeated on most pages, would be mistaken for the
  watermark.

## 3. Classifying lines

Screenplay elements are recognised from the **left indent** of each line (in PDF points)
and, for scene headings, from the text:

| Element | Rule |
| --- | --- |
| Scene number | numeric text in the left margin (x < 70) |
| Duplicate scene number | numeric text in the right margin, ignored |
| Page number | numeric text in the top-right corner |
| Scene heading | x < 130 and starts with `INT.`, `EXT.`, `I/E` … |
| Action | x < 130, anything else |
| Dialogue | 130 ≤ x < 186 |
| Parenthetical | 186 ≤ x < 216 |
| Character | 216 ≤ x < 330 |
| Transition | x ≥ 330 |

Thresholds match the layout of the tested PDF and may need adjusting for other exports.

## 4. Building paragraphs

- Consecutive lines of the same type with a small vertical gap are merged into one
  paragraph (hard line breaks are removed so text reflows).
- A word hyphenated at a line break is rejoined without a space.
- A character cue starts a dialogue block; parentheticals and speech that follow stay
  inside it, and the block avoids page breaks.
- The scene number from the margin is attached to its heading by matching vertical
  position (e.g. `81A`).

## 5. Writing the EPUB

An EPUB 3 package is written directly with `zipfile` (with an EPUB 2 `toc.ncx` for older
readers): a title page, one XHTML file per scene, a navigation document listing all
scenes, and a stylesheet. Title and author come from the title page (the line after
`von`) unless overridden in `.env`.

## Known limitations

- `(MORE)` / `(CONT'D)` markers repeated across page breaks are kept.
- Page numbers are kept unless `STRIP_PAGE_NUMBERS=true`.
- The logo image on the title page is not included.
- Indent thresholds are tuned to one PDF layout.
