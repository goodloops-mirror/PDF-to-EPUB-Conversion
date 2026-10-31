"""Convert a watermarked screenplay PDF to EPUB.

The only content change is removing the diagonal watermark overlay. The watermark text is
kept as a regular footer (taken from the PDF's own footer if present, else from the overlay).
All configuration comes from environment variables (see .env.example).
"""
import os
import re
import sys
import uuid
import zipfile
from collections import Counter
from html import escape
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text().strip()

SCENE_RE = re.compile(r"^(INT|EXT|I/E|INT\./EXT|EXT\./INT)\b[./ ]", re.I)
NUM_RE = re.compile(r"^\d+[A-Z]?\.?$")


def env_list(name, sep=","):
    return [v.strip() for v in os.environ.get(name, "").split(sep) if v.strip()]


def extract_lines(page):
    """Return (overlay_texts, lines); line = dict(x, y, h, text)."""
    overlay, lines = [], []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            text = "".join(s["text"] for s in l["spans"]).strip()
            if not text:
                continue
            dx, dy = l["dir"]
            if abs(dy) > 0.05 or l["spans"][0]["size"] >= 40:
                overlay.append(text)
                continue
            x0, y0, x1, y1 = l["bbox"]
            lines.append({"x": x0, "x1": x1, "y": y0, "h": y1 - y0, "text": text})
    lines.sort(key=lambda l: (round(l["y"]), l["x"]))
    return overlay, lines


def classify(line, page_w):
    x, t = line["x"], line["text"]
    if NUM_RE.match(t) and x < 70:
        return "scenenum"
    if NUM_RE.match(t) and x > 480:
        return "pagenum" if line["y"] < 60 else "scenenum_dup"
    if x < 130:
        return "heading" if SCENE_RE.match(t) else "action"
    if x < 186:
        return "dialogue"
    if x < 216:
        return "paren"
    if x < 330:
        return "character"
    return "transition"


def join(parts):
    out = ""
    for p in parts:
        if out and out[-1] == "-" and len(out) > 1 and out[-2].isalpha():
            out += p
        else:
            out += (" " if out else "") + p
    return out


def build_scenes(doc, watermark_terms, strip_pagenums, exclude):
    wm_counter, pages = Counter(), []
    for page in doc:
        overlay, lines = extract_lines(page)
        wm_counter.update(overlay)
        pages.append(lines)
    terms = watermark_terms or [t for t, n in wm_counter.items() if n >= len(doc) * 0.5]
    if not terms:
        sys.exit("No watermark detected; set WATERMARK_TERMS in .env")
    footer = terms[0]
    footer_in_pdf = False

    title, scenes = [], [{"title": None, "num": None, "items": []}]
    for pno, lines in enumerate(pages):
        kept = []
        for l in lines:
            if l["text"] in terms or l["text"] == footer:
                footer_in_pdf = True
                continue
            if any(p.search(l["text"]) for p in exclude):
                continue
            kept.append(l)
        if pno == 0:
            title = [l["text"] for l in kept]
            continue
        prev = None
        for l in kept:
            kind = classify(l, doc[pno].rect.width)
            if kind == "scenenum_dup" or (kind == "pagenum" and strip_pagenums):
                continue
            if kind == "scenenum":
                continue
            if kind == "heading":
                num = next((n["text"].rstrip(".") for n in kept
                            if classify(n, 0) == "scenenum" and abs(n["y"] - l["y"]) < 4), None)
                scenes.append({"title": l["text"], "num": num, "items": []})
                prev = None
                continue
            gap = (l["y"] - prev["y"] - prev["h"]) if prev else 0
            items = scenes[-1]["items"]
            same = items and items[-1][0] == kind and gap < l["h"] * 0.5 and kind not in ("character", "pagenum")
            if same:
                items[-1][1].append(l["text"])
            else:
                items.append([kind, [l["text"]]])
            prev = l
    return footer, footer_in_pdf, title, scenes


def scene_xhtml(scene, footer, idx):
    h = ["<h2>%s%s</h2>" % ((escape(scene["num"]) + " " if scene["num"] else ""), escape(scene["title"] or ""))]
    in_dlg = False
    for kind, parts in scene["items"]:
        text = escape(join(parts))
        if kind == "character":
            if in_dlg:
                h.append("</div>")
            h.append('<div class="dlg"><p class="character">%s</p>' % text)
            in_dlg = True
            continue
        if in_dlg and kind not in ("dialogue", "paren", "pagenum"):
            h.append("</div>")
            in_dlg = False
        h.append('<p class="%s">%s</p>' % (kind, text))
    if in_dlg:
        h.append("</div>")
    return page(escape(scene["title"] or ""), "\n".join(h), footer)


