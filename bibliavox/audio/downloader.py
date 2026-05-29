"""Resilient chapter audio downloader with retry and batch support."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypedDict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class DownloadResult(TypedDict):
    """Single chapter download result."""

    book_usx: str
    chapter: int
    target: str
    status: str
    error: str | None


class BatchSummary(TypedDict):
    """Batch download summary split by outcome."""

    downloaded: list[DownloadResult]
    skipped: list[DownloadResult]
    failed: list[DownloadResult]


def _target_path(item: dict[str, Any], output_root: Path) -> Path:
    book = str(item["book_usx"]).upper()
    chapter = int(item["chapter"])
    return output_root / book / f"{chapter:03d}.mp3"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _stream_download(
    client: Any,
    url: str,
    part_path: Path,
    resume_from: int,
) -> None:
    headers = {"Range": f"bytes={resume_from}-"} if resume_from > 0 else {}
    with client.stream("GET", url, headers=headers) as response:
        response.raise_for_status()

        mode = "ab" if resume_from > 0 and response.status_code == 206 else "wb"
        with open(part_path, mode) as file_handle:
            for chunk in response.iter_bytes():
                file_handle.write(chunk)


def download_chapter(
    item: dict[str, Any],
    output_root: Path,
    *,
    client: Any | None = None,
    force: bool = False,
) -> DownloadResult:
    """Download one chapter to canonical raw artifact path."""
    target = _target_path(item, output_root)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and not force:
        return DownloadResult(
            book_usx=str(item["book_usx"]),
            chapter=int(item["chapter"]),
            target=str(target),
            status="skipped",
            error=None,
        )

    part_path = target.with_suffix(f"{target.suffix}.part")
    resume_from = part_path.stat().st_size if part_path.exists() else 0

    owned_client = client is None
    http_client = client or httpx.Client(
        timeout=httpx.Timeout(30.0, connect=30.0, read=30.0, write=30.0, pool=10.0),
        limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
        follow_redirects=True,
    )

    try:
        _stream_download(http_client, str(item["url"]), part_path, resume_from)
        part_path.replace(target)
        return DownloadResult(
            book_usx=str(item["book_usx"]),
            chapter=int(item["chapter"]),
            target=str(target),
            status="downloaded",
            error=None,
        )
    except Exception as exc:  # noqa: BLE001
        return DownloadResult(
            book_usx=str(item["book_usx"]),
            chapter=int(item["chapter"]),
            target=str(target),
            status="failed",
            error=str(exc),
        )
    finally:
        if owned_client:
            http_client.close()


def download_all(
    manifest: list[dict[str, Any]],
    output_root: Path,
    *,
    workers: int = 4,
    force: bool = False,
    client_factory: Any | None = None,
    executor_cls: type[ThreadPoolExecutor] = ThreadPoolExecutor,
) -> BatchSummary:
    """Download all manifest chapters with bounded parallel workers."""
    safe_workers = max(1, workers)

    def _client_for(url: str) -> Any:
        if client_factory is not None:
            return client_factory(url)
        return httpx.Client(
            timeout=httpx.Timeout(30.0, connect=30.0, read=30.0, write=30.0, pool=10.0),
            limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
            follow_redirects=True,
        )

    def _run_one(item: dict[str, Any]) -> DownloadResult:
        target = _target_path(item, output_root)
        if target.exists() and not force:
            return DownloadResult(
                book_usx=str(item["book_usx"]),
                chapter=int(item["chapter"]),
                target=str(target),
                status="skipped",
                error=None,
            )

        url = str(item["url"])
        client = _client_for(url)
        try:
            return download_chapter(item, output_root, client=client, force=force)
        finally:
            if hasattr(client, "close"):
                client.close()

    with executor_cls(max_workers=safe_workers) as executor:
        results = list(executor.map(_run_one, manifest))

    downloaded = [result for result in results if result["status"] == "downloaded"]
    skipped = [result for result in results if result["status"] == "skipped"]
    failed = [result for result in results if result["status"] == "failed"]

    return BatchSummary(downloaded=downloaded, skipped=skipped, failed=failed)
