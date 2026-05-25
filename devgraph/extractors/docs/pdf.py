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
            temp = path.with_suffix(path.suffix + ".txt")
            temp.write_text(text, encoding="utf-8")
            try:
                result = super().extract(root, temp)
                result.file.path = path.relative_to(root).as_posix()
                result.file.absolute_path = str(path.resolve())
                result.warnings.append("PDF text extracted via optional pypdf dependency.")
                return result
            finally:
                temp.unlink(missing_ok=True)
        except Exception:
            result = ExtractionResult(
                file=self._stub_file(root, path),
                warnings=["PDF extraction requires optional dependency: pip install devgraph-os[docs]"],
            )
            return result

    def _stub_file(self, root: Path, path: Path):
        from devgraph.extractors.base import make_file_record

        return make_file_record(root, path, "document", "pdf", "")
