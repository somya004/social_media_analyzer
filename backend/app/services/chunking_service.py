import uuid
from dataclasses import dataclass, field
from app.utils.logging import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 700
CHUNK_OVERLAP = 120


@dataclass
class TextChunk:
    chunk_id: str
    video_id: str
    source: str          # "youtube" | "instagram"
    text: str
    start_char: int
    end_char: int
    metadata: dict = field(default_factory=dict)


class TranscriptChunker:

    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> None:
        if overlap >= chunk_size:
            raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(
        self,
        text: str,
        video_id: str,
        source: str,
        metadata: dict,
    ) -> list[TextChunk]:
        text = text.strip()
        if not text:
            logger.warning("chunk_text called with empty text  video_id=%s", video_id)
            return []

        raw_spans = self._split(text)
        chunks = []
        for start, end in raw_spans:
            chunk_text = text[start:end].strip()
            if not chunk_text:
                continue
            chunks.append(
                TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    video_id=video_id,
                    source=source,
                    text=chunk_text,
                    start_char=start,
                    end_char=end,
                    metadata=metadata.copy(),
                )
            )

        logger.debug(
            "chunked  video_id=%s  source=%s  total_chars=%d  chunks=%d",
            video_id, source, len(text), len(chunks),
        )
        return chunks

    def _split(self, text: str) -> list[tuple[int, int]]:
        """
        Slide a window of size chunk_size over the text with step
        (chunk_size - overlap). Tries to break at sentence or word
        boundaries within a small tolerance window.
        """
        step = self.chunk_size - self.overlap
        spans: list[tuple[int, int]] = []
        start = 0
        length = len(text)

        while start < length:
            end = min(start + self.chunk_size, length)

            # Try to snap the end to a sentence boundary first, then word boundary.
            if end < length:
                snapped = self._snap_boundary(text, end)
                if snapped is not None:
                    end = snapped

            spans.append((start, end))

            if end >= length:
                break

            start = end - self.overlap

        return spans

    def _snap_boundary(self, text: str, pos: int, tolerance: int = 80) -> int | None:
        """
        Look backwards from pos within tolerance chars for a sentence-ending
        punctuation followed by whitespace, or failing that a whitespace char.
        Returns the adjusted position, or None if no boundary found.
        """
        search_start = max(0, pos - tolerance)
        window = text[search_start:pos]

        # Prefer sentence boundary: '. ', '! ', '? '
        for i in range(len(window) - 1, -1, -1):
            if window[i] in ".!?" and (i + 1 < len(window) and window[i + 1] == " "):
                return search_start + i + 2  # start after the space

        # Fall back to any whitespace
        for i in range(len(window) - 1, -1, -1):
            if window[i] == " ":
                return search_start + i + 1

        return None
