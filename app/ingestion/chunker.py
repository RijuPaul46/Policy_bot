def find_page_numbers(
    start: int,
    end: int,
    page_info: list[tuple[int, int, int]],
) -> list[int]:
    if start < 0 or end <= start or not page_info:
        return []
    return [
        page_number
        for page_start, page_end, page_number in page_info
        if page_start < end and page_end > start
    ]


def find_chunk_info(
    start: int,
    end: int,
    page_info: list[tuple[int, int, int]],
) -> dict:
    return {"start": start, "end": end, "pages": find_page_numbers(start, end, page_info)}


def _next_boundary(text: str, start: int, desired_end: int) -> int:
    if desired_end >= len(text):
        return len(text)
    floor = start + max(1, (desired_end - start) // 2)
    for separator in ("\n\n", "\n", ". ", " "):
        boundary = text.rfind(separator, floor, desired_end)
        if boundary >= floor:
            return boundary + len(separator)
    return desired_end


def split_text(
    text: str,
    page_info: list[tuple[int, int, int]],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap smaller than chunk_size")

    chunks: list[dict] = []
    start = 0
    while start < len(text):
        end = _next_boundary(text, start, min(start + chunk_size, len(text)))
        if end <= start:
            raise ValueError("Chunking did not advance")
        content = text[start:end].strip()
        if content:
            chunks.append(
                {
                    "text": content,
                    "start": start,
                    "end": end,
                    "pages": find_page_numbers(start, end, page_info),
                }
            )
        if end == len(text):
            break
        start = max(start + 1, end - chunk_overlap)
    return chunks
