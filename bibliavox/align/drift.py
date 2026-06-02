"""CTC drift compensation for long audio chapters.

Chunks audio at VAD-detected silence boundaries, aligns each chunk independently,
and merges results with confidence-based conflict resolution.

Per D-15, D-16, D-17 from RESEARCH.md:
- D-15: VAD-based chunking using silero-vad for natural silence boundaries
- D-16: 500ms-1s overlap between chunks for continuity at boundaries
- D-17: Confidence-based merge for overlapping timestamps
"""

import logging
from typing import Any, Callable

try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def get_vad_segments(
    audio: Any,
    sr: int,
    threshold: float = 0.5,
) -> list[tuple[float, float]]:
    """Detect speech segments using silero-vad.

    Args:
        audio: 1D tensor of audio samples.
        sr: Sample rate (must be 16000 for silero-vad).
        threshold: Speech probability threshold.

    Returns:
        List of (start_sec, end_sec) tuples for detected speech regions.
    """
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        trust_repo=True,
    )
    get_speech_timestamps = utils[0]
    speech_timestamps = get_speech_timestamps(
        audio, model, sampling_rate=sr, threshold=threshold
    )
    return [(ts["start"] / sr, ts["end"] / sr) for ts in speech_timestamps]


def chunk_audio_by_vad(
    audio: Any,
    sr: int,
    overlap_ms: float = 500.0,
    min_chunk_sec: float = 5.0,
) -> list[dict[str, Any]]:
    """Chunk audio at VAD-detected silence boundaries with overlap.

    Args:
        audio: 1D tensor of audio samples.
        sr: Sample rate.
        overlap_ms: Overlap between adjacent chunks in milliseconds (D-16: 500ms-1s).
        min_chunk_sec: Minimum chunk duration in seconds.

    Returns:
        List of dicts with keys:
        - "audio": torch.Tensor chunk
        - "start_sample": int
        - "end_sample": int
        - "start_sec": float
        - "end_sec": float
    """
    vad_segments = get_vad_segments(audio, sr)
    if not vad_segments:
        # No speech detected — return whole audio as one chunk
        return [
            {
                "audio": audio,
                "start_sample": 0,
                "end_sample": len(audio),
                "start_sec": 0.0,
                "end_sec": len(audio) / sr,
            }
        ]

    overlap_samples = int(overlap_ms * sr / 1000)
    chunks: list[dict[str, Any]] = []

    for seg_start_sec, seg_end_sec in vad_segments:
        start_sample = max(0, int(seg_start_sec * sr) - overlap_samples)
        end_sample = min(len(audio), int(seg_end_sec * sr) + overlap_samples)

        chunks.append(
            {
                "audio": audio[start_sample:end_sample],
                "start_sample": start_sample,
                "end_sample": end_sample,
                "start_sec": start_sample / sr,
                "end_sec": end_sample / sr,
            }
        )

    # Merge adjacent chunks that are too close together
    merged: list[dict[str, Any]] = []
    for chunk in chunks:
        if merged and (chunk["start_sec"] - merged[-1]["end_sec"]) < min_chunk_sec:
            # Extend previous chunk
            prev = merged[-1]
            prev["end_sample"] = chunk["end_sample"]
            prev["end_sec"] = chunk["end_sec"]
            prev["audio"] = audio[prev["start_sample"] : prev["end_sample"]]
        else:
            merged.append(chunk)

    return merged


def merge_chunk_results(
    chunk_results: list[list[dict[str, Any]]],
    chunk_offsets: list[float],
    overlap_ms: float = 500.0,
) -> list[dict[str, Any]]:
    """Merge alignment results from overlapping chunks using confidence scores.

    Args:
        chunk_results: List of word lists from each chunk.
        chunk_offsets: Start time offset for each chunk in seconds.
        overlap_ms: Overlap window in milliseconds.

    Returns:
        Merged list of word dicts sorted by start time.
    """
    # Adjust timestamps by chunk offsets
    adjusted: list[dict[str, Any]] = []
    for chunk_words, offset in zip(chunk_results, chunk_offsets):
        for word in chunk_words:
            adjusted.append(
                {
                    **word,
                    "start": word["start"] + offset,
                    "end": word["end"] + offset,
                }
            )

    # Sort by start time
    adjusted.sort(key=lambda w: w["start"])

    # Remove duplicates in overlap regions (keep higher confidence)
    overlap_sec = overlap_ms / 1000
    merged: list[dict[str, Any]] = []
    for word in adjusted:
        if merged and abs(word["start"] - merged[-1]["start"]) < overlap_sec:
            # Same word in overlap region — keep higher confidence
            existing = merged[-1]
            existing_score = existing.get("score", existing.get("probability", 0))
            new_score = word.get("score", word.get("probability", 0))
            if new_score > existing_score:
                merged[-1] = word
        else:
            merged.append(word)

    return merged


def snap_to_vad(
    words: list[dict[str, Any]],
    vad_segments: list[tuple[float, float]],
    tolerance_ms: float = 100.0,
) -> list[dict[str, Any]]:
    """Snap word boundaries to VAD-detected speech regions.

    Args:
        words: List of word dicts with "start" and "end" keys.
        vad_segments: List of (start_sec, end_sec) speech regions.
        tolerance_ms: Maximum snap distance in milliseconds.

    Returns:
        List of word dicts with boundaries snapped to VAD regions.
    """
    if not vad_segments:
        return words

    refined: list[dict[str, Any]] = []

    for w in words:
        w_mid = (w["start"] + w["end"]) / 2

        # Find the VAD segment containing this word's midpoint
        best_seg = next(
            (s for s in vad_segments if s[0] <= w_mid <= s[1]),
            None,
        )

        if best_seg:
            # Snap boundaries to VAD segment edges if within tolerance
            w["start"] = max(w["start"], best_seg[0])
            w["end"] = min(w["end"], best_seg[1])
        else:
            # Word is in silence — snap to nearest speech region
            closest = min(
                vad_segments,
                key=lambda s: min(abs(w_mid - s[0]), abs(w_mid - s[1])),
            )
            if w_mid < closest[0]:
                w["start"] = closest[0]
                w["end"] = closest[0] + 0.1
            else:
                w["start"] = closest[1] - 0.1
                w["end"] = closest[1]

        refined.append(w)

    return refined


def compensate_drift(
    audio: Any,
    sr: int,
    align_fn: Callable[[Any], list[dict[str, Any]]],
    overlap_ms: float = 500.0,
) -> list[dict[str, Any]]:
    """Full drift compensation pipeline: chunk, align, merge, snap.

    Args:
        audio: 1D tensor of audio samples.
        sr: Sample rate.
        align_fn: Function that takes an audio tensor and returns word-level alignment results.
        overlap_ms: Overlap between chunks in milliseconds (D-16).

    Returns:
        Merged and snapped word-level alignment results.
    """
    if len(audio) == 0:
        return []

    chunks = chunk_audio_by_vad(audio, sr, overlap_ms=overlap_ms)

    if len(chunks) <= 1:
        # Short audio — no chunking needed
        return align_fn(audio)

    # Align each chunk
    chunk_results: list[list[dict[str, Any]]] = []
    chunk_offsets: list[float] = []
    for chunk in chunks:
        words = align_fn(chunk["audio"])
        chunk_results.append(words)
        chunk_offsets.append(chunk["start_sec"])

    # Merge overlapping results
    merged = merge_chunk_results(chunk_results, chunk_offsets, overlap_ms=overlap_ms)

    # Snap to VAD boundaries
    vad_segments = get_vad_segments(audio, sr)
    snapped = snap_to_vad(merged, vad_segments)

    return snapped
