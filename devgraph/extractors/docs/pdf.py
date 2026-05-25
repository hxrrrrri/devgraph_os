"""Optional PDF extraction."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.schema import ExtractionResult
from devgraph.extractors.docs.text import TextExtractor


class PdfExtractor(TextExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return self.extract_text(
                root,
                path,
                text,
                language="pdf",
                warnings=["PDF text extracted via optional pypdf dependency."],
            )
        except Exception:
            result = ExtractionResult(
                file=self._stub_file(root, path),
                warnings=["PDF extraction requires optional dependency: pip install devgraph-os[docs]"],
            )
            return result

    def _stub_file(self, root: Path, path: Path):
        from devgraph.extractors.base import make_file_record

        return make_file_record(root, path, "document", "pdf", "")
