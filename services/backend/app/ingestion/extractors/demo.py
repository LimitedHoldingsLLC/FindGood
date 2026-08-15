from app.ingestion.protocols import ExtractedCandidate, ParsedDocument


class DemoExtractor:
    """Deterministic extractor. An LLMExtractor can implement the same interface later."""

    version = "demo-extractor-1"

    def extract(self, document: ParsedDocument) -> list[ExtractedCandidate]:
        data = document.data
        deals = data.get("deals") or []
        venue = data.get("venue") or {}
        results: list[ExtractedCandidate] = []
        for deal in deals:
            payload = {
                "venue": venue,
                "title": deal.get("title"),
                "description": deal.get("description"),
                "deal_type": deal.get("deal_type"),
                "offering_kind": deal.get("offering_kind"),
                "schedules": deal.get("schedules") or [],
                "items": deal.get("items") or [],
                "venue_location_hint": deal.get("venue_location_hint"),
            }
            results.append(
                ExtractedCandidate(
                    candidate_type="deal",
                    payload=payload,
                    confidence=float(deal.get("confidence", 0.9)),
                    diagnostic_notes=f"extractor={self.version}",
                )
            )
        return results
