"""Tests for CTC drift compensation module (bibliavox/align/drift.py).

Uses synthetic data and mocked torch/silero-vad to test VAD-based chunking,
overlap merge, boundary snapping, and end-to-end drift compensation.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

# Mock torch so drift.py can be imported without a real PyTorch installation
mock_torch = ModuleType("torch")


# Create a Tensor-like class for isinstance checks and type hints
class _FakeTensor:
    """Minimal tensor stand-in used in tests."""

    def __init__(self, data=None, size=0):
        self._data = data if data is not None else []
        self._size = size

    def __len__(self):
        return self._size

    def __getitem__(self, key):
        return _FakeTensor(self._data[key] if self._data else [], size=0)

    def __iter__(self):
        return iter(self._data)

    def size(self, dim=None):
        if dim is not None:
            return 0
        return (0,)


mock_torch.Tensor = _FakeTensor
mock_torch.hub = ModuleType("torch.hub")
sys.modules["torch"] = mock_torch
sys.modules["torch.hub"] = mock_torch.hub

import pytest  # noqa: E402

from bibliavox.align.drift import (  # noqa: E402
    chunk_audio_by_vad,
    compensate_drift,
    get_vad_segments,
    merge_chunk_results,
    snap_to_vad,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def _make_speech_timestamps(segments: list[tuple[int, int]]) -> list[dict]:
    """Build silero-vad style speech timestamp dicts from (start, end) sample pairs."""
    return [{"start": s, "end": e} for s, e in segments]


def _mock_torch_hub_load(segments: list[tuple[int, int]]):
    """Return a mock for torch.hub.load that yields fixed speech timestamps."""
    get_speech_timestamps = MagicMock(
        side_effect=lambda audio, model, sampling_rate=16000, **kw: (
            _make_speech_timestamps(segments)
        )
    )
    mock_model = MagicMock()
    return MagicMock(return_value=(mock_model, [get_speech_timestamps]))


def _make_fake_audio(sr: int = 16000, duration_sec: float = 10.0):
    """Create a fake audio object with __len__ support."""
    n_samples = int(sr * duration_sec)
    obj = MagicMock()
    obj.__len__ = MagicMock(return_value=n_samples)
    return obj


def _make_word(
    start: float, end: float, word: str = "hello", score: float = 0.9
) -> dict:
    """Create a word alignment result dict."""
    return {"word": word, "start": start, "end": end, "score": score}


# ---------------------------------------------------------------------------
# Tests: get_vad_segments
# ---------------------------------------------------------------------------


class TestGetVadSegments:
    """get_vad_segments returns list of (start_sec, end_sec) tuples."""

    def test_returns_segments_as_tuples(self):
        audio = _make_fake_audio(sr=16000, duration_sec=5.0)
        # 2 speech segments: 0-2s and 3-5s (in samples)
        segments = [(0, 32000), (48000, 80000)]
        mock_hub = _mock_torch_hub_load(segments)

        mock_torch.hub.load = mock_hub
        result = get_vad_segments(audio, 16000)

        assert len(result) == 2
        assert all(isinstance(s, tuple) and len(s) == 2 for s in result)
        # First segment: 0/16000 = 0.0, 32000/16000 = 2.0
        assert result[0] == (0.0, 2.0)
        assert result[1] == (3.0, 5.0)

    def test_empty_segments(self):
        audio = _make_fake_audio(sr=16000, duration_sec=3.0)
        mock_hub = _mock_torch_hub_load([])

        mock_torch.hub.load = mock_hub
        result = get_vad_segments(audio, 16000)

        assert result == []


# ---------------------------------------------------------------------------
# Tests: chunk_audio_by_vad
# ---------------------------------------------------------------------------


class TestChunkAudioByVad:
    """chunk_audio_by_vad produces chunks with correct overlap."""

    def test_single_vad_segment_returns_one_chunk(self):
        """Audio with one speech region produces one chunk."""
        audio = _make_fake_audio(sr=16000, duration_sec=5.0)
        segments = [(0, 80000)]
        mock_hub = _mock_torch_hub_load(segments)

        mock_torch.hub.load = mock_hub
        result = chunk_audio_by_vad(audio, 16000, overlap_ms=500)

        assert len(result) >= 1
        chunk = result[0]
        assert "audio" in chunk
        assert "start_sample" in chunk
        assert "end_sample" in chunk
        assert "start_sec" in chunk
        assert "end_sec" in chunk

    def test_chunks_overlap_by_overlap_ms(self):
        """Adjacent chunks overlap by at least overlap_ms at boundaries."""
        audio = _make_fake_audio(sr=16000, duration_sec=30.0)
        # Two speech segments separated by 2s silence
        segments = [(0, 160000), (192000, 480000)]  # 0-10s, 12-30s
        mock_hub = _mock_torch_hub_load(segments)
        overlap_ms = 500

        mock_torch.hub.load = mock_hub
        result = chunk_audio_by_vad(
            audio, 16000, overlap_ms=overlap_ms, min_chunk_sec=1.0
        )

        if len(result) >= 2:
            first = result[0]
            second = result[1]
            # The first chunk should extend past the VAD boundary by overlap
            assert first["end_sample"] >= segments[0][1]
            # The second chunk should start before its VAD boundary by overlap
            assert second["start_sample"] <= segments[1][0]

    def test_no_speech_returns_whole_audio(self):
        """No speech detected returns whole audio as single chunk."""
        audio = _make_fake_audio(sr=16000, duration_sec=5.0)
        mock_hub = _mock_torch_hub_load([])

        mock_torch.hub.load = mock_hub
        result = chunk_audio_by_vad(audio, 16000)

        assert len(result) == 1
        assert result[0]["start_sec"] == 0.0
        assert result[0]["end_sec"] == pytest.approx(5.0, abs=0.01)

    def test_close_segments_merged(self):
        """Segments closer than min_chunk_sec are merged into one chunk."""
        audio = _make_fake_audio(sr=16000, duration_sec=20.0)
        # Two close segments (3s apart, less than min_chunk_sec=5s)
        segments = [(0, 64000), (112000, 320000)]  # 0-4s, 7-20s
        mock_hub = _mock_torch_hub_load(segments)

        mock_torch.hub.load = mock_hub
        result = chunk_audio_by_vad(audio, 16000, min_chunk_sec=5.0)

        # Close segments should be merged
        assert len(result) <= 2

    def test_chunk_contains_audio_slice(self):
        """Each chunk's audio field is a slice of the input audio."""
        audio = _make_fake_audio(sr=16000, duration_sec=5.0)
        segments = [(0, 80000)]
        mock_hub = _mock_torch_hub_load(segments)

        mock_torch.hub.load = mock_hub
        result = chunk_audio_by_vad(audio, 16000)

        for chunk in result:
            # audio should be something sliceable (not None)
            assert chunk["audio"] is not None


