"""HTML parser. Turns fetched bytes into a structured page document."""

from app.ingestion.crawler.html import parse_html
from app.ingestion.protocols import FetchResult, ParsedDocument


class HtmlParser:
    version = "html-1"

    def parse(self, fetched: FetchResult) -> ParsedDocument:
        page = parse_html(
            fetched.content.decode("utf-8", errors="replace"),
            url=fetched.final_url or fetched.url,
            headers=fetched.headers,
        )
        return ParsedDocument(kind="html", data=page, parser_version=self.version)
