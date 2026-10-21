from __future__ import annotations

from pathlib import Path

Manifest = dict[str, dict[str, object]]
Catalog = dict[str, str]
REGISTERED_STATUSES = {"accepted", "ignored"}


def keys_dropped_by_extraction(
    previous_manifest: Manifest,
    current_manifest: Manifest,
) -> list[str]:
    """Strings that the scanner does not produce, but the manifest carried as registered."""
    return sorted(
        key
        for key in set(previous_manifest) - set(current_manifest)
        if previous_manifest[key].get("status") in REGISTERED_STATUSES
    )


def span_matches(zed_root: Path, key: str, occurrence: dict[str, object]) -> bool:
    source_path = zed_root / str(occurrence["file"])
    try:
        source = source_path.read_bytes()
    except OSError:
        return False
    try:
        text = source[int(occurrence["start_byte"]) : int(occurrence["end_byte"])].decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return False
    return key in text


def readd_manual_strings(
    previous_manifest: Manifest,
    previous_catalog: Catalog,
    current_manifest: Manifest,
    current_catalog: Catalog,
    zed_root: Path,
) -> tuple[list[str], list[str]]:
    """Carry hand-registered strings across a re-extraction, verifying their byte spans first.

    Extraction rebuilds the manifest from the source, so strings that were registered by hand are
    not reproduced. Their offsets are only valid while the file they point at is unchanged, so each
    occurrence is checked against the source before it is carried over.
    """
    readded: list[str] = []
    mismatched: list[str] = []
    for key in keys_dropped_by_extraction(previous_manifest, current_manifest):
        entry = previous_manifest[key]
        occurrences = entry.get("occurrences") or []
        spans_match = bool(occurrences) and all(
            span_matches(zed_root, key, occurrence) for occurrence in occurrences
        )
        if not spans_match:
            mismatched.append(key)
            continue
        current_manifest[key] = entry
        current_catalog[key] = previous_catalog.get(key, key)
        readded.append(key)
    return readded, mismatched