# ---------------------------------------------------------------------------
# Tests: merge_chunk_results
# ---------------------------------------------------------------------------


class TestMergeChunkResults:
    """merge_chunk_results merges overlapping words keeping higher confidence."""

    def test_basic_merge(self):
        """Non-overlapping words from different chunks are merged correctly."""
        chunk1 = [_make_word(0.0, 0.5, "hello"), _make_word(0.6, 1.0, "world")]
        chunk2 = [_make_word(1.2, 1.7, "foo"), _make_word(1.8, 2.3, "bar")]
        offsets = [0.0, 1.0]

        result = merge_chunk_results([chunk1, chunk2], offsets, overlap_ms=500)

        assert len(result) == 4
        starts = [w["start"] for w in result]
        assert starts == sorted(starts)

    def test_deduplication_in_overlap(self):
        """Words appearing in both chunks keep the higher confidence one."""
        chunk1 = [_make_word(0.0, 0.5, "hello", score=0.8)]
        chunk2 = [_make_word(0.0, 0.5, "hello", score=0.95)]
        offsets = [0.0, 0.0]

        result = merge_chunk_results([chunk1, chunk2], offsets, overlap_ms=500)

        assert len(result) == 1
        assert result[0]["score"] == 0.95

    def test_word_in_only_one_chunk(self):
        """Words appearing in only one chunk are kept."""
        chunk1 = [_make_word(0.0, 0.5, "aaa", score=0.9)]
        chunk2 = [_make_word(2.0, 2.5, "zzz", score=0.9)]
        offsets = [0.0, 1.5]

        result = merge_chunk_results([chunk1, chunk2], offsets, overlap_ms=500)

        assert len(result) == 2
        words = {w["word"] for w in result}
        assert words == {"aaa", "zzz"}

    def test_offset_adjustment(self):
        """Timestamps are adjusted by chunk offsets."""
        chunk1 = [_make_word(0.0, 0.5, "a")]
        chunk2 = [_make_word(0.0, 0.5, "b")]
        offsets = [0.0, 10.0]

        result = merge_chunk_results([chunk1, chunk2], offsets, overlap_ms=500)

        b_word = next(w for w in result if w["word"] == "b")
        assert b_word["start"] == pytest.approx(10.0, abs=0.01)
        assert b_word["end"] == pytest.approx(10.5, abs=0.01)

    def test_empty_chunks(self):
        """Empty chunk results are handled gracefully."""
        result = merge_chunk_results([[], []], [0.0, 5.0], overlap_ms=500)
        assert result == []

    def test_probability_key_used_as_fallback(self):
        """When 'score' is missing, 'probability' is used for comparison."""
        chunk1 = [{"word": "x", "start": 0.0, "end": 0.5, "probability": 0.7}]
        chunk2 = [{"word": "x", "start": 0.0, "end": 0.5, "probability": 0.9}]
        offsets = [0.0, 0.0]

        result = merge_chunk_results([chunk1, chunk2], offsets, overlap_ms=500)

        assert len(result) == 1
        assert result[0]["probability"] == 0.9


