"""Optional Office document extraction."""

from __future__ import annotations

from pathlib import Path

from devgraph.core.schema import ExtractionResult
from devgraph.extractors.docs.text import TextExtractor


class OfficeExtractor(TextExtractor):
    def extract(self, root: Path, path: Path) -> ExtractionResult:
        try:
            import docx

            document = docx.Document(str(path))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            return self.extract_text(
                root,
                path,
                text,
                language="office",
                warnings=["Office text extracted via optional python-docx dependency."],
            )
        except Exception:
            from devgraph.extractors.base import make_file_record

            return ExtractionResult(
                file=make_file_record(root, path, "document", "office", ""),
                warnings=["Office extraction requires optional dependency: pip install devgraph-os[docs]"],
            )
