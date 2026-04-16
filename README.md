# eBook Bilingual Combine

Merge two editions of the same book into one bilingual output.

Supported inputs:

- `.epub`
- `.txt`
- `.md` / `.markdown`
- `.html` / `.htm` / `.xhtml`

Supported outputs:

- `.epub`
- `.md`
- `.txt`

No third-party runtime dependencies are required.

## Install

If you are not technical, follow these steps exactly.

### Option A: Clone with Git

1. Open Terminal.
2. Run:

```bash
cd ~
git clone https://github.com/hiddensev/ebook-bilingual-combine.git
cd ebook-bilingual-combine
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
```

If you are on Windows PowerShell, use this instead of `source .venv/bin/activate`:

```bash
.venv\Scripts\Activate.ps1
```

After that, run:

```bash
ebook-bilingual-combine
```

### Option B: Download ZIP instead of using Git

1. Open the GitHub page:

   `https://github.com/hiddensev/ebook-bilingual-combine`

2. Click `Code` -> `Download ZIP`.
3. Unzip the folder.
4. Open Terminal and enter that folder.
5. Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
ebook-bilingual-combine
```

### Notes

- Keep the terminal window open while using the tool.
- If you close the terminal and come back later, go back into the folder and run:

```bash
source .venv/bin/activate
```

- Then start the tool again with:

```bash
ebook-bilingual-combine
```

## How to Update

If you installed from a Git clone:

```bash
cd ~/ebook-bilingual-combine
git pull
source .venv/bin/activate
python3 -m pip install .
```

If you installed in editable mode before, this also works:

```bash
cd ~/ebook-bilingual-combine
git pull
source .venv/bin/activate
python3 -m pip install -e .
```

If you installed from a ZIP download, download the latest ZIP again, unzip it,
enter the new folder, and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
```

## Quick Start

The simplest usage is just:

```bash
ebook-bilingual-combine
```

This starts interactive mode. The tool will ask:

1. where the `Language A` eBook file is
2. where the `Language B` eBook file is

Then it will:

- create a per-run alignment config automatically
- try to merge the two books
- tell you where the output file was written
- ask you for help only if chapter pairing still needs manual input

By default, interactive mode writes its output, alignment config, and working
directory into the current directory.

You do not need to create a config file first for normal usage.

## What The Commands Mean

`ebook-bilingual-combine`

- the recommended mode
- enters the interactive question-and-answer flow
- treats the first input file as `Language A` and the second input file as `Language B`
- uses chapter order by default only when both sides already have the same chapter count
- best for normal users

`ebook-bilingual-combine inspect`

- an advanced debugging command
- shows the chapter list after cleanup and preprocessing
- useful if you want to see which chapters were skipped, how many paragraphs were kept, and where mismatches might come from

Example:

```bash
ebook-bilingual-combine inspect \
  "/path/to/book-a.epub" \
  "/path/to/book-b.epub" \
  --config alignment-config.json
```

`ebook-bilingual-combine init-config`

- an advanced setup command
- writes a reusable config template if you want to customize cleanup keywords yourself

Example:

```bash
ebook-bilingual-combine init-config \
  --config alignment-config.json \
  --language-a English \
  --language-b Chinese
```

`ebook-bilingual-combine merge`

- the advanced non-wizard command
- useful if you want full control over output path, config path, or work directory

Example:

```bash
ebook-bilingual-combine merge \
  "/path/to/book-a.epub" \
  "/path/to/book-b.epub" \
  --config alignment-config.json \
  --output merged-bilingual.epub \
  --work-dir merge-work \
  --language-a English \
  --language-b Chinese
```

## How It Works

- parses both books into chapters and paragraphs
- removes obvious structural noise such as `***`, empty paragraphs, and isolated reference-only blocks
- skips obvious non-main-content chapters such as contents, copyright pages, acknowledgments, story notes, and similar front/back matter
- trims likely trailing afterword / translator material appended to the end of chapters
- separates obvious trailing note blocks at chapter ends, such as a final `注释` heading followed by bracketed note paragraphs
- keeps those trailing notes in the final output, but excludes them from paragraph matching
- aligns chapters by paragraph count when possible
- if counts still differ, tries local paragraph-block alignment by length signals and automatically adopts the suggested paragraph ranges
- stores chapter pairings and paragraph alignments in a JSON config file

If both sides end up with the same number of chapters after obvious cleanup, the
tool pairs chapters by order.

If the chapter counts still differ, the tool does not try to guess where the
main text begins or ends. Instead, it shows both chapter lists and asks you for
chapter-pair anchors.

You do not need to enter every pair one by one. You can enter just the start
and end anchors of a continuous aligned block.

Example:

```text
3=2,26=25
```

`2=3` and `02=03` are treated the same way. The leading zero is only for
display in the chapter list.

This means:

- `Language A` chapter 3 matches `Language B` chapter 2
- `Language A` chapter 26 matches `Language B` chapter 25
- all chapters in between are expanded automatically in order

So the tool will infer:

- `4=3`
- `5=4`
- ...
- `25=24`

This is useful when one edition has extra prefaces, author pages, chronologies,
or appendices before or after the main text.

## Cleanup Rules

Cleanup rules are configurable through the JSON config file. You can add or remove:

- back matter markers
- non-main-content title keywords
- EPUB filename markers for front/back matter
- translator-credit suffixes

Start from [alignment-config.example.json](./alignment-config.example.json), or generate a fresh local config with `init-config`.

Example:

```json
{
  "cleanup": {
    "trailing_backmatter_markers_add": ["出版后记"],
    "backmatter_title_keywords_add": ["编者按"],
    "non_main_title_exact_remove": ["序"]
  }
}
```

## Automatic Alignment

When paragraph counts differ after cleanup, the tool keeps order fixed and tries local `N:M` matches up to `--max-auto-span`.

Typical cases:

- `1:1`
- `1:2`
- `2:1`
- `2:2`
- larger local blocks if you raise `--max-auto-span`

The score uses simple length-related signals instead of embeddings:

- meaningful character count
- English word count
- Chinese Han character count
- sentence count
- dialogue / speaker-label hints

This is meant to catch common editorial differences such as one long paragraph on one side being split into several shorter dialogue paragraphs on the other side.

## Manual Alignment

If the tool cannot produce any paragraph-range suggestion at all, it writes a review file under `merge-work/review/` so you can inspect the mismatch.

Example input:

```text
1=1,2-3=2,4=3-4
```

This means:

- paragraph 1 in source A matches paragraph 1 in source B
- paragraphs 2 to 3 in source A match paragraph 2 in source B
- paragraph 4 in source A matches paragraphs 3 to 4 in source B

The ranges must cover both chapters completely, stay continuous, and remain in order.

## Main Files

- [combine_books.py](./combine_books.py): main CLI module
- [alignment-config.example.json](./alignment-config.example.json): starter config example
- [pyproject.toml](./pyproject.toml): packaging and console-script entry point

## Development Notes

Direct script usage still works if you do not want to install the package:

```bash
python3 combine_books.py --help
```