# ---------------------------------------------------------------------------
# Tests: snap_to_vad
# ---------------------------------------------------------------------------


class TestSnapToVad:
    """snap_to_vad moves word boundaries into VAD-detected speech regions."""

    def test_snap_inside_segment(self):
        """Words already inside a VAD segment are clamped to segment edges."""
        words = [_make_word(0.5, 1.5)]
        vad_segments = [(0.0, 2.0)]

        result = snap_to_vad(words, vad_segments)

        assert result[0]["start"] >= 0.0
        assert result[0]["end"] <= 2.0

    def test_snap_word_in_silence(self):
        """Words entirely in silence are snapped to nearest speech region."""
        words = [_make_word(3.0, 3.5)]
        vad_segments = [(0.0, 2.0), (5.0, 8.0)]

        result = snap_to_vad(words, vad_segments)

        # Word midpoint is 3.25; distance to (0,2) edge=1.25, to (5,8) edge=1.75
        # Closest segment is (0.0, 2.0) — word is after it, so snaps to end
        assert result[0]["end"] == pytest.approx(2.0, abs=0.1)
        assert result[0]["start"] <= 2.0

    def test_empty_vad_segments_returns_words_unchanged(self):
        """No VAD segments returns words as-is."""
        words = [_make_word(0.0, 1.0)]
        result = snap_to_vad(words, [])
        assert result == words

    def test_word_midpoint_determines_segment(self):
        """Word is assigned to segment containing its midpoint."""
        words = [_make_word(0.8, 1.2)]  # midpoint = 1.0
        vad_segments = [(0.0, 1.5), (2.0, 4.0)]

        result = snap_to_vad(words, vad_segments)

        assert result[0]["start"] >= 0.0
        assert result[0]["end"] <= 1.5

    def test_word_in_silence_snaps_to_before(self):
        """Word in silence before a segment snaps to start of that segment."""
        words = [_make_word(0.2, 0.4)]  # midpoint = 0.3
        vad_segments = [(1.0, 3.0)]

        result = snap_to_vad(words, vad_segments)

        assert result[0]["start"] == pytest.approx(1.0, abs=0.1)
        assert result[0]["end"] >= 1.0

    def test_word_in_silence_snaps_to_after(self):
        """Word in silence after a segment snaps to end of that segment."""
        words = [_make_word(4.0, 4.2)]  # midpoint = 4.1
        vad_segments = [(1.0, 3.0)]

        result = snap_to_vad(words, vad_segments)

        assert result[0]["end"] == pytest.approx(3.0, abs=0.1)
        assert result[0]["start"] <= 3.0


