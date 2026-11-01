# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/), versioning follows [SemVer](https://semver.org/).

## [Unreleased]
### Added
- Buy Me a Coffee link in `README.md`.

## [0.2.1] - 2026-10-31
### Added
- `LICENSE` (GNU AGPL-3.0).
- `README.md` with a personal-use-only and intellectual-property notice, and `docs/HOW_IT_WORKS.md` (including why watermark auto-detection usually needs no configuration).

## [0.2.0] - 2026-10-31
### Added
- `src/convert.py`: PDF to EPUB converter. Removes only the diagonal watermark overlay and re-adds its text as a regular footer on every EPUB page (a matching PDF footer, if any, is used as the footer instead).
- Screenplay formatting (headings, action, dialogue, parentheticals, transitions), one chapter per scene with a table of contents.
- Optional `.env` settings: `EXCLUDE_PATTERNS`, `STRIP_PAGE_NUMBERS`, `EPUB_TITLE`, `EPUB_AUTHOR`.

## [0.1.0] - 2026-10-31
### Added
- Project scaffolding: launcher script, in-repo venv, `.env` configuration, changelog.
