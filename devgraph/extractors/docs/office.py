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
            temp = path.with_suffix(path.suffix + ".txt")
            temp.write_text(text, encoding="utf-8")
            try:
                result = super().extract(root, temp)
                result.file.path = path.relative_to(root).as_posix()
                result.file.absolute_path = str(path.resolve())
                result.warnings.append("Office text extracted via optional python-docx dependency.")
                return result
            finally:
                temp.unlink(missing_ok=True)
        except Exception:
            from devgraph.extractors.base import make_file_record

            return ExtractionResult(
                file=make_file_record(root, path, "document", "office", ""),
                warnings=["Office extraction requires optional dependency: pip install devgraph-os[docs]"],
            )
