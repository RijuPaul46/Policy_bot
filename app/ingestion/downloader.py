from pathlib import Path
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (
        host == "wellsfargo.com" or host.endswith(".wellsfargo.com")
    ):
        raise ValueError("Only HTTPS URLs hosted on Wells Fargo domains are allowed")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _download(url: str, timeout: float) -> bytes:
    with httpx.stream(
        "GET",
        url,
        headers={"User-Agent": "PolicyBot/1.0 (policy document ingestion)"},
        timeout=timeout,
        follow_redirects=False,
    ) as response:
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > 50 * 1024 * 1024:
            raise ValueError(f"PDF from {url} exceeds the 50 MiB download limit")
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > 50 * 1024 * 1024:
                raise ValueError(f"PDF from {url} exceeds the 50 MiB download limit")
    content = bytes(body)
    if not content.startswith(b"%PDF"):
        raise ValueError(f"Response from {url} is not a PDF")
    return content


def download_pdfs(urls: list[str], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for index, url in enumerate(urls, start=1):
        _validate_url(url)
        filename = Path(urlparse(url).path).name or f"policy-{index}.pdf"
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        content = _download(url, timeout=30)
        path = output_dir / filename
        if path.exists():
            path = output_dir / f"{path.stem}-{index}{path.suffix}"
        path.write_bytes(content)
        saved.append(path)
    return saved
