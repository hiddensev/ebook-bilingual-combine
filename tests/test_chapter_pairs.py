import unittest
from pathlib import Path

import combine_books


def make_paragraph(index: int, text: str) -> combine_books.Paragraph:
    return combine_books.Paragraph(
        index=index,
        source_index=index,
        html=f"<p>{text}</p>",
        text=text,
    )


def make_chapter(order: int, href: str, title: str, texts: list[str]) -> combine_books.Chapter:
    return combine_books.Chapter(
        order=order,
        spine_order=order,
        href=href,
        title=title,
        paragraphs=[make_paragraph(index, text) for index, text in enumerate(texts, start=1)],
        trailing_note_paragraphs=[],
        removed_paragraphs=[],
    )


def make_book(title: str, href_prefix: str, chapter_texts: list[list[str]]) -> combine_books.Book:
    chapters = [
        make_chapter(index, f"{href_prefix}{index}.xhtml", f"{title} {index}", texts)
        for index, texts in enumerate(chapter_texts, start=1)
    ]
    return combine_books.Book(
        path=Path(f"{title}.epub"),
        title=title,
        creator="",
        language="und",
        source_format="epub",
        chapters=chapters,
        skipped_chapters=[],
    )


class ChapterPairTests(unittest.TestCase):
    def test_validate_chapter_pairs_normalizes_legacy_and_grouped_entries(self) -> None:
        book_a = make_book("Book A", "a-", [["a1"], ["a2"], ["a3"]])
        book_b = make_book("Book B", "b-", [["b1"], ["b2"], ["b3"]])

        validated = combine_books.validate_chapter_pairs(
            book_a,
            book_b,
            [
                {"a_href": "a-1.xhtml", "b_href": "b-1.xhtml"},
                {
                    "id": "chapter-02",
                    "a_hrefs": ["a-2.xhtml", "a-3.xhtml"],
                    "b_hrefs": ["b-2.xhtml"],
                    "title": "Grouped pair",
                    "alignments": [{"a": [1, 2], "b": [1, 1]}],
                },
            ],
        )

        self.assertEqual(validated[0]["a_hrefs"], ["a-1.xhtml"])
        self.assertEqual(validated[0]["b_hrefs"], ["b-1.xhtml"])
        self.assertEqual(validated[1]["a_hrefs"], ["a-2.xhtml", "a-3.xhtml"])
        self.assertEqual(validated[1]["b_hrefs"], ["b-2.xhtml"])
        self.assertEqual(validated[1]["title"], "Grouped pair")
        self.assertEqual(validated[1]["alignments"], [{"a": [1, 2], "b": [1, 1]}])

    def test_parse_chapter_pairs_emits_grouped_href_lists(self) -> None:
        book_a = make_book("Book A", "a-", [["a1"], ["a2"], ["a3"]])
        book_b = make_book("Book B", "b-", [["b1"], ["b2"], ["b3"]])

        pairs = combine_books.parse_chapter_pairs("1=1,3=3", book_a, book_b)

        self.assertEqual(len(pairs), 3)
        self.assertEqual(pairs[1]["a_hrefs"], ["a-2.xhtml"])
        self.assertEqual(pairs[1]["b_hrefs"], ["b-2.xhtml"])

    def test_build_chapter_group_flattens_multiple_chapters(self) -> None:
        book_a = make_book("Book A", "a-", [["a1 first", "a1 second"], ["a2 only"]])

        group = combine_books.build_chapter_group(
            {
                "a_hrefs": ["a-1.xhtml", "a-2.xhtml"],
                "title": "Combined",
            },
            "a",
            book_a.chapters_by_href,
        )

        self.assertEqual(group.title, "Combined")
        self.assertEqual(group.paragraph_count, 3)
        self.assertEqual(
            [paragraph.text for paragraph in group.paragraphs],
            ["a1 first", "a1 second", "a2 only"],
        )
        self.assertEqual([paragraph.index for paragraph in group.paragraphs], [1, 2, 3])

    def test_validate_semantic_resolution_uses_hrefs(self) -> None:
        book_a = make_book(
            "Book A",
            "a-",
            [[f"a1-{index}" for index in range(1, 10)], [f"a2-{index}" for index in range(1, 10)]],
        )
        book_b = make_book(
            "Book B",
            "b-",
            [[f"b1-{index}" for index in range(1, 10)], [f"b2-{index}" for index in range(1, 10)]],
        )
        cleanup_rules = combine_books.build_cleanup_rules({})

        result = combine_books.validate_semantic_resolution(
            {
                "status": "resolved",
                "continuous_main_text": True,
                "main_text_range": {
                    "a": ["a-1.xhtml", "a-2.xhtml"],
                    "b": ["b-1.xhtml", "b-2.xhtml"],
                },
                "mapping_units": [
                    {
                        "id": "m1",
                        "a_hrefs": ["a-1.xhtml"],
                        "b_hrefs": ["b-1.xhtml"],
                        "relation": "1:1",
                        "confidence": 0.9,
                        "evidence": ["match"],
                    },
                    {
                        "id": "m2",
                        "a_hrefs": ["a-2.xhtml"],
                        "b_hrefs": ["b-2.xhtml"],
                        "relation": "1:1",
                        "confidence": 0.9,
                        "evidence": ["match"],
                    },
                ],
                "info_request": None,
            },
            book_a,
            book_b,
            cleanup_rules,
        )

        self.assertEqual(result["normalized_pairs"][0]["a_hrefs"], ["a-1.xhtml"])
        self.assertEqual(result["labels_by_side"]["a"]["a-1.xhtml"], "main")

    def test_validate_semantic_info_request_accepts_local_window(self) -> None:
        book_a = make_book(
            "Book A",
            "a-",
            [[f"a1-{index}" for index in range(1, 8)], [f"a2-{index}" for index in range(1, 8)]],
        )
        book_b = make_book(
            "Book B",
            "b-",
            [
                [f"b1-{index}" for index in range(1, 8)],
                [f"b2-{index}" for index in range(1, 8)],
                [f"b3-{index}" for index in range(1, 8)],
            ],
        )
        cleanup_rules = combine_books.build_cleanup_rules({})

        combine_books.validate_semantic_info_request(
            {
                "status": "request_more_info",
                "continuous_main_text": True,
                "main_text_range": {
                    "a": ["a-1.xhtml", "a-2.xhtml"],
                    "b": ["b-1.xhtml", "b-3.xhtml"],
                },
                "mapping_units": [],
                "info_request": {
                    "request_id": "req-1",
                    "a_hrefs": ["a-1.xhtml"],
                    "b_hrefs": ["b-1.xhtml", "b-2.xhtml"],
                    "reason": "Need openings to confirm the earliest local split.",
                },
            },
            book_a,
            book_b,
            cleanup_rules,
            {"a": set(), "b": set()},
        )


if __name__ == "__main__":
    unittest.main()
