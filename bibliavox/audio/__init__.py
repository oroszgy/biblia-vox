"""Audio pipeline helpers for discovery, download, convert, prepare, and seek."""

from bibliavox.audio.convert import AudioConversionError, convert_to_wav
from bibliavox.audio.discovery import build_audio_manifest, inventory_report, parse_m3u
from bibliavox.audio.metadata import AudioProbeError, format_audio_info, probe_audio
from bibliavox.audio.pipeline import prepare_chapter
from bibliavox.audio.seek_index import (
    SeekIndexError,
    build_seek_index,
    resolve_sample_window,
    write_seek_preview,
)

__all__ = [
    "AudioConversionError",
    "AudioProbeError",
    "SeekIndexError",
    "build_audio_manifest",
    "build_seek_index",
    "convert_to_wav",
    "format_audio_info",
    "inventory_report",
    "parse_m3u",
    "prepare_chapter",
    "probe_audio",
    "resolve_sample_window",
    "write_seek_preview",
]
