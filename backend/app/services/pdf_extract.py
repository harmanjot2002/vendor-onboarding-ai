import io
from pypdf import PdfReader


def extract_text_and_metadata(file_bytes: bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    # Note: extract_text() pulls every text object regardless of fill color, so white-on-white
    # text (used in the prompt-injection test PDF) is extracted just like any visible text.
    text_parts = [page.extract_text() or "" for page in reader.pages]

    metadata = dict(reader.metadata or {})
    return {
        "text": "\n".join(text_parts),
        "metadata": metadata,
        "num_pages": len(reader.pages),
    }
