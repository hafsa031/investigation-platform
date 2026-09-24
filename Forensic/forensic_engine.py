"""
forensic_engine.py
JagSpire AI - Sprint 1
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# HASHING

CHUNK_SIZE = 65536  # 64KB, so large evidence files don't blow up memory


def compute_sha256(file_path: Path) -> dict:
    """SHA-256 hash of the file — the chain-of-custody anchor. Computed
    first, always, before anything else touches the file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return {
        "algorithm": "SHA-256",
        "hash_value": sha256.hexdigest(),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_integrity(file_path: Path, expected_hash: str) -> bool:
    """Re-hash and compare — used to detect tampering of stored evidence."""
    return compute_sha256(file_path)["hash_value"].lower() == expected_hash.lower()



# FILE TYPE IDENTIFICATION (magic bytes, no libmagic dependency)

_SIGNATURES = [
    (b"\xff\xd8\xff", 0, "jpg", "image/jpeg", "image"),
    (b"\x89PNG\r\n\x1a\n", 0, "png", "image/png", "image"),
    (b"GIF87a", 0, "gif", "image/gif", "image"),
    (b"GIF89a", 0, "gif", "image/gif", "image"),
    (b"BM", 0, "bmp", "image/bmp", "image"),
    (b"II*\x00", 0, "tiff", "image/tiff", "image"),
    (b"MM\x00*", 0, "tiff", "image/tiff", "image"),
    (b"%PDF-", 0, "pdf", "application/pdf", "document"),
    (b"PK\x03\x04", 0, "zip", "application/zip", "archive"),  # also docx/xlsx/pptx
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", 0, "doc", "application/msword", "document"),
    (b"Rar!\x1a\x07\x00", 0, "rar", "application/x-rar-compressed", "archive"),
    (b"\x1f\x8b", 0, "gz", "application/gzip", "archive"),
    (b"ID3", 0, "mp3", "audio/mpeg", "audio"),
    (b"\x00\x00\x00\x18ftyp", 4, "mp4", "video/mp4", "video"),
]

_OOXML_INNER = {
    "word/document.xml": ("docx", "document"),
    "xl/workbook.xml": ("xlsx", "document"),
    "ppt/presentation.xml": ("pptx", "document"),
}


def _disambiguate_ooxml(file_path: Path):
    try:
        with zipfile.ZipFile(file_path) as zf:
            names = set(zf.namelist())
            for marker, result in _OOXML_INNER.items():
                if marker in names:
                    return result
    except (zipfile.BadZipFile, OSError):
        return None
    return None


def identify_file(file_path: Path) -> dict:
    """Detect the ACTUAL file type from content and compare it against the
    declared extension. A mismatch (e.g. a .pdf renamed to .jpg) is a
    tamper/disguise signal worth flagging to the investigator."""
    declared_ext = file_path.suffix.lstrip(".").lower() or None

    with open(file_path, "rb") as f:
        header = f.read(64)

    detected_ext, mime_type, category = None, None, "unknown"
    for sig, offset, ext, mime, cat in _SIGNATURES:
        if header[offset:offset + len(sig)] == sig:
            detected_ext, mime_type, category = ext, mime, cat
            break

    if detected_ext == "zip":
        ooxml = _disambiguate_ooxml(file_path)
        if ooxml:
            detected_ext, category = ooxml
            mime_type = mimetypes.guess_type(f"f.{detected_ext}")[0] or mime_type

    if detected_ext is None:
        guessed_mime, _ = mimetypes.guess_type(str(file_path))
        mime_type = guessed_mime
        detected_ext = declared_ext
        if declared_ext in {"log", "txt"}:
            category = "log"

    is_mismatch = bool(
        declared_ext and detected_ext and declared_ext != detected_ext
        and not (declared_ext in {"jpg", "jpeg"} and detected_ext in {"jpg", "jpeg"})
    )

    return {
        "declared_extension": declared_ext,
        "detected_extension": detected_ext,
        "mime_type": mime_type,
        "category": category,
        "is_mismatch": is_mismatch,
    }


# FILESYSTEM METADATA / TIMESTAMPS


def extract_filesystem_metadata(file_path: Path) -> dict:
    """NOTE: on most Linux filesystems 'created_time' actually reflects
    last metadata-change time, not true creation time. Flagged as low
    confidence downstream in the timeline for that reason."""
    stat = file_path.stat()
    created = getattr(stat, "st_birthtime", None)
    created_time = datetime.fromtimestamp(created) if created else datetime.fromtimestamp(stat.st_ctime)

    return {
        "file_name": file_path.name,
        "size_bytes": stat.st_size,
        "created_time": created_time.isoformat(),
        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed_time": datetime.fromtimestamp(stat.st_atime).isoformat(),
    }



# EXIF EXTRACTION (images)

def _convert_to_degrees(value) -> float:
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def extract_exif(file_path: Path) -> dict:
    """Returns has_exif=False for non-image or EXIF-less files — expected,
    not an error."""
    try:
        from PIL import Image, ExifTags
    except ImportError:
        return {"has_exif": False, "note": "Pillow not installed"}

    try:
        with Image.open(file_path) as img:
            exif_raw = img._getexif() if hasattr(img, "_getexif") else None
    except Exception:
        return {"has_exif": False}

    if not exif_raw:
        return {"has_exif": False}

    tags: dict[str, Any] = {}
    gps_info = None
    for tag_id, value in exif_raw.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        if tag_name == "GPSInfo":
            gps_info = value
            continue
        if isinstance(value, bytes):
            value = value.hex()
        tags[tag_name] = value

    lat = lon = None
    if gps_info:
        try:
            gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_info.items()}
            lat = _convert_to_degrees(gps_tags["GPSLatitude"])
            if gps_tags.get("GPSLatitudeRef") == "S":
                lat = -lat
            lon = _convert_to_degrees(gps_tags["GPSLongitude"])
            if gps_tags.get("GPSLongitudeRef") == "W":
                lon = -lon
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    return {
        "has_exif": True,
        "camera_make": tags.get("Make"),
        "camera_model": tags.get("Model"),
        "datetime_original": tags.get("DateTimeOriginal") or tags.get("DateTime"),
        "gps_latitude": lat,
        "gps_longitude": lon,
        "software": tags.get("Software"),
        "raw_tags": tags,
    }

