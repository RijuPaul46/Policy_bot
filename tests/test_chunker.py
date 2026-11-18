import pytest

from app.ingestion.chunker import find_page_numbers, split_text


def test_find_page_numbers_for_single_and_spanning_chunks():
    pages = [(0, 5, 1), (6, 11, 2), (12, 17, 3)]

    assert find_page_numbers(1, 4, pages) == [1]
    assert find_page_numbers(4, 13, pages) == [1, 2, 3]
    assert find_page_numbers(5, 5, pages) == []


def test_split_text_preserves_content_and_page_metadata():
    text = "alpha beta gamma delta epsilon"
    pages = [(0, 15, 1), (16, len(text), 2)]

    chunks = split_text(text, pages, chunk_size=16, chunk_overlap=4)

    assert len(chunks) > 1
    assert chunks[0]["pages"] == [1]
    assert chunks[-1]["pages"] == [2]
    assert all(chunk["text"] for chunk in chunks)


def test_split_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        split_text("text", [], chunk_size=10, chunk_overlap=10)
