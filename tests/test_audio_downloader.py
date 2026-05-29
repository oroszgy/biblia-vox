"""Tests for resilient audio downloader workflows."""

from __future__ import annotations

from pathlib import Path

from bibliavox.audio.downloader import download_all, download_chapter


class _FakeResponse:
    def __init__(
        self, status_code: int, chunks: list[bytes], should_raise: bool = False
    ):
        self.status_code = status_code
        self._chunks = chunks
        self._should_raise = should_raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        if self._should_raise:
            raise RuntimeError("request failed")

    def iter_bytes(self) -> list[bytes]:
        return self._chunks


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def stream(self, method: str, url: str, headers: dict[str, str] | None = None):
        self.calls.append({"method": method, "url": url, "headers": headers or {}})
        return self._responses.pop(0)


def _sample_item(book: str, chapter: int, suffix: str = "") -> dict[str, object]:
    return {
        "book_usx": book,
        "chapter": chapter,
        "url": f"https://mek.oszk.hu/08800/08820/mp3/{book.lower()}-{chapter}{suffix}.mp3",
        "relative_path": f"{book.lower()}-{chapter}{suffix}.mp3",
        "extinf_sec": 10,
        "source": "mek.m3u",
    }


def test_partial_part_file_resumes_when_response_is_206(tmp_path: Path) -> None:
    item = _sample_item("GEN", 1)
    target = tmp_path / "data" / "raw"
    part_path = target / "GEN" / "001.mp3.part"
    part_path.parent.mkdir(parents=True, exist_ok=True)
    part_path.write_bytes(b"hello")

    fake_client = _FakeClient([_FakeResponse(status_code=206, chunks=[b" world"])])
    result = download_chapter(item, target, client=fake_client)

    assert result["status"] == "downloaded"
    assert (target / "GEN" / "001.mp3").read_bytes() == b"hello world"
    assert fake_client.calls[0]["headers"] == {"Range": "bytes=5-"}


def test_response_200_overwrites_part_instead_of_append(tmp_path: Path) -> None:
    item = _sample_item("GEN", 2)
    target = tmp_path / "data" / "raw"
    part_path = target / "GEN" / "002.mp3.part"
    part_path.parent.mkdir(parents=True, exist_ok=True)
    part_path.write_bytes(b"stale")

    fake_client = _FakeClient([_FakeResponse(status_code=200, chunks=[b"fresh"])])
    result = download_chapter(item, target, client=fake_client)

    assert result["status"] == "downloaded"
    assert (target / "GEN" / "002.mp3").read_bytes() == b"fresh"
    assert fake_client.calls[0]["headers"] == {"Range": "bytes=5-"}


def test_download_all_applies_worker_limit_skip_and_failure_summary(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "data" / "raw"
    existing = output_root / "GEN" / "001.mp3"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_bytes(b"existing")

    items = [
        _sample_item("GEN", 1),
        _sample_item("GEN", 2),
        _sample_item("GEN", 3),
    ]

    class _ExecutorSpy:
        recorded_workers: int | None = None

        def __init__(self, max_workers: int):
            self.recorded_workers = max_workers
            _ExecutorSpy.recorded_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, fn, inputs):
            return [fn(item) for item in inputs]

    class _FailingClient(_FakeClient):
        pass

    clients = {
        items[1]["url"]: _FakeClient([_FakeResponse(status_code=200, chunks=[b"ok"])])
    }

    def _client_factory(url: str):
        if url == items[2]["url"]:
            return _FakeClient(
                [_FakeResponse(status_code=500, chunks=[], should_raise=True)]
            )
        return clients[url]

    summary = download_all(
        items,
        output_root,
        workers=2,
        client_factory=_client_factory,
        executor_cls=_ExecutorSpy,
    )

    assert _ExecutorSpy.recorded_workers == 2
    assert len(summary["downloaded"]) == 1
    assert len(summary["skipped"]) == 1
    assert len(summary["failed"]) == 1
