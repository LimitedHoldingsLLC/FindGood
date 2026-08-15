from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class FetchResult:
    url: str
    http_status: int
    content_type: str
    content: bytes
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    kind: str
    data: Any
    parser_version: str


@dataclass
class ExtractedCandidate:
    candidate_type: str
    payload: dict[str, Any]
    confidence: float
    diagnostic_notes: str | None = None


class Fetcher(Protocol):
    def fetch(self, url: str, *, user_agent: str, timeout_seconds: int) -> FetchResult: ...


class Parser(Protocol):
    def parse(self, fetched: FetchResult) -> ParsedDocument: ...


class Extractor(Protocol):
    def extract(self, document: ParsedDocument) -> list[ExtractedCandidate]: ...


class Normalizer(Protocol):
    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class Validator(Protocol):
    def validate(self, payload: dict[str, Any]) -> list[str]: ...


class Publisher(Protocol):
    def publish(self, candidate_id: str, *, actor: str) -> str: ...
