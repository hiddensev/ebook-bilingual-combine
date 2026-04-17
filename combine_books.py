#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import sys
import textwrap
import uuid
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path

XHTML_NS = "http://www.w3.org/1999/xhtml"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
EPUB_NS = "http://www.idpf.org/2007/ops"
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"
XML_NS = "http://www.w3.org/XML/1998/namespace"

SOURCE_SUFFIXES = {
    ".epub",
    ".txt",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".xhtml",
}
TEXT_SUFFIXES = {".txt"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}
HTML_SUFFIXES = {".html", ".htm", ".xhtml"}
EPUB_OUTPUT_SUFFIXES = {".epub"}
TEXT_OUTPUT_SUFFIXES = {".txt"}
MARKDOWN_OUTPUT_SUFFIXES = {".md", ".markdown"}

DECORATIVE_SEPARATOR_RE = re.compile(r"^[\s\-\*=#_~·•●○◆◇※＊・—–…\.]+$")
ISOLATED_REFERENCE_RE = re.compile(r"^(?:\[\d+\]|\(\d+\)|\d+)$")
TRAILING_NOTE_HEADING_RE = re.compile(
    r"^\s*[\[【〔(（]?\s*(?:注释|尾注|注|notes?|endnotes?)\s*[:：]?\s*[\]】〕)）]?\s*$",
    re.IGNORECASE,
)
TRAILING_NOTE_PARAGRAPH_RE = re.compile(
    r"^\s*(?:"
    r"[\[【〔(（]\s*\d+\s*[\]】〕)）][\s.:：、]*"
    r"|"
    r"\d+\s*[\].．)、:：][\s]*"
    r"|"
    r"(?:注|注释)\s*[:：]"
    r")",
    re.IGNORECASE,
)
TEXT_CHAPTER_HEADING_RE = re.compile(
    r"^\s*(?:chapter|part|book)\b.*$|^\s*第[\d一二三四五六七八九十百千零〇两]+[章节卷部回篇].*$",
    re.IGNORECASE,
)
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,2})\s+(.*\S)\s*$")
TRAILING_BACKMATTER_MARKERS = [
    "后记",
    "译后记",
    "译者后记",
    "译者按",
    "译者说明",
    "译者序",
    "译者前言",
    "译者注",
    "译注",
    "编者按",
    "编后记",
    "附记",
    "跋",
    "致谢",
    "鸣谢",
    "注释",
    "尾注",
    "参考文献",
    "参考书目",
    "索引",
    "作者简介",
    "译者简介",
    "内容简介",
    "出版说明",
    "版权信息",
    "afterword",
    "translator's note",
    "translator’s note",
    "translator's preface",
    "translator’s preface",
    "note on the translation",
    "about the author",
    "about the translator",
    "acknowledgments",
    "acknowledgements",
    "notes",
    "endnotes",
    "bibliography",
    "references",
    "index",
    "glossary",
]
BACKMATTER_TITLE_KEYWORDS = [
    "story notes",
    "notes",
    "endnotes",
    "acknowledg",
    "publication history",
    "afterword",
    "bibliography",
    "references",
    "index",
    "glossary",
    "credits",
    "about the author",
    "about the translator",
    "note on the translation",
    "translator's note",
    "translator’s note",
    "注释",
    "尾注",
    "后记",
    "附记",
    "致谢",
    "鸣谢",
    "参考文献",
    "参考书目",
    "索引",
    "译者",
    "作者简介",
    "译者简介",
    "出版",
    "版权",
    "内容简介",
]
NON_MAIN_TITLE_EXACT = [
    "praise",
    "contents",
    "table of contents",
    "copyright",
    "cover",
    "dedication",
    "publication history",
    "story notes",
    "acknowledgments",
    "acknowledgements",
    "credits",
    "colophon",
    "title page",
    "half title",
    "also by",
    "other books by",
    "reading group guide",
    "discussion questions",
    "what's next on your reading list?",
    "what’s next on your reading list?",
    "版权信息",
    "版权页",
    "目录",
    "目录 contents",
    "注释",
    "后记",
    "译后记",
    "译者后记",
    "译者按",
    "译者说明",
    "译者序",
    "译序",
    "译者前言",
    "前言",
    "导言",
    "序言",
    "序",
    "跋",
    "致谢",
    "鸣谢",
    "作者简介",
    "译者简介",
    "出版说明",
    "内容简介",
    "凡例",
    "扉页",
    "书名页",
    "献词",
    "献辞",
]
NON_MAIN_TITLE_PREFIXES = [
    "praise for ",
    "about the author",
    "about the translator",
    "other books by ",
    "also by ",
    "出版",
    "译者",
]
NON_MAIN_TITLE_SUBSTRINGS = [
    "ted chiang",
]
EPUB_NON_MAIN_FILE_MARKERS = [
    "titlepage.xhtml",
    "cover_page.xhtml",
    "next-reads",
    "/fm",
    "_fm",
    "-fm",
    "/ata",
    "_ata",
    "-ata",
    "/tp",
    "_tp",
    "-tp",
    "/cop",
    "_cop",
    "-cop",
    "/ded",
    "_ded",
    "-ded",
    "/toc",
    "_toc",
    "-toc",
    "/bm",
    "_bm",
    "-bm",
    "/ack",
    "_ack",
    "-ack",
    "copyright",
    "colophon",
    "imprint",
]
TRANSLATOR_CREDIT_SUFFIXES = [
    "译",
    "译注",
    "编译",
    "校译",
    "审校",
    "编",
    "注",
    "导读",
]
CLEANUP_TERM_KEYS = [
    "trailing_backmatter_markers",
    "backmatter_title_keywords",
    "non_main_title_exact",
    "non_main_title_prefixes",
    "non_main_title_substrings",
    "epub_non_main_file_markers",
    "translator_credit_suffixes",
]


def compile_exact_title_regex(terms: list[str]) -> re.Pattern[str]:
    escaped = "|".join(re.escape(term) for term in terms)
    return re.compile(rf"^\s*(?:{escaped})\s*$", re.IGNORECASE)


def compile_contains_regex(terms: list[str]) -> re.Pattern[str]:
    escaped = "|".join(re.escape(term) for term in terms)
    return re.compile(rf"(?:{escaped})", re.IGNORECASE)


def compile_prefix_regex(terms: list[str]) -> re.Pattern[str]:
    escaped = "|".join(re.escape(term) for term in terms)
    return re.compile(rf"^\s*(?:{escaped})", re.IGNORECASE)


def compile_trailing_backmatter_marker_regex(terms: list[str]) -> re.Pattern[str]:
    escaped = "|".join(re.escape(term) for term in terms)
    return re.compile(rf"^\[?\s*(?:{escaped})\s*\]?$", re.IGNORECASE)


def compile_translator_credit_regex(suffixes: list[str]) -> re.Pattern[str]:
    escaped_suffixes = "|".join(re.escape(term) for term in suffixes)
    return re.compile(
        rf"^(?:translated by\s+.+|translator\s*[:：].+|"
        rf"[A-Za-z\u4e00-\u9fff·•\s]{{1,30}}\s*(?:{escaped_suffixes}))$",
        re.IGNORECASE,
    )
LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
MEANINGFUL_CHAR_RE = re.compile(r"[A-Za-z0-9\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
SENTENCE_END_RE = re.compile(r"[.!?。！？]+")

ET.register_namespace("", XHTML_NS)
ET.register_namespace("epub", EPUB_NS)


@dataclass
class Paragraph:
    index: int
    source_index: int
    html: str
    text: str


@dataclass
class RemovedParagraph:
    source_index: int
    text: str
    reason: str


@dataclass
class Chapter:
    order: int
    spine_order: int
    href: str
    title: str
    paragraphs: list[Paragraph]
    trailing_note_paragraphs: list[Paragraph]
    removed_paragraphs: list[RemovedParagraph]

    @property
    def paragraph_count(self) -> int:
        return len(self.paragraphs)


@dataclass
class SkippedChapter:
    href: str
    title: str
    reason: str


@dataclass
class Book:
    path: Path
    title: str
    creator: str
    language: str
    source_format: str
    chapters: list[Chapter]
    skipped_chapters: list[SkippedChapter]

    @property
    def chapters_by_href(self) -> dict[str, Chapter]:
        return {chapter.href: chapter for chapter in self.chapters}

    @property
    def skipped_by_href(self) -> dict[str, SkippedChapter]:
        return {chapter.href: chapter for chapter in self.skipped_chapters}


@dataclass
class MergedSegment:
    index: int
    paragraphs_a: list[Paragraph]
    paragraphs_b: list[Paragraph]


@dataclass
class MergedChapter:
    index: int
    title: str
    segments: list[MergedSegment]
    trailing_note_paragraphs_a: list[Paragraph]
    trailing_note_paragraphs_b: list[Paragraph]


@dataclass(frozen=True)
class AlignmentFeatures:
    meaningful_chars: int
    sentence_count: int
    speaker_labels: int
    dialogue_paragraphs: int


@dataclass
class AutoAlignmentResult:
    alignments: list[dict]
    total_cost: float
    average_cost: float
    max_segment_cost: float


@dataclass(frozen=True)
class CleanupRules:
    trailing_backmatter_marker_re: re.Pattern[str]
    backmatter_title_re: re.Pattern[str]
    non_main_title_exact_re: re.Pattern[str]
    non_main_title_prefix_re: re.Pattern[str]
    non_main_title_contains_re: re.Pattern[str]
    epub_non_main_file_re: re.Pattern[str]
    translator_credit_re: re.Pattern[str]


class AlignmentError(Exception):
    pass


def html_qname(tag: str) -> str:
    return f"{{{XHTML_NS}}}{tag}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def default_cleanup_config() -> dict:
    cleanup = {}
    for key in CLEANUP_TERM_KEYS:
        cleanup[f"{key}_add"] = []
        cleanup[f"{key}_remove"] = []
    return cleanup


def normalize_term_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        folded = text.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        normalized.append(text)
    return normalized


def merge_cleanup_terms(
    default_terms: list[str],
    cleanup_config: dict,
    key: str,
) -> list[str]:
    remove_values = {
        term.casefold()
        for term in normalize_term_list(cleanup_config.get(f"{key}_remove"))
    }
    merged: list[str] = []
    seen: set[str] = set()
    for term in default_terms + normalize_term_list(cleanup_config.get(f"{key}_add")):
        folded = term.casefold()
        if folded in remove_values or folded in seen:
            continue
        seen.add(folded)
        merged.append(term)
    return merged


def ensure_cleanup_config(config: dict) -> dict:
    cleanup = config.setdefault("cleanup", {})
    defaults = default_cleanup_config()
    for key, default_value in defaults.items():
        cleanup[key] = normalize_term_list(cleanup.get(key, default_value))
    return cleanup


def build_cleanup_rules(config: dict) -> CleanupRules:
    cleanup = ensure_cleanup_config(config)
    trailing_backmatter_markers = merge_cleanup_terms(
        TRAILING_BACKMATTER_MARKERS,
        cleanup,
        "trailing_backmatter_markers",
    )
    backmatter_title_keywords = merge_cleanup_terms(
        BACKMATTER_TITLE_KEYWORDS,
        cleanup,
        "backmatter_title_keywords",
    )
    non_main_title_exact = merge_cleanup_terms(
        NON_MAIN_TITLE_EXACT,
        cleanup,
        "non_main_title_exact",
    )
    non_main_title_prefixes = merge_cleanup_terms(
        NON_MAIN_TITLE_PREFIXES,
        cleanup,
        "non_main_title_prefixes",
    )
    non_main_title_substrings = merge_cleanup_terms(
        NON_MAIN_TITLE_SUBSTRINGS,
        cleanup,
        "non_main_title_substrings",
    )
    epub_non_main_file_markers = merge_cleanup_terms(
        EPUB_NON_MAIN_FILE_MARKERS,
        cleanup,
        "epub_non_main_file_markers",
    )
    translator_credit_suffixes = merge_cleanup_terms(
        TRANSLATOR_CREDIT_SUFFIXES,
        cleanup,
        "translator_credit_suffixes",
    )
    return CleanupRules(
        trailing_backmatter_marker_re=compile_trailing_backmatter_marker_regex(
            trailing_backmatter_markers
        ),
        backmatter_title_re=compile_contains_regex(backmatter_title_keywords),
        non_main_title_exact_re=compile_exact_title_regex(non_main_title_exact),
        non_main_title_prefix_re=compile_prefix_regex(non_main_title_prefixes),
        non_main_title_contains_re=compile_contains_regex(non_main_title_substrings),
        epub_non_main_file_re=compile_contains_regex(epub_non_main_file_markers),
        translator_credit_re=compile_translator_credit_regex(
            translator_credit_suffixes
        ),
    )


def default_config(label_a: str, label_b: str) -> dict:
    return {
        "version": 1,
        "language_a": label_a,
        "language_b": label_b,
        "cleanup": default_cleanup_config(),
        "chapter_pairs": [],
    }


def get_config_language_names(config: dict) -> tuple[str, str]:
    language_a = (
        config.get("language_a")
        or config.get("language_a_label")
        or "Language A"
    )
    language_b = (
        config.get("language_b")
        or config.get("language_b_label")
        or "Language B"
    )
    return str(language_a), str(language_b)


def set_config_language_names(config: dict, language_a: str, language_b: str) -> None:
    config["language_a"] = language_a
    config["language_b"] = language_b
    config.pop("language_a_label", None)
    config.pop("language_b_label", None)


def strip_namespaces(element: ET.Element) -> None:
    if "}" in element.tag:
        namespace, local_name = element.tag[1:].split("}", 1)
        if namespace == EPUB_NS:
            element.tag = f"epub:{local_name}"
        elif namespace == XML_NS:
            element.tag = f"xml:{local_name}"
        else:
            element.tag = local_name

    for attribute in list(element.attrib):
        if "}" not in attribute:
            continue
        value = element.attrib.pop(attribute)
        namespace, local_name = attribute[1:].split("}", 1)
        if namespace == EPUB_NS:
            element.attrib[f"epub:{local_name}"] = value
        elif namespace == XML_NS:
            element.attrib[f"xml:{local_name}"] = value
        else:
            element.attrib[local_name] = value

    for child in element:
        strip_namespaces(child)


def is_external_reference(ref: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", ref))


def sanitize_embedded_links(element: ET.Element) -> None:
    href = element.attrib.get("href")
    if href:
        target = href.split("#", 1)[0].strip()
        if target and not is_external_reference(target):
            element.attrib.pop("href", None)
            if element.tag == "a":
                element.tag = "span"

    for child in element:
        sanitize_embedded_links(child)


def serialize_xhtml_fragment(element: ET.Element) -> str:
    clone = copy.deepcopy(element)
    strip_namespaces(clone)
    sanitize_embedded_links(clone)
    return ET.tostring(clone, encoding="unicode", method="xml")


def paragraph_from_text(source_index: int, text: str) -> Paragraph:
    escaped = html_escape(text)
    return Paragraph(
        index=source_index,
        source_index=source_index,
        html=f"<p>{escaped}</p>",
        text=text,
    )


def extract_title_from_document(document: ET.Element, fallback: str) -> str:
    body = document.find(f".//{html_qname('body')}")
    if body is not None:
        leading_headings: list[str] = []
        for child in list(body):
            tag = child.tag
            if tag in {
                html_qname("h1"),
                html_qname("h2"),
                html_qname("h3"),
            }:
                text = normalize_text("".join(child.itertext()))
                if text:
                    leading_headings.append(text)
                continue
            if leading_headings:
                break
            if normalize_text("".join(child.itertext())):
                break

        if leading_headings:
            if len(leading_headings) == 1:
                return leading_headings[0]
            return ": ".join(leading_headings)

    for tag in ("h1", "h2", "h3", "title"):
        element = document.find(f".//{html_qname(tag)}")
        if element is None:
            continue
        text = normalize_text("".join(element.itertext()))
        if text:
            return text
    return fallback


def normalize_epub_href(base_dir: str, ref: str) -> str | None:
    target = ref.split("#", 1)[0].strip()
    if not target:
        return None
    return os.path.normpath(os.path.join(base_dir, target))


def extract_nav_titles_from_nav_document(
    document: ET.Element,
    nav_dir: str,
) -> dict[str, str]:
    titles: dict[str, str] = {}
    for nav in document.findall(f".//{html_qname('nav')}"):
        nav_type = (
            nav.attrib.get(f"{{{EPUB_NS}}}type")
            or nav.attrib.get("type")
            or ""
        )
        if "toc" not in nav_type.casefold():
            continue
        for anchor in nav.findall(f".//{html_qname('a')}"):
            href = anchor.attrib.get("href", "")
            normalized_href = normalize_epub_href(nav_dir, href)
            if not normalized_href:
                continue
            text = normalize_text("".join(anchor.itertext()))
            if text and normalized_href not in titles:
                titles[normalized_href] = text
    return titles


def extract_nav_titles_from_ncx(document: ET.Element, nav_dir: str) -> dict[str, str]:
    titles: dict[str, str] = {}
    for nav_point in document.findall(f".//{{{NCX_NS}}}navPoint"):
        label = nav_point.find(f"./{{{NCX_NS}}}navLabel/{{{NCX_NS}}}text")
        content = nav_point.find(f"./{{{NCX_NS}}}content")
        if label is None or content is None:
            continue
        href = content.attrib.get("src", "")
        normalized_href = normalize_epub_href(nav_dir, href)
        if not normalized_href:
            continue
        text = normalize_text("".join(label.itertext()))
        if text and normalized_href not in titles:
            titles[normalized_href] = text
    return titles


def extract_epub_navigation_titles(
    archive: zipfile.ZipFile,
    package: ET.Element,
    opf_dir: str,
) -> dict[str, str]:
    ns = {"opf": OPF_NS}
    titles: dict[str, str] = {}

    for item in package.findall("opf:manifest/opf:item", ns):
        href = item.attrib.get("href", "")
        media_type = item.attrib.get("media-type", "")
        full_path = normalize_epub_href(opf_dir, href)
        if not full_path:
            continue
        nav_dir = os.path.dirname(full_path)

        if "nav" in item.attrib.get("properties", "").split():
            try:
                document = ET.fromstring(archive.read(full_path))
            except KeyError:
                continue
            titles.update(extract_nav_titles_from_nav_document(document, nav_dir))
            continue

        if media_type == "application/x-dtbncx+xml":
            try:
                document = ET.fromstring(archive.read(full_path))
            except KeyError:
                continue
            for normalized_href, text in extract_nav_titles_from_ncx(
                document,
                nav_dir,
            ).items():
                titles.setdefault(normalized_href, text)

    return titles


def extract_xhtml_paragraphs(root: ET.Element) -> list[Paragraph]:
    body = root.find(f".//{html_qname('body')}")
    if body is None:
        return []

    paragraphs: list[Paragraph] = []
    for source_index, paragraph in enumerate(
        body.findall(f".//{html_qname('p')}"),
        start=1,
    ):
        text = normalize_text("".join(paragraph.itertext()))
        paragraphs.append(
            Paragraph(
                index=source_index,
                source_index=source_index,
                html=serialize_xhtml_fragment(paragraph),
                text=text,
            )
        )
    return paragraphs


def is_backmatter_title(title: str, cleanup_rules: CleanupRules) -> bool:
    return bool(cleanup_rules.backmatter_title_re.search(title))


def non_main_chapter_reason(
    title: str,
    cleanup_rules: CleanupRules,
    href: str = "",
    paragraph_count: int = 0,
    book_title: str = "",
) -> str | None:
    if cleanup_rules.non_main_title_exact_re.search(title):
        return "non_main_content"
    if cleanup_rules.non_main_title_prefix_re.search(title):
        return "non_main_content"
    if cleanup_rules.non_main_title_contains_re.search(title):
        return "non_main_content"
    href_name = Path(href).name
    if href_name and cleanup_rules.epub_non_main_file_re.search(href_name):
        return "non_main_content"
    normalized_title = normalize_text(title).casefold()
    normalized_book_title = normalize_text(book_title).casefold()
    if (
        normalized_title
        and normalized_book_title
        and normalized_title == normalized_book_title
        and paragraph_count <= 20
    ):
        return "non_main_content"
    if normalized_title == Path(href).stem.casefold() and paragraph_count <= 3:
        return "non_main_content"
    return None


def classify_structural_noise(text: str) -> str | None:
    if not text:
        return "empty"
    compact = text.replace(" ", "")
    if len(compact) <= 24 and DECORATIVE_SEPARATOR_RE.fullmatch(text):
        return "decorative_separator"
    if len(compact) <= 12 and ISOLATED_REFERENCE_RE.fullmatch(text):
        return "isolated_reference"
    return None


def is_note_heading_paragraph(text: str) -> bool:
    return bool(TRAILING_NOTE_HEADING_RE.fullmatch(text))


def is_note_content_paragraph(text: str) -> bool:
    return bool(TRAILING_NOTE_PARAGRAPH_RE.match(text))


def find_trailing_note_cutoff(paragraphs: list[Paragraph]) -> int | None:
    if len(paragraphs) < 2:
        return None

    # Case 1: an explicit note heading like "注释" or "【注释】" appears near the end.
    search_start = max(0, len(paragraphs) // 2)
    for index in range(search_start, len(paragraphs) - 1):
        if not is_note_heading_paragraph(paragraphs[index].text):
            continue
        tail = paragraphs[index + 1 :]
        if tail and all(is_note_content_paragraph(paragraph.text) for paragraph in tail):
            return index

    # Case 2: the chapter ends with a contiguous run of numbered note paragraphs.
    tail_start: int | None = None
    for index in range(len(paragraphs) - 1, -1, -1):
        if is_note_content_paragraph(paragraphs[index].text):
            tail_start = index
            continue
        break

    if tail_start is None:
        return None

    tail_length = len(paragraphs) - tail_start
    if tail_length >= 2:
        return tail_start
    return None


def find_trailing_backmatter_cutoff(
    chapter_title: str,
    paragraphs: list[Paragraph],
    cleanup_rules: CleanupRules,
) -> int | None:
    if is_backmatter_title(chapter_title, cleanup_rules) or not paragraphs:
        return None

    search_start = max(0, len(paragraphs) // 2)
    for index in range(search_start, len(paragraphs)):
        if cleanup_rules.trailing_backmatter_marker_re.fullmatch(paragraphs[index].text):
            return index
    return None


def normalize_paragraphs(
    chapter_title: str,
    raw_paragraphs: list[Paragraph],
    cleanup_rules: CleanupRules,
) -> tuple[list[Paragraph], list[Paragraph], list[RemovedParagraph]]:
    kept: list[Paragraph] = []
    trailing_notes: list[Paragraph] = []
    removed: list[RemovedParagraph] = []

    for paragraph in raw_paragraphs:
        reason = classify_structural_noise(paragraph.text)
        if reason is not None:
            removed.append(
                RemovedParagraph(
                    source_index=paragraph.source_index,
                    text=paragraph.text,
                    reason=reason,
                )
            )
            continue
        kept.append(paragraph)

    note_cutoff = find_trailing_note_cutoff(kept)
    if note_cutoff is not None:
        trailing_notes = kept[note_cutoff:]
        kept = kept[:note_cutoff]

    cutoff = find_trailing_backmatter_cutoff(chapter_title, kept, cleanup_rules)
    if cutoff is not None:
        for paragraph in kept[cutoff:]:
            removed.append(
                RemovedParagraph(
                    source_index=paragraph.source_index,
                    text=paragraph.text,
                    reason="trailing_backmatter",
                )
            )
        kept = kept[:cutoff]

    while kept and cleanup_rules.translator_credit_re.fullmatch(kept[-1].text):
        paragraph = kept.pop()
        removed.append(
            RemovedParagraph(
                source_index=paragraph.source_index,
                text=paragraph.text,
                reason="translator_credit",
            )
        )

    normalized: list[Paragraph] = []
    for index, paragraph in enumerate(kept, start=1):
        normalized.append(
            Paragraph(
                index=index,
                source_index=paragraph.source_index,
                html=paragraph.html,
                text=paragraph.text,
            )
        )

    normalized_trailing_notes: list[Paragraph] = []
    for index, paragraph in enumerate(trailing_notes, start=1):
        normalized_trailing_notes.append(
            Paragraph(
                index=index,
                source_index=paragraph.source_index,
                html=paragraph.html,
                text=paragraph.text,
            )
        )

    removed.sort(key=lambda item: item.source_index)
    return normalized, normalized_trailing_notes, removed


def build_chapter(
    order: int,
    spine_order: int,
    href: str,
    title: str,
    raw_paragraphs: list[Paragraph],
    cleanup_rules: CleanupRules,
) -> Chapter | None:
    paragraphs, trailing_notes, removed = normalize_paragraphs(
        title,
        raw_paragraphs,
        cleanup_rules,
    )
    if not paragraphs:
        return None
    return Chapter(
        order=order,
        spine_order=spine_order,
        href=href,
        title=title,
        paragraphs=paragraphs,
        trailing_note_paragraphs=trailing_notes,
        removed_paragraphs=removed,
    )


def load_epub_book(path: Path, cleanup_rules: CleanupRules) -> Book:
    with zipfile.ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find(
            f"{{{CONTAINER_NS}}}rootfiles/{{{CONTAINER_NS}}}rootfile"
        )
        if rootfile is None:
            raise AlignmentError(f"Could not find OPF path in {path}")

        opf_path = rootfile.attrib["full-path"]
        opf_dir = os.path.dirname(opf_path)
        package = ET.fromstring(archive.read(opf_path))
        ns = {"opf": OPF_NS, "dc": DC_NS}

        title = package.findtext("opf:metadata/dc:title", "", namespaces=ns).strip()
        creator = package.findtext("opf:metadata/dc:creator", "", namespaces=ns).strip()
        language = package.findtext("opf:metadata/dc:language", "", namespaces=ns).strip()

        manifest = {
            item.attrib["id"]: item.attrib
            for item in package.findall("opf:manifest/opf:item", ns)
        }
        spine = package.findall("opf:spine/opf:itemref", ns)
        nav_titles = extract_epub_navigation_titles(archive, package, opf_dir)

        chapters: list[Chapter] = []
        skipped_chapters: list[SkippedChapter] = []
        for spine_order, itemref in enumerate(spine, start=1):
            item = manifest.get(itemref.attrib["idref"])
            if item is None:
                continue
            if item.get("media-type") not in {"application/xhtml+xml", "text/html"}:
                continue

            href = os.path.normpath(os.path.join(opf_dir, item["href"]))
            document = ET.fromstring(archive.read(href))
            raw_paragraphs = extract_xhtml_paragraphs(document)
            chapter_title = nav_titles.get(href) or extract_title_from_document(
                document,
                Path(href).stem,
            )
            chapter = build_chapter(
                order=len(chapters) + 1,
                spine_order=spine_order,
                href=href,
                title=chapter_title,
                raw_paragraphs=raw_paragraphs,
                cleanup_rules=cleanup_rules,
            )
            if chapter is not None:
                chapters.append(chapter)

    return Book(
        path=path,
        title=title or path.stem,
        creator=creator,
        language=language or "und",
        source_format="epub",
        chapters=chapters,
        skipped_chapters=skipped_chapters,
    )


def split_plain_paragraphs(text: str) -> list[str]:
    chunks = re.split(r"\n\s*\n+", text.strip())
    return [normalize_text(chunk) for chunk in chunks if normalize_text(chunk)]


def split_markdown_sections(text: str, default_title: str) -> list[tuple[str, str]]:
    text = text.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5 :]

    sections: list[tuple[str, list[str]]] = []
    current_title = default_title
    current_lines: list[str] = []
    saw_heading = False

    for line in text.splitlines():
        match = MARKDOWN_HEADING_RE.match(line)
        if match is not None:
            saw_heading = True
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = match.group(2).strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines or not saw_heading:
        sections.append((current_title, current_lines))

    normalized: list[tuple[str, str]] = []
    for title, lines in sections:
        body = "\n".join(lines).strip()
        if body:
            normalized.append((title, body))
    return normalized or [(default_title, text)]


def split_text_sections(text: str, default_title: str) -> list[tuple[str, str]]:
    text = text.replace("\r\n", "\n")
    sections: list[tuple[str, list[str]]] = []
    current_title = default_title
    current_lines: list[str] = []
    saw_heading = False

    for line in text.splitlines():
        if TEXT_CHAPTER_HEADING_RE.match(line.strip()):
            saw_heading = True
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line.strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines or not saw_heading:
        sections.append((current_title, current_lines))

    normalized: list[tuple[str, str]] = []
    for title, lines in sections:
        body = "\n".join(lines).strip()
        if body:
            normalized.append((title, body))
    return normalized or [(default_title, text)]


def load_plain_text_book(
    path: Path,
    source_format: str,
    cleanup_rules: CleanupRules,
) -> Book:
    text = path.read_text(encoding="utf-8")
    if source_format == "markdown":
        sections = split_markdown_sections(text, path.stem)
    else:
        sections = split_text_sections(text, path.stem)

    chapters: list[Chapter] = []
    skipped_chapters: list[SkippedChapter] = []
    for index, (title, body) in enumerate(sections, start=1):
        raw_paragraphs = [
            paragraph_from_text(source_index, paragraph_text)
            for source_index, paragraph_text in enumerate(
                split_plain_paragraphs(body),
                start=1,
            )
        ]
        chapter = build_chapter(
            order=len(chapters) + 1,
            spine_order=index,
            href=f"section-{index:02d}",
            title=title,
            raw_paragraphs=raw_paragraphs,
            cleanup_rules=cleanup_rules,
        )
        if chapter is not None:
            chapters.append(chapter)

    return Book(
        path=path,
        title=path.stem,
        creator="",
        language="und",
        source_format=source_format,
        chapters=chapters,
        skipped_chapters=skipped_chapters,
    )


def load_html_book(path: Path, cleanup_rules: CleanupRules) -> Book:
    document = ET.fromstring(path.read_bytes())
    body = document.find(f".//{html_qname('body')}")
    if body is None:
        raise AlignmentError(f"No <body> found in {path}")

    fallback_title = extract_title_from_document(document, path.stem)
    sections: list[tuple[str, list[Paragraph]]] = []
    current_title = fallback_title
    current_paragraphs: list[Paragraph] = []
    next_paragraph_index = 1

    for node in body.iter():
        local_tag = node.tag.split("}", 1)[-1] if "}" in node.tag else node.tag
        if local_tag in {"h1", "h2"}:
            title = normalize_text("".join(node.itertext()))
            if title:
                if current_paragraphs:
                    sections.append((current_title, current_paragraphs))
                current_title = title
                current_paragraphs = []
                next_paragraph_index = 1
            continue
        if local_tag != "p":
            continue
        text = normalize_text("".join(node.itertext()))
        current_paragraphs.append(
            Paragraph(
                index=next_paragraph_index,
                source_index=next_paragraph_index,
                html=serialize_xhtml_fragment(node),
                text=text,
            )
        )
        next_paragraph_index += 1

    if current_paragraphs:
        sections.append((current_title, current_paragraphs))

    chapters: list[Chapter] = []
    skipped_chapters: list[SkippedChapter] = []
    for index, (title, raw_paragraphs) in enumerate(sections, start=1):
        chapter = build_chapter(
            order=len(chapters) + 1,
            spine_order=index,
            href=f"section-{index:02d}",
            title=title,
            raw_paragraphs=raw_paragraphs,
            cleanup_rules=cleanup_rules,
        )
        if chapter is not None:
            chapters.append(chapter)

    return Book(
        path=path,
        title=fallback_title,
        creator="",
        language="und",
        source_format="html",
        chapters=chapters,
        skipped_chapters=skipped_chapters,
    )


def load_book(path: Path, cleanup_rules: CleanupRules) -> Book:
    suffix = path.suffix.lower()
    if suffix == ".epub":
        return load_epub_book(path, cleanup_rules)
    if suffix in TEXT_SUFFIXES:
        return load_plain_text_book(path, "text", cleanup_rules)
    if suffix in MARKDOWN_SUFFIXES:
        return load_plain_text_book(path, "markdown", cleanup_rules)
    if suffix in HTML_SUFFIXES:
        return load_html_book(path, cleanup_rules)
    raise AlignmentError(
        f"Unsupported input format '{suffix}'. Supported formats: "
        + ", ".join(sorted(SOURCE_SUFFIXES))
    )


def load_config(config_path: Path, label_a: str, label_b: str) -> dict:
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = default_config(label_a, label_b)
    config.setdefault("version", 1)
    config.setdefault("chapter_pairs", [])
    existing_a, existing_b = get_config_language_names(config)
    set_config_language_names(
        config,
        existing_a if existing_a else label_a,
        existing_b if existing_b else label_b,
    )
    ensure_cleanup_config(config)
    return config


def save_config(config_path: Path, config: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def prompt_for_path(prompt_text: str) -> Path:
    while True:
        raw = input(prompt_text).strip()
        if not raw:
            print("  A path is required.")
            continue
        path = Path(raw).expanduser()
        if not path.exists():
            print(f"  File does not exist: {path}")
            continue
        if not path.is_file():
            print(f"  Not a file: {path}")
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            print(
                "  Unsupported format. Supported input formats: "
                + ", ".join(sorted(SOURCE_SUFFIXES))
            )
            continue
        return path


def resolve_source_path(provided: Path | None, prompt_text: str) -> Path:
    if provided is not None:
        path = provided.expanduser()
        if not path.exists():
            raise AlignmentError(f"File does not exist: {path}")
        if not path.is_file():
            raise AlignmentError(f"Not a file: {path}")
        return path
    return prompt_for_path(prompt_text)


def sanitize_output_stem(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", name).strip("-")
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    return (sanitized[:60] or "merged-bilingual").strip("-")


def inspect_books(book_a: Book, book_b: Book) -> None:
    for label, book in (("Source A", book_a), ("Source B", book_b)):
        print(f"{label}: {book.path.name}")
        print(f"  Format: {book.source_format}")
        print(f"  Title: {book.title}")
        print(f"  Creator: {book.creator or 'Unknown'}")
        print(f"  Language: {book.language or 'und'}")
        print("  Normalized chapters:")
        for chapter in book.chapters:
            removed = len(chapter.removed_paragraphs)
            notes = len(chapter.trailing_note_paragraphs)
            details: list[str] = []
            if removed:
                details.append(f"{removed} removed")
            if notes:
                details.append(f"{notes} trailing notes")
            suffix = f", {', '.join(details)}" if details else ""
            print(
                f"    {chapter.order:02d}. {chapter.title} "
                f"({chapter.paragraph_count} kept{suffix}) [{chapter.href}]"
            )
        if book.skipped_chapters:
            print("  Skipped non-main chapters:")
            for chapter in book.skipped_chapters:
                print(
                    f"    - {chapter.title} [{chapter.reason}] [{chapter.href}]"
                )
        print()


def resolve_chapter_pairs(
    book_a: Book,
    book_b: Book,
    config: dict,
    interactive: bool,
) -> list[dict]:
    configured_pairs = config.get("chapter_pairs", [])
    if configured_pairs and not interactive:
        validated = validate_chapter_pairs(book_a, book_b, configured_pairs)
        config["chapter_pairs"] = validated
        return validated

    if interactive and configured_pairs:
        config["chapter_pairs"] = []

    if not interactive:
        raise AlignmentError(
            "No chapter pairs are defined in the config. Run interactively first or "
            "add chapter_pairs to the config JSON."
        )

    print()
    print("Chapter pairing is not configured yet.")
    print("Use the chapter lists below to define the matching range.")
    print()
    print("Source A chapters:")
    for chapter in book_a.chapters:
        removed = len(chapter.removed_paragraphs)
        suffix = f", {removed} removed" if removed else ""
        print(
            f"  {chapter.order:02d} = {chapter.title} "
            f"({chapter.paragraph_count} kept{suffix})"
        )

    print()
    print("Source B chapters:")
    for chapter in book_b.chapters:
        removed = len(chapter.removed_paragraphs)
        suffix = f", {removed} removed" if removed else ""
        print(
            f"  {chapter.order:02d} = {chapter.title} "
            f"({chapter.paragraph_count} kept{suffix})"
        )

    print()
    print("Enter the start and end chapter anchors as A=B.")
    print("Example start anchor: 4=2")
    print("Example end anchor: 24=22")
    print("The tool will expand all chapters in between in order.")
    start_anchor = input("Starting chapter anchor (A=B): ").strip()
    end_anchor = input("Ending chapter anchor (A=B): ").strip()
    raw = f"{start_anchor},{end_anchor}"
    pairs = parse_chapter_pairs(raw, book_a, book_b)
    config["chapter_pairs"] = pairs
    return pairs


def validate_chapter_pairs(book_a: Book, book_b: Book, pairs: list[dict]) -> list[dict]:
    chapters_a = book_a.chapters_by_href
    chapters_b = book_b.chapters_by_href
    skipped_a = book_a.skipped_by_href
    skipped_b = book_b.skipped_by_href

    validated: list[dict] = []
    for index, pair in enumerate(pairs, start=1):
        href_a = pair.get("a_href")
        href_b = pair.get("b_href")
        if href_a not in chapters_a:
            if href_a in skipped_a:
                raise AlignmentError(
                    f"Config chapter in source A was skipped as non-main content: "
                    f"{skipped_a[href_a].title}"
                )
            raise AlignmentError(f"Config chapter not found in source A: {href_a}")
        if href_b not in chapters_b:
            if href_b in skipped_b:
                raise AlignmentError(
                    f"Config chapter in source B was skipped as non-main content: "
                    f"{skipped_b[href_b].title}"
                )
            raise AlignmentError(f"Config chapter not found in source B: {href_b}")
        chapter_a = chapters_a[href_a]
        chapter_b = chapters_b[href_b]
        validated.append(
            {
                "id": pair.get("id", f"chapter-{index:02d}"),
                "a_href": href_a,
                "b_href": href_b,
                "title": pair.get("title")
                or f"{chapter_a.title} / {chapter_b.title}",
                "alignments": pair.get("alignments", []),
            }
        )
    return validated


def parse_chapter_pairs(raw: str, book_a: Book, book_b: Book) -> list[dict]:
    if not raw:
        raise AlignmentError("No chapter pairs were provided.")

    anchors: list[tuple[int, int]] = []
    seen_a: set[int] = set()
    seen_b: set[int] = set()

    for chunk in raw.split(","):
        chunk = chunk.strip()
        match = re.fullmatch(r"(\d+)\s*=\s*(\d+)", chunk)
        if match is None:
            raise AlignmentError(
                f"Invalid chapter pair '{chunk}'. Expected entries like 4=1."
            )

        chapter_a_index = int(match.group(1))
        chapter_b_index = int(match.group(2))
        if chapter_a_index in seen_a:
            raise AlignmentError(f"Source A chapter {chapter_a_index} is paired twice.")
        if chapter_b_index in seen_b:
            raise AlignmentError(f"Source B chapter {chapter_b_index} is paired twice.")
        if chapter_a_index < 1 or chapter_a_index > len(book_a.chapters):
            raise AlignmentError(f"Source A chapter index out of range: {chapter_a_index}")
        if chapter_b_index < 1 or chapter_b_index > len(book_b.chapters):
            raise AlignmentError(f"Source B chapter index out of range: {chapter_b_index}")

        seen_a.add(chapter_a_index)
        seen_b.add(chapter_b_index)

        if anchors and (
            chapter_a_index <= anchors[-1][0] or chapter_b_index <= anchors[-1][1]
        ):
            raise AlignmentError("Chapter pair anchors must be strictly increasing.")
        anchors.append((chapter_a_index, chapter_b_index))

    expanded_pairs: list[tuple[int, int]] = []
    for index, (chapter_a_index, chapter_b_index) in enumerate(anchors):
        if index == 0:
            expanded_pairs.append((chapter_a_index, chapter_b_index))
            continue

        prev_a, prev_b = anchors[index - 1]
        gap_a = chapter_a_index - prev_a
        gap_b = chapter_b_index - prev_b
        if gap_a != gap_b:
            raise AlignmentError(
                "Anchor pairs must preserve the same chapter distance. "
                "For example, 2=3,25=26 is valid, but 2=3,25=27 is not."
            )
        for offset in range(1, gap_a + 1):
            expanded_pairs.append((prev_a + offset, prev_b + offset))

    pairs: list[dict] = []
    for index, (chapter_a_index, chapter_b_index) in enumerate(expanded_pairs, start=1):
        chapter_a = book_a.chapters[chapter_a_index - 1]
        chapter_b = book_b.chapters[chapter_b_index - 1]
        pairs.append(
            {
                "id": f"chapter-{index:02d}",
                "a_href": chapter_a.href,
                "b_href": chapter_b.href,
                "title": f"{chapter_a.title} / {chapter_b.title}",
            }
        )

    return pairs


def one_to_one_alignment(count: int) -> list[dict]:
    return [{"a": [index, index], "b": [index, index]} for index in range(1, count + 1)]


def validate_alignment_ranges(
    segments: list[dict],
    expected_a: int,
    expected_b: int,
) -> list[dict]:
    next_a = 1
    next_b = 1

    for segment in segments:
        a_start, a_end = segment["a"]
        b_start, b_end = segment["b"]
        if a_start != next_a or b_start != next_b:
            raise AlignmentError(
                "Alignment ranges must be continuous and non-overlapping."
            )
        if a_start > a_end or b_start > b_end:
            raise AlignmentError("Alignment ranges must be ascending.")
        next_a = a_end + 1
        next_b = b_end + 1

    if next_a != expected_a + 1:
        raise AlignmentError(
            f"Alignment covers source A paragraphs 1-{next_a - 1}, expected 1-{expected_a}."
        )
    if next_b != expected_b + 1:
        raise AlignmentError(
            f"Alignment covers source B paragraphs 1-{next_b - 1}, expected 1-{expected_b}."
        )
    return segments


def parse_alignment_ranges(
    raw: str,
    expected_a: int,
    expected_b: int,
) -> list[dict]:
    if not raw:
        raise AlignmentError("No alignment ranges were provided.")

    segments: list[dict] = []
    next_a = 1
    next_b = 1

    for chunk in raw.split(","):
        chunk = chunk.strip()
        match = re.fullmatch(
            r"(\d+)(?:\s*-\s*(\d+))?\s*=\s*(\d+)(?:\s*-\s*(\d+))?",
            chunk,
        )
        if match is None:
            raise AlignmentError(
                f"Invalid range '{chunk}'. Expected entries like 1=1 or 2-3=2."
            )

        a_start = int(match.group(1))
        a_end = int(match.group(2) or match.group(1))
        b_start = int(match.group(3))
        b_end = int(match.group(4) or match.group(3))
        if a_start > a_end or b_start > b_end:
            raise AlignmentError(f"Descending ranges are not allowed: {chunk}")
        if a_start != next_a or b_start != next_b:
            raise AlignmentError(
                "Ranges must be continuous and in order. "
                f"Expected A to start at {next_a} and B to start at {next_b}."
            )

        next_a = a_end + 1
        next_b = b_end + 1
        segments.append({"a": [a_start, a_end], "b": [b_start, b_end]})

    return validate_alignment_ranges(segments, expected_a, expected_b)


def review_line(paragraph: Paragraph) -> str:
    if paragraph.index == paragraph.source_index:
        prefix = str(paragraph.index)
    else:
        prefix = f"{paragraph.index} [src {paragraph.source_index}]"
    stats = paragraph_length_signature(paragraph.text)
    return f"{prefix}. [{stats}] {paragraph.text}"


def paragraph_length_signature(text: str) -> str:
    meaningful_chars = len(MEANINGFUL_CHAR_RE.findall(text))
    latin_words = len(LATIN_WORD_RE.findall(text))
    cjk_chars = len(CJK_CHAR_RE.findall(text))
    sentence_count = len(SENTENCE_END_RE.findall(text))
    return (
        f"len={meaningful_chars} w={latin_words} han={cjk_chars} s={sentence_count}"
    )


def sentence_count_for_alignment(text: str) -> int:
    if not text:
        return 0
    return max(1, len(SENTENCE_END_RE.findall(text)))


def is_speaker_label(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and len(stripped) <= 120 and stripped.endswith((':', '：'))


def is_dialogue_like(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith(("“", "\"", "'", "‘", "—", "–", "-"))


def paragraph_alignment_features(text: str) -> AlignmentFeatures:
    return AlignmentFeatures(
        meaningful_chars=len(MEANINGFUL_CHAR_RE.findall(text)),
        sentence_count=sentence_count_for_alignment(text),
        speaker_labels=1 if is_speaker_label(text) else 0,
        dialogue_paragraphs=1 if is_dialogue_like(text) else 0,
    )


def build_feature_prefix_sums(paragraphs: list[Paragraph]) -> dict[str, list[int]]:
    prefixes = {
        "meaningful_chars": [0],
        "sentence_count": [0],
        "speaker_labels": [0],
        "dialogue_paragraphs": [0],
    }
    for paragraph in paragraphs:
        features = paragraph_alignment_features(paragraph.text)
        for key in prefixes:
            prefixes[key].append(prefixes[key][-1] + getattr(features, key))
    return prefixes


def prefix_span_total(
    prefixes: dict[str, list[int]],
    key: str,
    start: int,
    end: int,
) -> int:
    return prefixes[key][end] - prefixes[key][start]


def format_alignment_segment(segment: dict) -> str:
    a_start, a_end = segment["a"]
    b_start, b_end = segment["b"]
    a_label = str(a_start) if a_start == a_end else f"{a_start}-{a_end}"
    b_label = str(b_start) if b_start == b_end else f"{b_start}-{b_end}"
    return f"{a_label}={b_label}"


def summarize_nontrivial_alignments(
    alignments: list[dict],
    limit: int = 12,
) -> list[str]:
    nontrivial = [
        format_alignment_segment(segment)
        for segment in alignments
        if segment["a"][0] != segment["a"][1] or segment["b"][0] != segment["b"][1]
    ]
    if len(nontrivial) <= limit:
        return nontrivial
    return nontrivial[:limit] + [f"... ({len(nontrivial) - limit} more)"]


def block_alignment_cost(
    prefixes_a: dict[str, list[int]],
    prefixes_b: dict[str, list[int]],
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
    expected_char_ratio: float,
) -> float:
    chars_a = prefix_span_total(prefixes_a, "meaningful_chars", start_a, end_a)
    chars_b = prefix_span_total(prefixes_b, "meaningful_chars", start_b, end_b)
    sentences_a = prefix_span_total(prefixes_a, "sentence_count", start_a, end_a)
    sentences_b = prefix_span_total(prefixes_b, "sentence_count", start_b, end_b)
    labels_a = prefix_span_total(prefixes_a, "speaker_labels", start_a, end_a)
    labels_b = prefix_span_total(prefixes_b, "speaker_labels", start_b, end_b)
    dialogue_a = prefix_span_total(prefixes_a, "dialogue_paragraphs", start_a, end_a)
    dialogue_b = prefix_span_total(prefixes_b, "dialogue_paragraphs", start_b, end_b)

    scaled_chars_b = chars_b * expected_char_ratio
    char_cost = abs(chars_a - scaled_chars_b) / max(80.0, chars_a, scaled_chars_b, 1.0)
    sentence_cost = abs(sentences_a - sentences_b) / max(
        1.0,
        float(max(sentences_a, sentences_b)),
    )
    label_cost = abs(labels_a - labels_b)
    dialogue_cost = abs(dialogue_a - dialogue_b) / max(
        1.0,
        float(max(dialogue_a, dialogue_b, 1)),
    )

    span_a = end_a - start_a
    span_b = end_b - start_b
    extra_a = span_a - 1
    extra_b = span_b - 1
    complexity_cost = (
        0.7 * (extra_a + extra_b)
        + 0.35 * min(extra_a, extra_b)
        + 0.08 * abs(span_a - span_b)
    )

    return (
        3.2 * char_cost
        + 1.6 * sentence_cost
        + 0.9 * label_cost
        + 0.35 * dialogue_cost
        + complexity_cost
    )


def build_auto_alignment_result(
    alignments: list[dict],
    costs: list[float],
) -> AutoAlignmentResult:
    total_cost = sum(costs)
    average_cost = total_cost / max(1, len(alignments))
    max_segment_cost = max(costs, default=0.0)
    return AutoAlignmentResult(
        alignments=alignments,
        total_cost=total_cost,
        average_cost=average_cost,
        max_segment_cost=max_segment_cost,
    )


def anomaly_guided_auto_align_chapter(
    chapter_a: Chapter,
    chapter_b: Chapter,
    max_span: int,
) -> AutoAlignmentResult | None:
    count_a = chapter_a.paragraph_count
    count_b = chapter_b.paragraph_count
    prefixes_a = build_feature_prefix_sums(chapter_a.paragraphs)
    prefixes_b = build_feature_prefix_sums(chapter_b.paragraphs)

    total_chars_a = prefix_span_total(prefixes_a, "meaningful_chars", 0, count_a)
    total_chars_b = prefix_span_total(prefixes_b, "meaningful_chars", 0, count_b)
    if total_chars_a == 0 or total_chars_b == 0:
        return None

    expected_char_ratio = total_chars_a / total_chars_b
    alignments: list[dict] = []
    costs: list[float] = []
    index_a = 0
    index_b = 0

    while index_a < count_a and index_b < count_b:
        remaining_a = count_a - index_a
        remaining_b = count_b - index_b
        if remaining_a == remaining_b:
            for offset in range(remaining_a):
                alignments.append(
                    {
                        "a": [index_a + offset + 1, index_a + offset + 1],
                        "b": [index_b + offset + 1, index_b + offset + 1],
                    }
                )
                costs.append(
                    block_alignment_cost(
                        prefixes_a,
                        prefixes_b,
                        index_a + offset,
                        index_a + offset + 1,
                        index_b + offset,
                        index_b + offset + 1,
                        expected_char_ratio,
                    )
                )
            return build_auto_alignment_result(alignments, costs)

        pair_scores = [
            block_alignment_cost(
                prefixes_a,
                prefixes_b,
                index_a + offset,
                index_a + offset + 1,
                index_b + offset,
                index_b + offset + 1,
                expected_char_ratio,
            )
            for offset in range(min(remaining_a, remaining_b))
        ]
        if not pair_scores:
            break

        anomaly_offset = max(range(len(pair_scores)), key=pair_scores.__getitem__)
        for offset in range(anomaly_offset):
            alignments.append(
                {
                    "a": [index_a + 1, index_a + 1],
                    "b": [index_b + 1, index_b + 1],
                }
            )
            costs.append(pair_scores[offset])
            index_a += 1
            index_b += 1

        remaining_a = count_a - index_a
        remaining_b = count_b - index_b
        current_diff = remaining_a - remaining_b
        best_candidate: tuple[float, int, int, float] | None = None
        for span_a in range(1, max_span + 1):
            next_a = index_a + span_a
            if next_a > count_a:
                break
            for span_b in range(1, max_span + 1):
                next_b = index_b + span_b
                if next_b > count_b:
                    break
                if span_a == span_b:
                    continue
                if current_diff > 0 and span_a <= span_b:
                    continue
                if current_diff < 0 and span_b <= span_a:
                    continue

                new_diff = (count_a - next_a) - (count_b - next_b)
                if abs(new_diff) >= abs(current_diff):
                    continue

                cost = block_alignment_cost(
                    prefixes_a,
                    prefixes_b,
                    index_a,
                    next_a,
                    index_b,
                    next_b,
                    expected_char_ratio,
                )
                score = cost + 0.2 * abs(new_diff)
                candidate = (score, span_a, span_b, cost)
                if best_candidate is None or candidate < best_candidate:
                    best_candidate = candidate

        if best_candidate is None:
            return None

        _, span_a, span_b, block_cost = best_candidate
        alignments.append(
            {
                "a": [index_a + 1, index_a + span_a],
                "b": [index_b + 1, index_b + span_b],
            }
        )
        costs.append(block_cost)
        index_a += span_a
        index_b += span_b

    if index_a == count_a and index_b == count_b:
        return build_auto_alignment_result(alignments, costs)
    return None


def dynamic_programming_auto_align_chapter(
    chapter_a: Chapter,
    chapter_b: Chapter,
    max_span: int,
) -> AutoAlignmentResult | None:
    count_a = chapter_a.paragraph_count
    count_b = chapter_b.paragraph_count
    prefixes_a = build_feature_prefix_sums(chapter_a.paragraphs)
    prefixes_b = build_feature_prefix_sums(chapter_b.paragraphs)

    total_chars_a = prefix_span_total(prefixes_a, "meaningful_chars", 0, count_a)
    total_chars_b = prefix_span_total(prefixes_b, "meaningful_chars", 0, count_b)
    if total_chars_a == 0 or total_chars_b == 0:
        return None

    expected_char_ratio = total_chars_a / total_chars_b
    inf = float("inf")
    dp = [[inf] * (count_b + 1) for _ in range(count_a + 1)]
    back: list[list[tuple[int, int] | None]] = [
        [None] * (count_b + 1) for _ in range(count_a + 1)
    ]
    segment_costs: list[list[float]] = [
        [inf] * (count_b + 1) for _ in range(count_a + 1)
    ]
    dp[0][0] = 0.0

    for index_a in range(count_a + 1):
        for index_b in range(count_b + 1):
            if not math.isfinite(dp[index_a][index_b]):
                continue
            for span_a in range(1, max_span + 1):
                next_a = index_a + span_a
                if next_a > count_a:
                    break
                for span_b in range(1, max_span + 1):
                    next_b = index_b + span_b
                    if next_b > count_b:
                        break
                    cost = block_alignment_cost(
                        prefixes_a,
                        prefixes_b,
                        index_a,
                        next_a,
                        index_b,
                        next_b,
                        expected_char_ratio,
                    )
                    score = dp[index_a][index_b] + cost
                    if score < dp[next_a][next_b]:
                        dp[next_a][next_b] = score
                        back[next_a][next_b] = (index_a, index_b)
                        segment_costs[next_a][next_b] = cost

    if not math.isfinite(dp[count_a][count_b]):
        return None

    alignments: list[dict] = []
    collected_costs: list[float] = []
    cursor_a = count_a
    cursor_b = count_b
    while cursor_a > 0 or cursor_b > 0:
        previous = back[cursor_a][cursor_b]
        if previous is None:
            return None
        prev_a, prev_b = previous
        alignments.append(
            {"a": [prev_a + 1, cursor_a], "b": [prev_b + 1, cursor_b]}
        )
        collected_costs.append(segment_costs[cursor_a][cursor_b])
        cursor_a = prev_a
        cursor_b = prev_b

    alignments.reverse()
    collected_costs.reverse()
    return build_auto_alignment_result(alignments, collected_costs)


def auto_alignment_is_confident(result: AutoAlignmentResult) -> bool:
    return result.average_cost <= 0.55 and result.max_segment_cost <= 4.2


def write_review_file(
    pair: dict,
    chapter_a: Chapter,
    chapter_b: Chapter,
    work_dir: Path,
    label_a: str,
    label_b: str,
    suggestion: AutoAlignmentResult | None = None,
) -> Path:
    review_dir = work_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"{pair['id']}.md"

    lines = [
        f"# {pair['title']}",
        "",
    ]
    if suggestion is not None:
        summary = summarize_nontrivial_alignments(suggestion.alignments)
        lines.extend(
            [
                "## Length-Based Suggestion",
                "",
                (
                    "Suggested automatically using local paragraph-length matching. "
                    f"Average cost: {suggestion.average_cost:.3f}; "
                    f"max segment cost: {suggestion.max_segment_cost:.3f}."
                ),
                "",
            ]
        )
        if summary:
            lines.extend(
                [
                    "Non-1:1 segments:",
                    "",
                ]
            )
            for item in summary:
                lines.append(f"- {item}")
            lines.append("")

    lines.extend(
        [
        f"## {label_a}: {chapter_a.title}",
        "",
        f"Paragraph count after preprocessing: {chapter_a.paragraph_count}",
        "",
    ]
    )
    if chapter_a.removed_paragraphs:
        lines.append("Removed during preprocessing:")
        lines.append("")
        for removed in chapter_a.removed_paragraphs:
            lines.append(
                f"- src {removed.source_index}: [{removed.reason}] {removed.text or '[EMPTY]'}"
            )
        lines.append("")
    if chapter_a.trailing_note_paragraphs:
        lines.append("Trailing notes excluded from paragraph matching but preserved in output:")
        lines.append("")
        for paragraph in chapter_a.trailing_note_paragraphs:
            lines.append(
                f"- src {paragraph.source_index}: {paragraph.text or '[EMPTY]'}"
            )
        lines.append("")

    for paragraph in chapter_a.paragraphs:
        lines.append(review_line(paragraph))
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            f"## {label_b}: {chapter_b.title}",
            "",
            f"Paragraph count after preprocessing: {chapter_b.paragraph_count}",
            "",
        ]
    )
    if chapter_b.removed_paragraphs:
        lines.append("Removed during preprocessing:")
        lines.append("")
        for removed in chapter_b.removed_paragraphs:
            lines.append(
                f"- src {removed.source_index}: [{removed.reason}] {removed.text or '[EMPTY]'}"
            )
        lines.append("")
    if chapter_b.trailing_note_paragraphs:
        lines.append("Trailing notes excluded from paragraph matching but preserved in output:")
        lines.append("")
        for paragraph in chapter_b.trailing_note_paragraphs:
            lines.append(
                f"- src {paragraph.source_index}: {paragraph.text or '[EMPTY]'}"
            )
        lines.append("")

    for paragraph in chapter_b.paragraphs:
        lines.append(review_line(paragraph))
        lines.append("")

    review_path.write_text("\n".join(lines), encoding="utf-8")
    return review_path


def resolve_alignments(
    pair: dict,
    chapter_a: Chapter,
    chapter_b: Chapter,
    config: dict,
    config_path: Path,
    work_dir: Path,
    interactive: bool,
    label_a: str,
    label_b: str,
    max_auto_span: int,
) -> list[dict] | None:
    if chapter_a.paragraph_count == chapter_b.paragraph_count and not pair.get("alignments"):
        return one_to_one_alignment(chapter_a.paragraph_count)
    if pair.get("alignments"):
        return validate_alignment_ranges(
            pair["alignments"],
            chapter_a.paragraph_count,
            chapter_b.paragraph_count,
        )

    suggestion = anomaly_guided_auto_align_chapter(
        chapter_a,
        chapter_b,
        max_span=max_auto_span,
    )
    if suggestion is None or not auto_alignment_is_confident(suggestion):
        fallback = dynamic_programming_auto_align_chapter(
            chapter_a,
            chapter_b,
            max_span=max_auto_span,
        )
        if fallback is not None and (
            suggestion is None or fallback.average_cost < suggestion.average_cost
        ):
            suggestion = fallback
    if suggestion is not None:
        pair["alignments"] = suggestion.alignments
        save_config(config_path, config)
        summary = summarize_nontrivial_alignments(suggestion.alignments)
        summary_text = ", ".join(summary) if summary else "all segments 1:1"
        print(
            f"Auto-aligned {pair['title']} using length-based matching "
            f"(avg cost {suggestion.average_cost:.3f}; {summary_text})."
        )
        return suggestion.alignments

    review_path = write_review_file(
        pair,
        chapter_a,
        chapter_b,
        work_dir,
        label_a,
        label_b,
        suggestion=suggestion,
    )

    if not interactive:
        suggestion_note = ""
        if suggestion is not None:
            summary = summarize_nontrivial_alignments(suggestion.alignments)
            if summary:
                suggestion_note = (
                    "\n  Suggested non-1:1 ranges: " + ", ".join(summary)
                )
        print(
            textwrap.dedent(
                f"""\
                Missing paragraph alignment for {pair['title']}.
                  Source A count: {chapter_a.paragraph_count}
                  Source B count: {chapter_b.paragraph_count}
                  Review file: {review_path}
                {suggestion_note}
                """
            ),
            file=sys.stderr,
        )
        return None

    print()
    print(f"Missing paragraph alignment for {pair['title']}.")
    print(f"  {label_a}: {chapter_a.paragraph_count}")
    print(f"  {label_b}: {chapter_b.paragraph_count}")
    print(f"  Review file: {review_path}")
    return None


def build_merged_chapter(
    index: int,
    pair: dict,
    chapter_a: Chapter,
    chapter_b: Chapter,
    alignments: list[dict],
) -> MergedChapter:
    segments: list[MergedSegment] = []
    for segment_index, segment in enumerate(alignments, start=1):
        a_start, a_end = segment["a"]
        b_start, b_end = segment["b"]
        segments.append(
            MergedSegment(
                index=segment_index,
                paragraphs_a=chapter_a.paragraphs[a_start - 1 : a_end],
                paragraphs_b=chapter_b.paragraphs[b_start - 1 : b_end],
            )
        )
    return MergedChapter(
        index=index,
        title=pair["title"],
        segments=segments,
        trailing_note_paragraphs_a=chapter_a.trailing_note_paragraphs,
        trailing_note_paragraphs_b=chapter_b.trailing_note_paragraphs,
    )


def build_merged_chapter_xhtml(
    chapter: MergedChapter,
    label_a: str,
    label_b: str,
    language_a: str,
    language_b: str,
    primary_language: str,
) -> str:
    blocks: list[str] = []
    for segment in chapter.segments:
        blocks.append(
            textwrap.dedent(
                f"""\
                <section class="pair" id="chapter-{chapter.index:02d}-segment-{segment.index:04d}">
                  <div class="lang-block lang-a" lang="{xml_escape(language_a)}" xml:lang="{xml_escape(language_a)}">
                    {''.join(paragraph.html for paragraph in segment.paragraphs_a)}
                  </div>
                  <div class="lang-block lang-b" lang="{xml_escape(language_b)}" xml:lang="{xml_escape(language_b)}">
                    {''.join(paragraph.html for paragraph in segment.paragraphs_b)}
                  </div>
                </section>
                """
            ).strip()
        )

    if chapter.trailing_note_paragraphs_a or chapter.trailing_note_paragraphs_b:
        blocks.append(
            textwrap.dedent(
                f"""\
                <section class="pair pair-notes" id="chapter-{chapter.index:02d}-notes">
                  <div class="lang-block lang-a" lang="{xml_escape(language_a)}" xml:lang="{xml_escape(language_a)}">
                    {''.join(paragraph.html for paragraph in chapter.trailing_note_paragraphs_a)}
                  </div>
                  <div class="lang-block lang-b" lang="{xml_escape(language_b)}" xml:lang="{xml_escape(language_b)}">
                    {''.join(paragraph.html for paragraph in chapter.trailing_note_paragraphs_b)}
                  </div>
                </section>
                """
            ).strip()
        )

    return textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="utf-8"?>
        <html xmlns="{XHTML_NS}" xmlns:epub="{EPUB_NS}" lang="{xml_escape(primary_language)}" xml:lang="{xml_escape(primary_language)}">
          <head>
            <title>{xml_escape(chapter.title)}</title>
            <link rel="stylesheet" type="text/css" href="styles/main.css" />
          </head>
          <body>
            <section class="chapter">
              <h1>{xml_escape(chapter.title)}</h1>
              {' '.join(blocks)}
            </section>
          </body>
        </html>
        """
    ).lstrip()


def xml_escape(text: str) -> str:
    return html_escape(text, quote=True).replace("'", "&apos;")


def build_nav_xhtml(chapters: list[dict]) -> str:
    items = "\n".join(
        f'          <li><a href="{chapter["file_name"]}">{xml_escape(chapter["title"])}</a></li>'
        for chapter in chapters
    )
    return textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="utf-8"?>
        <html xmlns="{XHTML_NS}" xmlns:epub="{EPUB_NS}" xml:lang="en">
          <head>
            <title>Table of Contents</title>
          </head>
          <body>
            <nav epub:type="toc" id="toc">
              <h1>Table of Contents</h1>
              <ol>
        {items}
              </ol>
            </nav>
          </body>
        </html>
        """
    ).lstrip()


def build_ncx(identifier: str, title: str, chapters: list[dict]) -> str:
    nav_points = []
    for index, chapter in enumerate(chapters, start=1):
        nav_points.append(
            textwrap.dedent(
                f"""\
                <navPoint id="navPoint-{index}" playOrder="{index}">
                  <navLabel><text>{xml_escape(chapter["title"])}</text></navLabel>
                  <content src="{chapter["file_name"]}"/>
                </navPoint>
                """
            ).strip()
        )
    joined = "\n    ".join(nav_points)
    return textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <ncx xmlns="{NCX_NS}" version="2005-1">
          <head>
            <meta name="dtb:uid" content="{identifier}"/>
            <meta name="dtb:depth" content="1"/>
            <meta name="dtb:totalPageCount" content="0"/>
            <meta name="dtb:maxPageNumber" content="0"/>
          </head>
          <docTitle><text>{xml_escape(title)}</text></docTitle>
          <navMap>
            {joined}
          </navMap>
        </ncx>
        """
    ).lstrip()


def normalize_language_code(language: str | None, fallback: str) -> str:
    value = (language or "").strip().replace("_", "-")
    if not value:
        return fallback
    folded = value.casefold()
    if folded in {"und", "mul", "zxx"}:
        return fallback
    return value


def build_opf(
    identifier: str,
    title: str,
    creator: str,
    chapters: list[dict],
    primary_language: str,
) -> str:
    manifest_items = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="styles/main.css" media-type="text/css"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
    ]
    spine_items = []

    for index, chapter in enumerate(chapters, start=1):
        manifest_items.append(
            f'<item id="chapter-{index:02d}" href="{chapter["file_name"]}" '
            'media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="chapter-{index:02d}"/>')

    manifest = "\n    ".join(manifest_items)
    spine = "\n    ".join(spine_items)
    modified = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )

    return textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="utf-8"?>
        <package xmlns="{OPF_NS}" version="3.0" unique-identifier="bookid">
          <metadata xmlns:dc="{DC_NS}">
            <dc:identifier id="bookid">{identifier}</dc:identifier>
            <dc:title>{xml_escape(title)}</dc:title>
            <dc:creator>{xml_escape(creator)}</dc:creator>
            <dc:language>{xml_escape(primary_language)}</dc:language>
            <meta property="dcterms:modified">{modified}</meta>
          </metadata>
          <manifest>
            {manifest}
          </manifest>
          <spine toc="ncx">
            {spine}
          </spine>
        </package>
        """
    ).lstrip()


def epub_stylesheet() -> str:
    return textwrap.dedent(
        """\
        body {
          font-family: serif;
          line-height: 1.55;
          margin: 5%;
        }

        .chapter > h1 {
          margin-bottom: 1.5rem;
        }

        .pair {
          border-bottom: 1px solid #d0d0d0;
          margin: 0 0 1.25rem;
          padding-bottom: 1rem;
        }

        .lang-block {
          margin: 0 0 0.85rem;
        }

        .lang-label {
          color: #666;
          font-size: 0.75rem;
          font-weight: bold;
          letter-spacing: 0.08em;
          margin-bottom: 0.4rem;
          text-transform: uppercase;
        }

        p {
          margin: 0 0 0.85rem;
        }
        """
    )


def write_epub_output(
    output_path: Path,
    title: str,
    creator: str,
    merged_chapters: list[MergedChapter],
    label_a: str,
    label_b: str,
    language_a: str,
    language_b: str,
) -> None:
    identifier = f"urn:uuid:{uuid.uuid4()}"
    normalized_language_a = normalize_language_code(language_a, "en")
    normalized_language_b = normalize_language_code(language_b, normalized_language_a)
    primary_language = normalized_language_a
    container_xml = textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="utf-8"?>
        <container xmlns="{CONTAINER_NS}" version="1.0">
          <rootfiles>
            <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
          </rootfiles>
        </container>
        """
    ).lstrip()
    chapter_documents = [
        {
            "title": chapter.title,
            "file_name": f"chapter-{chapter.index:02d}.xhtml",
            "content": build_merged_chapter_xhtml(
                chapter,
                label_a,
                label_b,
                normalized_language_a,
                normalized_language_b,
                primary_language,
            ),
        }
        for chapter in merged_chapters
    ]
    nav_xhtml = build_nav_xhtml(chapter_documents)
    ncx = build_ncx(identifier, title, chapter_documents)
    opf = build_opf(identifier, title, creator, chapter_documents, primary_language)
    stylesheet = epub_stylesheet()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr("META-INF/container.xml", container_xml)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/nav.xhtml", nav_xhtml)
        archive.writestr("OEBPS/toc.ncx", ncx)
        archive.writestr("OEBPS/styles/main.css", stylesheet)
        for chapter in chapter_documents:
            archive.writestr(f'OEBPS/{chapter["file_name"]}', chapter["content"])


def write_markdown_output(
    output_path: Path,
    title: str,
    merged_chapters: list[MergedChapter],
    label_a: str,
    label_b: str,
) -> None:
    lines = [f"# {title}", ""]
    for chapter in merged_chapters:
        lines.extend([f"## {chapter.title}", ""])
        for segment in chapter.segments:
            lines.extend([f"### Segment {segment.index}", ""])
            for paragraph in segment.paragraphs_a:
                lines.extend([paragraph.text, ""])
            for paragraph in segment.paragraphs_b:
                lines.extend([paragraph.text, ""])
        if chapter.trailing_note_paragraphs_a or chapter.trailing_note_paragraphs_b:
            lines.extend(["### Trailing Notes", ""])
            for paragraph in chapter.trailing_note_paragraphs_a:
                lines.extend([paragraph.text, ""])
            for paragraph in chapter.trailing_note_paragraphs_b:
                lines.extend([paragraph.text, ""])
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_text_output(
    output_path: Path,
    title: str,
    merged_chapters: list[MergedChapter],
    label_a: str,
    label_b: str,
) -> None:
    lines = [title, "=" * len(title), ""]
    for chapter in merged_chapters:
        lines.extend([chapter.title, "-" * len(chapter.title), ""])
        for segment in chapter.segments:
            for paragraph in segment.paragraphs_a:
                lines.extend([paragraph.text, ""])
            for paragraph in segment.paragraphs_b:
                lines.extend([paragraph.text, ""])
        if chapter.trailing_note_paragraphs_a or chapter.trailing_note_paragraphs_b:
            lines.extend(["[Trailing Notes]", ""])
            for paragraph in chapter.trailing_note_paragraphs_a:
                lines.extend([paragraph.text, ""])
            for paragraph in chapter.trailing_note_paragraphs_b:
                lines.extend([paragraph.text, ""])
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_output(
    output_path: Path,
    title: str,
    creator: str,
    merged_chapters: list[MergedChapter],
    label_a: str,
    label_b: str,
    language_a: str,
    language_b: str,
) -> None:
    suffix = output_path.suffix.lower()
    if suffix in EPUB_OUTPUT_SUFFIXES:
        write_epub_output(
            output_path,
            title,
            creator,
            merged_chapters,
            label_a,
            label_b,
            language_a,
            language_b,
        )
        return
    if suffix in MARKDOWN_OUTPUT_SUFFIXES:
        write_markdown_output(output_path, title, merged_chapters, label_a, label_b)
        return
    if suffix in TEXT_OUTPUT_SUFFIXES:
        write_text_output(output_path, title, merged_chapters, label_a, label_b)
        return
    raise AlignmentError(
        f"Unsupported output format '{suffix}'. Supported outputs: .epub, .md, .txt"
    )


def merge_epubs(args: argparse.Namespace) -> int:
    config = load_config(args.config, args.label_a, args.label_b)
    cleanup_rules = build_cleanup_rules(config)
    source_a_path = resolve_source_path(args.source_a, "Path to source A: ")
    source_b_path = resolve_source_path(args.source_b, "Path to source B: ")
    book_a = load_book(source_a_path, cleanup_rules)
    book_b = load_book(source_b_path, cleanup_rules)

    chapter_pairs = resolve_chapter_pairs(
        book_a,
        book_b,
        config,
        interactive=not args.non_interactive,
    )
    save_config(args.config, config)

    label_a, label_b = get_config_language_names(config)
    work_dir = args.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    merged_chapters: list[MergedChapter] = []
    missing_alignments = False
    chapters_a = book_a.chapters_by_href
    chapters_b = book_b.chapters_by_href

    for position, pair in enumerate(chapter_pairs, start=1):
        chapter_a = chapters_a[pair["a_href"]]
        chapter_b = chapters_b[pair["b_href"]]
        alignments = resolve_alignments(
            pair,
            chapter_a,
            chapter_b,
            config,
            args.config,
            work_dir,
            interactive=not args.non_interactive,
            label_a=label_a,
            label_b=label_b,
            max_auto_span=args.max_auto_span,
        )
        if alignments is None:
            missing_alignments = True
            continue
        merged_chapters.append(
            build_merged_chapter(position, pair, chapter_a, chapter_b, alignments)
        )

    if missing_alignments:
        raise AlignmentError(
            "Some chapter alignments are still missing. Review the generated files "
            f"under {work_dir / 'review'} and add alignments to {args.config} or run "
            "the command interactively."
        )

    merged_title = args.title or f"{book_a.title} / {book_b.title}"
    merged_creator = book_a.creator or book_b.creator or "Unknown"
    write_output(
        args.output,
        merged_title,
        merged_creator,
        merged_chapters,
        label_a,
        label_b,
        book_a.language,
        book_b.language,
    )
    save_config(args.config, config)
    print(f"Merged output written to {args.output}")
    return 0


def inspect_command(args: argparse.Namespace) -> int:
    config = load_config(args.config, "Language A", "Language B")
    cleanup_rules = build_cleanup_rules(config)
    source_a_path = resolve_source_path(args.source_a, "Path to source A: ")
    source_b_path = resolve_source_path(args.source_b, "Path to source B: ")
    inspect_books(
        load_book(source_a_path, cleanup_rules),
        load_book(source_b_path, cleanup_rules),
    )
    return 0


def init_config_command(args: argparse.Namespace) -> int:
    config_path = args.config
    if config_path.exists() and not args.force:
        raise AlignmentError(
            f"Config already exists: {config_path}. Use --force to overwrite it."
        )
    config = default_config(args.label_a, args.label_b)
    save_config(config_path, config)
    print(f"Config template written to {config_path}")
    return 0


def interactive_wizard() -> int:
    print("Interactive mode")
    print("The tool will ask for the two source files.")
    print()

    label_a = "Language A"
    label_b = "Language B"
    source_a = resolve_source_path(None, "Path to the Language A eBook file: ")
    source_b = resolve_source_path(None, "Path to the Language B eBook file: ")

    output_stem = f"{sanitize_output_stem(source_a.stem)}-bilingual"
    output_path = Path.cwd() / f"{output_stem}.epub"
    config_path = Path.cwd() / f"{output_stem}.alignment.json"
    work_dir = Path.cwd() / f"{output_stem}-work"

    print()
    print(f"Output file will be written to: {output_path}")
    print(f"Alignment config will be stored in: {config_path}")
    print(f"Working files will be stored in: {work_dir}")
    print()

    args = argparse.Namespace(
        source_a=source_a,
        source_b=source_b,
        output=output_path,
        config=config_path,
        work_dir=work_dir,
        label_a=label_a,
        label_b=label_b,
        title="",
        max_auto_span=5,
        non_interactive=False,
    )
    return merge_epubs(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combine two book files into a bilingual output.",
        epilog="Run without a subcommand to start interactive mode.",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="List normalized chapters in both sources.",
    )
    inspect_parser.add_argument("source_a", nargs="?", type=Path)
    inspect_parser.add_argument("source_b", nargs="?", type=Path)
    inspect_parser.add_argument(
        "--config",
        type=Path,
        default=Path("alignment-config.json"),
        help=(
            "Optional config file that can customize cleanup keywords used during "
            "inspection."
        ),
    )
    inspect_parser.set_defaults(func=inspect_command)

    init_config_parser = subparsers.add_parser(
        "init-config",
        help="Write a starter config file with customizable cleanup keyword lists.",
    )
    init_config_parser.add_argument(
        "--config",
        type=Path,
        default=Path("alignment-config.json"),
        help="Path to the config file to create.",
    )
    init_config_parser.add_argument(
        "--language-a",
        "--label-a",
        dest="label_a",
        default="Language A",
        help="Display name for source A.",
    )
    init_config_parser.add_argument(
        "--language-b",
        "--label-b",
        dest="label_b",
        default="Language B",
        help="Display name for source B.",
    )
    init_config_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target file if it already exists.",
    )
    init_config_parser.set_defaults(func=init_config_command)

    merge_parser = subparsers.add_parser(
        "merge",
        help="Interactively align and merge two sources.",
    )
    merge_parser.add_argument("source_a", nargs="?", type=Path)
    merge_parser.add_argument("source_b", nargs="?", type=Path)
    merge_parser.add_argument(
        "--output",
        type=Path,
        default=Path("merged-bilingual.epub"),
        help="Generated output path. Supported outputs: .epub, .md, .txt",
    )
    merge_parser.add_argument(
        "--config",
        type=Path,
        default=Path("alignment-config.json"),
        help="JSON file used to persist chapter pairs and paragraph alignments.",
    )
    merge_parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("merge-work"),
        help="Directory for generated review files.",
    )
    merge_parser.add_argument(
        "--language-a",
        "--label-a",
        dest="label_a",
        default="Language A",
        help="Display name for source A in the merged output.",
    )
    merge_parser.add_argument(
        "--language-b",
        "--label-b",
        dest="label_b",
        default="Language B",
        help="Display name for source B in the merged output.",
    )
    merge_parser.add_argument(
        "--title",
        default="",
        help="Override the merged output title.",
    )
    merge_parser.add_argument(
        "--max-auto-span",
        type=int,
        default=5,
        help=(
            "Maximum paragraph block size considered by the automatic local aligner. "
            "Increase this if one paragraph sometimes maps to 5+ consecutive paragraphs."
        ),
    )
    merge_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt. Missing chapter pairs or alignments will raise an error.",
    )
    merge_parser.set_defaults(func=merge_epubs)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            return interactive_wizard()
        return args.func(args)
    except AlignmentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
