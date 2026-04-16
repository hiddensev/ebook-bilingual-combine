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

## Quick Start

The simplest usage is just:

```bash
ebook-bilingual-combine
```

This starts interactive mode. The tool will ask:

1. what the first language is called
2. what the second language is called
3. where the first eBook file is
4. where the second eBook file is

Then it will:

- create a per-run alignment config automatically
- try to merge the two books
- tell you where the output file was written
- ask you for help only if chapter pairing or paragraph alignment still needs manual input

By default, interactive mode writes its output, alignment config, and working
directory into the current directory.

You do not need to create a config file first for normal usage.

## What The Commands Mean

`ebook-bilingual-combine`

- the recommended mode
- enters the interactive question-and-answer flow
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
- aligns chapters by paragraph count when possible
- if counts still differ, tries local paragraph-block alignment by length signals before asking for manual help
- stores chapter pairings and manual alignments in a JSON config file

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

If automatic alignment is still not confident enough, the tool writes a review file under `merge-work/review/` and prompts for manual ranges.

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