def page(title, body, footer):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="de">'
            '<head><meta charset="utf-8"/><title>%s</title><link rel="stylesheet" href="style.css"/></head>'
            '<body>\n%s\n<footer><p class="wmfooter">%s</p></footer></body></html>' % (title, body, escape(footer)))


CSS = """body{font-family:serif;line-height:1.35;margin:0 .5em}
h1,h2{font-family:sans-serif} h2{font-size:1em;text-transform:uppercase;margin:1.2em 0 .6em;page-break-after:avoid}
p{margin:.5em 0} .transition{text-align:right;text-transform:uppercase}
.dlg{margin:.8em 0;page-break-inside:avoid} .character{margin:0 0 .1em 8em;text-transform:uppercase;page-break-after:avoid}
.paren{margin:0 0 .1em 5em;font-style:italic} .dialogue{margin:0 3em 0 3em}
.pagenum{text-align:right;font-size:.7em;color:#777}
.title{text-align:center} footer{margin-top:2.5em;border-top:1px solid #999;text-align:center;font-size:.7em;color:#555}
"""


def write_epub(out, title_lines, author, book_title, footer, scenes):
    files = [("title.xhtml", "Titel", page(escape(book_title),
             '<div class="title">%s</div>' % "".join("<p>%s</p>" % escape(t) for t in title_lines), footer))]
    for i, s in enumerate(scenes[1:] if not scenes[0]["items"] else scenes):
        if s["title"] is None:
            s = dict(s, title="Anfang")
        files.append(("s%04d.xhtml" % i, (s["num"] + " " if s["num"] else "") + s["title"], scene_xhtml(s, footer, i)))
    uid = "urn:uuid:" + str(uuid.uuid4())
    manifest = "".join('<item id="f%d" href="%s" media-type="application/xhtml+xml"/>' % (i, f) for i, (f, _, _) in enumerate(files))
    spine = "".join('<itemref idref="f%d"/>' % i for i in range(len(files)))
    navli = "".join('<li><a href="%s">%s</a></li>' % (f, escape(t)) for f, t, _ in files)
    ncx = "".join('<navPoint id="n%d" playOrder="%d"><navLabel><text>%s</text></navLabel><content src="%s"/></navPoint>'
                  % (i, i + 1, escape(t), f) for i, (f, t, _) in enumerate(files))
    opf = ('<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">%s</dc:identifier><dc:title>%s</dc:title>'
           '<dc:creator>%s</dc:creator><dc:language>de</dc:language><meta property="dcterms:modified">2000-01-01T00:00:00Z</meta></metadata>'
           '<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="css" href="style.css" media-type="text/css"/>%s</manifest>'
           '<spine toc="ncx">%s</spine></package>') % (uid, escape(book_title), escape(author), manifest, spine)
    nav = ('<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
           '<head><title>Inhalt</title></head><body><nav epub:type="toc"><h1>Inhalt</h1><ol>%s</ol></nav></body></html>' % navli)
    toc = ('<?xml version="1.0" encoding="utf-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head>'
           '<meta name="dtb:uid" content="%s"/></head><docTitle><text>%s</text></docTitle><navMap>%s</navMap></ncx>' % (uid, escape(book_title), ncx))
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>', zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", toc, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS, zipfile.ZIP_DEFLATED)
        for f, _, content in files:
            z.writestr("OEBPS/" + f, content, zipfile.ZIP_DEFLATED)


def main():
    src = os.environ.get("INPUT_PDF") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not src or not Path(src).is_file():
        sys.exit("Set INPUT_PDF in .env (or pass the PDF path as argument)")
    out_dir = Path(os.environ.get("OUTPUT_DIR", "output"))
    out_dir = out_dir if out_dir.is_absolute() else ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    exclude = [re.compile(p) for p in env_list("EXCLUDE_PATTERNS", ";;")]
    strip_pn = os.environ.get("STRIP_PAGE_NUMBERS", "false").lower() == "true"
    doc = pymupdf.open(src)
    footer, in_pdf, title_lines, scenes = build_scenes(doc, env_list("WATERMARK_TERMS"), strip_pn, exclude)
    book_title = os.environ.get("EPUB_TITLE") or " – ".join(title_lines[:2])
    author = os.environ.get("EPUB_AUTHOR") or next(
        (title_lines[i + 1] for i, t in enumerate(title_lines[:-1]) if t.lower() == "von"), "Unknown")
    out = out_dir / (Path(src).stem + ".epub")
    write_epub(out, title_lines, author, book_title, footer, scenes)
    print("wrote %s (%d scenes; footer %s)" % (out, len(scenes), "taken from PDF footer" if in_pdf else "created from watermark"))


if __name__ == "__main__":
    main()
