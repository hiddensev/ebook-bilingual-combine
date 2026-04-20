import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

import combine_books


class EpubPathNormalizationTests(unittest.TestCase):
    def test_load_epub_book_normalizes_backslash_archive_paths(self) -> None:
        cleanup_rules = combine_books.build_cleanup_rules({})

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = Path(tmpdir) / "backslash-paths.epub"
            container_xml = textwrap.dedent(
                """\
                <?xml version="1.0"?>
                <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
                  <rootfiles>
                    <rootfile
                      full-path="OEBPS\\content.opf"
                      media-type="application/oebps-package+xml"
                    />
                  </rootfiles>
                </container>
                """
            )
            content_opf = textwrap.dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>
                <package xmlns="http://www.idpf.org/2007/opf" version="3.0">
                  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                    <dc:title>Path Test</dc:title>
                  </metadata>
                  <manifest>
                    <item
                      id="nav"
                      href="nav\\toc.xhtml"
                      media-type="application/xhtml+xml"
                      properties="nav"
                    />
                    <item
                      id="chapter-1"
                      href="text\\chapter1.xhtml"
                      media-type="application/xhtml+xml"
                    />
                  </manifest>
                  <spine>
                    <itemref idref="chapter-1" />
                  </spine>
                </package>
                """
            )
            nav_xhtml = textwrap.dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>
                <html xmlns="http://www.w3.org/1999/xhtml"
                      xmlns:epub="http://www.idpf.org/2007/ops">
                  <body>
                    <nav epub:type="toc">
                      <ol>
                        <li><a href="..\\text\\chapter1.xhtml">Chapter One</a></li>
                      </ol>
                    </nav>
                  </body>
                </html>
                """
            )
            chapter_xhtml = textwrap.dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>
                <html xmlns="http://www.w3.org/1999/xhtml">
                  <body>
                    <h1>Fallback Heading</h1>
                    <p>Hello world.</p>
                  </body>
                </html>
                """
            )

            with zipfile.ZipFile(epub_path, "w") as archive:
                archive.writestr("mimetype", "application/epub+zip")
                archive.writestr("META-INF/container.xml", container_xml)
                archive.writestr("OEBPS/content.opf", content_opf)
                archive.writestr("OEBPS/nav/toc.xhtml", nav_xhtml)
                archive.writestr("OEBPS/text/chapter1.xhtml", chapter_xhtml)

            book = combine_books.load_epub_book(epub_path, cleanup_rules)

        self.assertEqual(book.title, "Path Test")
        self.assertEqual(len(book.chapters), 1)
        self.assertEqual(book.chapters[0].href, "OEBPS/text/chapter1.xhtml")
        self.assertEqual(book.chapters[0].title, "Chapter One")
        self.assertEqual(book.chapters[0].paragraphs[0].text, "Hello world.")

    def test_load_epub_book_falls_back_for_malformed_xhtml(self) -> None:
        cleanup_rules = combine_books.build_cleanup_rules({})

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = Path(tmpdir) / "malformed.epub"
            container_xml = textwrap.dedent(
                """\
                <?xml version="1.0"?>
                <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
                  <rootfiles>
                    <rootfile
                      full-path="OEBPS/content.opf"
                      media-type="application/oebps-package+xml"
                    />
                  </rootfiles>
                </container>
                """
            )
            content_opf = textwrap.dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>
                <package xmlns="http://www.idpf.org/2007/opf" version="3.0">
                  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                    <dc:title>Malformed Test</dc:title>
                  </metadata>
                  <manifest>
                    <item id="chapter-1" href="chapter1.xhtml" media-type="application/xhtml+xml" />
                  </manifest>
                  <spine>
                    <itemref idref="chapter-1" />
                  </spine>
                </package>
                """
            )
            malformed_xhtml = textwrap.dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>
                <!DOCTYPE html>
                <html xmlns="http://www.w3.org/1999/xhtml">
                  <head><title>Broken</title></head>
                  <body>
                    <section><div>
                      <h1>Broken Chapter</h1>
                      <p>First paragraph.</p>
                    </body>
                </html>
                """
            )

            with zipfile.ZipFile(epub_path, "w") as archive:
                archive.writestr("mimetype", "application/epub+zip")
                archive.writestr("META-INF/container.xml", container_xml)
                archive.writestr("OEBPS/content.opf", content_opf)
                archive.writestr("OEBPS/chapter1.xhtml", malformed_xhtml)

            book = combine_books.load_epub_book(epub_path, cleanup_rules)

        self.assertEqual(book.title, "Malformed Test")
        self.assertEqual(len(book.chapters), 1)
        self.assertEqual(book.chapters[0].title, "Broken Chapter")
        self.assertEqual(book.chapters[0].paragraphs[0].text, "First paragraph.")


if __name__ == "__main__":
    unittest.main()