#  DOCUMENT METADATA (PDF / DOCX)


def extract_document_metadata(file_path: Path, detected_extension: Optional[str]) -> Optional[dict]:
    """Returns None for unsupported/unreadable document types rather than
    raising, so the rest of the pipeline still completes."""
    ext = (detected_extension or "").lower()
    try:
        if ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            info = reader.metadata or {}
            return {
                "author": info.get("/Author") if info else None,
                "title": info.get("/Title") if info else None,
                "created": info.get("/CreationDate") if info else None,
                "modified": info.get("/ModDate") if info else None,
                "application": info.get("/Producer") if info else None,
                "page_or_paragraph_count": len(reader.pages),
            }
        if ext == "docx":
            import docx
            document = docx.Document(str(file_path))
            props = document.core_properties
            return {
                "author": props.author,
                "title": props.title,
                "created": str(props.created) if props.created else None,
                "modified": str(props.modified) if props.modified else None,
                "last_modified_by": props.last_modified_by,
                "page_or_paragraph_count": len(document.paragraphs),
            }
    except Exception:
        return None
    return None



#  BASIC LOG PARSING


_TIMESTAMP_PATTERNS = [
    (re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"), "%Y-%m-%d %H:%M:%S"),
    (re.compile(r"([A-Z][a-z]{2}\s+\d{1,2}\s\d{2}:\d{2}:\d{2})"), "%b %d %H:%M:%S"),
    (re.compile(r"(\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2})"), "%d/%b/%Y:%H:%M:%S"),
]
_LEVEL_PATTERN = re.compile(r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b", re.IGNORECASE)
_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAX_LOG_LINES = 50_000  # safety cap


def _parse_log_timestamp(line: str) -> Optional[datetime]:
    for pattern, fmt in _TIMESTAMP_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        raw = match.group(1).replace("T", " ")
        try:
            parsed = datetime.strptime(raw, fmt)
            if parsed.year == 1900:  # syslog has no year
                parsed = parsed.replace(year=datetime.now().year)
            return parsed
        except ValueError:
            continue
    return None


def parse_log_file(file_path: Path) -> list[dict]:
    """Nothing is silently dropped: lines with no recognizable
    timestamp/level/IP are still kept with raw_line preserved."""
    entries = []
    with open(file_path, "r", errors="replace") as f:
        for i, line in enumerate(f, start=1):
            if i > MAX_LOG_LINES:
                break
            line = line.rstrip("\n")
            if not line.strip():
                continue
            level_match = _LEVEL_PATTERN.search(line)
            ip_match = _IP_PATTERN.search(line)
            ts = _parse_log_timestamp(line)
            entries.append({
                "line_number": i,
                "timestamp": ts.isoformat() if ts else None,
                "level": level_match.group(1).upper() if level_match else None,
                "source_ip": ip_match.group(0) if ip_match else None,
                "raw_line": line[:1000],
            })
    return entries

# 7. TIMELINE EVENT GENERATION

def _parse_exif_dt(raw: str) -> Optional[datetime]:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def build_timeline(fs_metadata: dict, exif: Optional[dict], doc_metadata: Optional[dict],
                    log_entries: list[dict]) -> list[dict]:
    """Merges every timestamp source discovered above into one
    chronologically sorted timeline."""
    events = []

    if fs_metadata.get("created_time"):
        events.append({
            "timestamp": fs_metadata["created_time"],
            "event_type": "file_created",
            "description": f"File '{fs_metadata['file_name']}' created on disk.",
            "source": "filesystem_metadata",
            "confidence": "low",  # ctime unreliable as true creation time on Linux
        })
    if fs_metadata.get("modified_time"):
        events.append({
            "timestamp": fs_metadata["modified_time"],
            "event_type": "file_modified",
            "description": f"File '{fs_metadata['file_name']}' last modified.",
            "source": "filesystem_metadata",
            "confidence": "medium",
        })

    if exif and exif.get("has_exif") and exif.get("datetime_original"):
        dt = _parse_exif_dt(exif["datetime_original"])
        events.append({
            "timestamp": dt.isoformat() if dt else None,
            "event_type": "exif_capture",
            "description": "Image capture timestamp recorded in EXIF data.",
            "source": "exif",
            "confidence": "high",
        })

    if doc_metadata:
        if doc_metadata.get("created"):
            events.append({
                "timestamp": None,  # raw format varies by file type; kept as text below
                "event_type": "document_created",
                "description": f"Document created (raw: {doc_metadata['created']}).",
                "source": "document_metadata",
                "confidence": "medium",
            })
        if doc_metadata.get("modified"):
            events.append({
                "timestamp": None,
                "event_type": "document_modified",
                "description": f"Document last modified by "
                                f"{doc_metadata.get('last_modified_by') or 'unknown'} "
                                f"(raw: {doc_metadata['modified']}).",
                "source": "document_metadata",
                "confidence": "medium",
            })

    for entry in log_entries:
        if not entry.get("timestamp"):
            continue
        desc = "Log event"
        if entry.get("level"):
            desc += f" [{entry['level']}]"
        if entry.get("source_ip"):
            desc += f" from {entry['source_ip']}"
        events.append({
            "timestamp": entry["timestamp"],
            "event_type": "log_event",
            "description": f"{desc}: {entry['raw_line'][:200]}",
            "source": f"log_line_{entry['line_number']}",
            "confidence": "high",
        })

    events.sort(key=lambda e: (e["timestamp"] is None, e["timestamp"] or ""))
    return events


# ONE ENGINE, ONE CALL: process_evidence()

def process_evidence(file_path: str | Path, case_id: str = None, evidence_id: str = None) -> dict:
    """
    THE single entry point. Pass a file in, get the full forensic result
    back — hash, file identification, filesystem metadata, EXIF, document
    metadata, parsed log entries, and a unified timeline — all in one call.

    This is what Intern 1 should call from the Evidence Upload API right
    after a file is saved to disk, and what Intern 6 should persist as-is
    (the keys already line up with the Evidence / EvidenceHashes /
    TimelineEvents tables).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evidence file not found: {path}")

    errors = []

    # Hash first, always — the chain-of-custody anchor
    file_hash = compute_sha256(path)

    # Identify actual file type (don't trust the extension)
    identification = identify_file(path)

    # Filesystem-level metadata
    fs_metadata = extract_filesystem_metadata(path)

    exif_data = None
    doc_metadata = None
    log_entries = []

    # Type-specific extraction — each isolated so one failure doesn't
    # take down the whole pipeline
    try:
        if identification["category"] == "image":
            exif_data = extract_exif(path)
    except Exception as e:
        errors.append(f"EXIF extraction failed: {e}")

    try:
        if identification["category"] == "document":
            doc_metadata = extract_document_metadata(path, identification["detected_extension"])
    except Exception as e:
        errors.append(f"Document metadata extraction failed: {e}")

    try:
        if identification["category"] == "log":
            log_entries = parse_log_file(path)
    except Exception as e:
        errors.append(f"Log parsing failed: {e}")

    timeline_events = build_timeline(fs_metadata, exif_data, doc_metadata, log_entries)

    return {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "hash": file_hash,
        "file_identification": identification,
        "filesystem_metadata": fs_metadata,
        "exif": exif_data,
        "document_metadata": doc_metadata,
        "log_entries": log_entries,
        "timeline_events": timeline_events,
        "processing_errors": errors,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

# CLI entry point — run this file directly on any evidence file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python forensic_engine.py <path-to-evidence-file-or-folder>")
        sys.exit(1)

    target = Path(sys.argv[1])

    if not target.exists():
        print(f"Path not found: {target}")
        sys.exit(1)

    if target.is_dir():
        # Process every file in the folder, one engine call each, and
        # print one combined JSON array — so pointing this at a whole
        # evidence folder just works instead of erroring out.
        files = [p for p in sorted(target.iterdir()) if p.is_file()]
        if not files:
            print(f"No files found in folder: {target}")
            sys.exit(0)

        results = []
        for f in files:
            try:
                results.append(process_evidence(f))
            except Exception as e:
                results.append({"file_name": f.name, "error": str(e)})

        print(json.dumps(results, indent=2, default=str))
    else:
        result = process_evidence(target)
        print(json.dumps(result, indent=2, default=str))
