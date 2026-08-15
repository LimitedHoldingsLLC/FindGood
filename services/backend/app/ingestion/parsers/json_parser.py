import json

from app.ingestion.protocols import FetchResult, ParsedDocument


class JsonParser:
    version = "json-1"

    def parse(self, fetched: FetchResult) -> ParsedDocument:
        data = json.loads(fetched.content.decode("utf-8"))
        return ParsedDocument(kind="json", data=data, parser_version=self.version)