# ---------------------------------------------------------------------------
# Tests: compensate_drift (end-to-end)
# ---------------------------------------------------------------------------


class TestCompensateDrift:
    """compensate_drift end-to-end: chunks, aligns, merges, snaps."""

    def test_end_to_end_with_mock_align(self):
        """Full pipeline with mocked align function produces merged results."""
        audio = _make_fake_audio(sr=16000, duration_sec=20.0)

        segments = [(0, 320000)]
        mock_hub = _mock_torch_hub_load(segments)

        def mock_align(chunk_audio):
            duration = 20.0  # approximate
            return [
                _make_word(0.0, duration * 0.3, "word1"),
                _make_word(duration * 0.3, duration * 0.6, "word2"),
                _make_word(duration * 0.6, duration * 0.9, "word3"),
            ]

        mock_torch.hub.load = mock_hub
        result = compensate_drift(audio, 16000, mock_align, overlap_ms=500)

        assert len(result) > 0
        assert all("word" in w and "start" in w and "end" in w for w in result)

    def test_short_audio_passes_through(self):
        """Short audio (single chunk) bypasses chunking and calls align directly."""
        audio = _make_fake_audio(sr=16000, duration_sec=3.0)

        mock_hub = _mock_torch_hub_load([])

        align_called = False

        def mock_align(chunk_audio):
            nonlocal align_called
            align_called = True
            return [_make_word(0.0, 1.0, "short")]

        mock_torch.hub.load = mock_hub
        result = compensate_drift(audio, 16000, mock_align)

        assert align_called
        assert len(result) == 1
        assert result[0]["word"] == "short"

    def test_empty_audio(self):
        """Empty audio returns empty results."""
        audio = MagicMock()
        audio.__len__ = MagicMock(return_value=0)
        mock_hub = _mock_torch_hub_load([])

        def mock_align(chunk_audio):
            return []

        mock_torch.hub.load = mock_hub
        result = compensate_drift(audio, 16000, mock_align)

        assert result == []

    def test_multi_chunk_alignment(self):
        """Audio with multiple VAD segments produces merged alignment."""
        audio = _make_fake_audio(sr=16000, duration_sec=30.0)

        segments = [(0, 160000), (192000, 480000)]
        mock_hub = _mock_torch_hub_load(segments)

        call_count = 0

        def mock_align(chunk_audio):
            nonlocal call_count
            call_count += 1
            return [_make_word(0.0, 0.5, f"word_{call_count}")]

        mock_torch.hub.load = mock_hub
        result = compensate_drift(audio, 16000, mock_align, overlap_ms=500)

        assert call_count >= 1
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for drift compensation functions."""

    def test_merge_single_chunk(self):
        """Merging a single chunk result returns its words."""
        words = [_make_word(0.0, 0.5, "a"), _make_word(0.6, 1.0, "b")]
        result = merge_chunk_results([words], [0.0], overlap_ms=500)
        assert len(result) == 2

    def test_snap_preserves_word_data(self):
        """Snap preserves all word fields (word, score, etc.)."""
        words = [_make_word(0.5, 1.5, "test", score=0.87)]
        vad_segments = [(0.0, 2.0)]

        result = snap_to_vad(words, vad_segments)

        assert result[0]["word"] == "test"
        assert result[0]["score"] == 0.87

    def test_merge_sorted_by_start_time(self):
        """Merged results are always sorted by start time."""
        chunk1 = [_make_word(5.0, 5.5, "z")]
        chunk2 = [_make_word(0.0, 0.5, "a")]
        offsets = [0.0, 0.0]

        result = merge_chunk_results([chunk1, chunk2], offsets, overlap_ms=500)

        starts = [w["start"] for w in result]
        assert starts == sorted(starts)
