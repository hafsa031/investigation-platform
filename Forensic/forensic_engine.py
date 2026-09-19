"""
forensic_engine.py
JagSpire AI - Sprint 1
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# HASHING

CHUNK_SIZE = 65536  # 64KB, so large evidence files don't blow up memory


def compute_hashes(file_path: Path) -> dict:
    """SHA-256 and MD5 — the chain-of-custody anchors. Computed together
    in a single pass over the file, first, always, before anything else
    touches it. SHA-256 is primary/verification; MD5 is kept alongside
    for legacy tooling and cross-reference against malware hash
    databases, which still index heavily on MD5."""
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
            md5.update(chunk)
    computed_at = datetime.now(timezone.utc).isoformat()
    return {
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "computed_at": computed_at,
        # Row-shaped view too, for a schema like EvidenceHashes(algorithm, hash_value)
        "hashes": [
            {"algorithm": "SHA-256", "hash_value": sha256.hexdigest(), "computed_at": computed_at},
            {"algorithm": "MD5", "hash_value": md5.hexdigest(), "computed_at": computed_at},
        ],
    }


def compute_sha256(file_path: Path) -> dict:
    """Back-compat wrapper: old single-hash shape. Prefer compute_hashes()."""
    hashes = compute_hashes(file_path)
    return {
        "algorithm": "SHA-256",
        "hash_value": hashes["sha256"],
        "computed_at": hashes["computed_at"],
    }


def verify_integrity(file_path: Path, expected_hash: str, algorithm: str = "sha256") -> bool:
    """Re-hash and compare — used to detect tampering of stored evidence.
    algorithm: 'sha256' (default) or 'md5'."""
    hashes = compute_hashes(file_path)
    actual = hashes["md5"] if algorithm.lower() == "md5" else hashes["sha256"]
    return actual.lower() == expected_hash.lower()



# FILE TYPE IDENTIFICATION (magic bytes, no libmagic dependency)

_SIGNATURES = [
    # Images
    (b"\xff\xd8\xff", 0, "jpg", "image/jpeg", "image"),
    (b"\x89PNG\r\n\x1a\n", 0, "png", "image/png", "image"),
    (b"GIF87a", 0, "gif", "image/gif", "image"),
    (b"GIF89a", 0, "gif", "image/gif", "image"),
    (b"BM", 0, "bmp", "image/bmp", "image"),
    (b"II*\x00", 0, "tiff", "image/tiff", "image"),
    (b"MM\x00*", 0, "tiff", "image/tiff", "image"),
    (b"WEBP", 8, "webp", "image/webp", "image"),

    # Documents
    (b"%PDF-", 0, "pdf", "application/pdf", "document"),
    (b"{\\rtf1", 0, "rtf", "application/rtf", "document"),
    # Legacy OLE compound container — doc/xls/ppt all share this signature,
    # disambiguated by _disambiguate_ole() below.
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", 0, "ole", "application/x-ole-storage", "document"),

    # Archives / containers
    (b"PK\x03\x04", 0, "zip", "application/zip", "archive"),  # also docx/xlsx/pptx/jar/apk
    (b"PK\x05\x06", 0, "zip", "application/zip", "archive"),  # empty zip
    (b"Rar!\x1a\x07\x00", 0, "rar", "application/x-rar-compressed", "archive"),
    (b"7z\xbc\xaf\x27\x1c", 0, "7z", "application/x-7z-compressed", "archive"),
    (b"BZh", 0, "bz2", "application/x-bzip2", "archive"),
    (b"\xfd7zXZ\x00", 0, "xz", "application/x-xz", "archive"),
    (b"\x1f\x8b", 0, "gz", "application/gzip", "archive"),
    (b"ustar", 257, "tar", "application/x-tar", "archive"),

    # Executables / binaries — high forensic value (malware, dropped tools)
    (b"MZ", 0, "exe", "application/x-msdownload", "executable"),  # PE; refined by extract_pe_summary
    (b"\x7fELF", 0, "elf", "application/x-elf", "executable"),
    (b"\xca\xfe\xba\xbe", 0, "macho", "application/x-mach-binary", "executable"),  # fat/universal
    (b"\xfe\xed\xfa\xce", 0, "macho", "application/x-mach-binary", "executable"),
    (b"\xfe\xed\xfa\xcf", 0, "macho", "application/x-mach-binary", "executable"),
    (b"\xcf\xfa\xed\xfe", 0, "macho", "application/x-mach-binary", "executable"),

    # Databases — SQLite backs browser history, WhatsApp/Telegram, call logs
    (b"SQLite format 3\x00", 0, "sqlite", "application/vnd.sqlite3", "database"),

    # Audio
    (b"ID3", 0, "mp3", "audio/mpeg", "audio"),
    (b"\xff\xfb", 0, "mp3", "audio/mpeg", "audio"),
    (b"fLaC", 0, "flac", "audio/flac", "audio"),
    (b"OggS", 0, "ogg", "audio/ogg", "audio"),
    (b"WAVE", 8, "wav", "audio/wav", "audio"),

    # Video
    (b"\x00\x00\x00\x18ftyp", 4, "mp4", "video/mp4", "video"),
    (b"\x00\x00\x00\x20ftyp", 4, "mp4", "video/mp4", "video"),
    (b"ftyp", 4, "mp4", "video/mp4", "video"),  # generic ISO-BMFF catch-all (mp4/mov/m4a family)
    (b"AVI ", 8, "avi", "video/x-msvideo", "video"),
    (b"\x1a\x45\xdf\xa3", 0, "mkv", "video/x-matroska", "video"),  # also matches .webm
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


_OLE_STREAM_MARKERS = {
    "WordDocument": ("doc", "document"),
    "Workbook": ("xls", "document"),
    "Book": ("xls", "document"),
    "PowerPoint Document": ("ppt", "document"),
}


def _disambiguate_ole(file_path: Path, declared_ext: Optional[str]):
    """Legacy .doc/.xls/.ppt all share one OLE compound-file signature.
    If 'olefile' is installed, peek at the internal stream names for a
    confident answer; otherwise fall back to the declared extension
    (kept low-confidence downstream since a renamed file would fool it)."""
    try:
        import olefile
        if olefile.isOleFile(str(file_path)):
            with olefile.OleFileIO(str(file_path)) as ole:
                streams = {entry[0] for entry in ole.listdir()}
                for marker, result in _OLE_STREAM_MARKERS.items():
                    if marker in streams:
                        return result, "high"
    except ImportError:
        pass
    except Exception:
        pass

    if declared_ext in {"doc", "xls", "ppt"}:
        return (declared_ext, "document"), "low"
    return ("doc", "document"), "low"


_TEXT_FORMAT_META = {
    "json": ("application/json", "data"),
    "xml": ("application/xml", "data"),
    "html": ("text/html", "document"),
    "csv": ("text/csv", "data"),
    "eml": ("message/rfc822", "email"),
}


def _sniff_text_format(file_path: Path) -> Optional[str]:
    """Cheap content sniff for text-based formats that have no magic
    bytes at all. Only runs when no binary signature matched, so it never
    overrides a confident detection."""
    try:
        with open(file_path, "r", errors="ignore") as f:
            head = f.read(2048).lstrip()
    except Exception:
        return None
    if not head:
        return None

    if re.match(r"^(From|Return-Path|Received|Delivered-To|Message-ID):\s", head, re.I | re.M):
        return "eml"
    lower = head.lower()
    if lower.startswith("<!doctype html") or "<html" in lower[:200]:
        return "html"
    if head.startswith("<?xml") or (head.startswith("<") and re.match(r"^<[a-zA-Z]", head)):
        return "xml"
    if head[0] in "{[":
        try:
            json.loads(head)
            return "json"
        except json.JSONDecodeError:
            return "json"  # likely truncated by the 2KB read, still almost certainly JSON
    first_line = head.splitlines()[0] if head.splitlines() else ""
    if first_line.count(",") >= 1 and len(head.splitlines()) > 1:
        return "csv"
    return None


def identify_file(file_path: Path) -> dict:
    """Detect the ACTUAL file type from content and compare it against the
    declared extension. A mismatch (e.g. a .pdf renamed to .jpg) is a
    tamper/disguise signal worth flagging to the investigator."""
    declared_ext = file_path.suffix.lstrip(".").lower() or None

    with open(file_path, "rb") as f:
        header = f.read(512)  # covers the tar magic at offset 257

    detected_ext, mime_type, category = None, None, "unknown"
    for sig, offset, ext, mime, cat in _SIGNATURES:
        if header[offset:offset + len(sig)] == sig:
            detected_ext, mime_type, category = ext, mime, cat
            break

    ole_confidence = None

    if detected_ext == "zip":
        ooxml = _disambiguate_ooxml(file_path)
        if ooxml:
            detected_ext, category = ooxml
            mime_type = mimetypes.guess_type(f"f.{detected_ext}")[0] or mime_type

    elif detected_ext == "ole":
        (detected_ext, category), ole_confidence = _disambiguate_ole(file_path, declared_ext)
        mime_type = mimetypes.guess_type(f"f.{detected_ext}")[0] or mime_type

    if detected_ext is None:
        sniffed = _sniff_text_format(file_path)
        if sniffed:
            detected_ext = sniffed
            mime_type, category = _TEXT_FORMAT_META[sniffed]
        else:
            guessed_mime, _ = mimetypes.guess_type(str(file_path))
            mime_type = guessed_mime
            detected_ext = declared_ext
            if declared_ext in {"log", "txt"}:
                category = "log"

    is_mismatch = bool(
        declared_ext and detected_ext and declared_ext != detected_ext
        and not (declared_ext in {"jpg", "jpeg"} and detected_ext in {"jpg", "jpeg"})
    )

    result = {
        "declared_extension": declared_ext,
        "detected_extension": detected_ext,
        "mime_type": mime_type,
        "category": category,
        "is_mismatch": is_mismatch,
    }
    if ole_confidence:
        result["ole_subtype_confidence"] = ole_confidence
    return result


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

# PE EXECUTABLE SUMMARY (exe/dll/sys) — no external dependency

_PE_MACHINE_TYPES = {0x14c: "x86", 0x8664: "x64", 0x1c0: "ARM", 0xaa64: "ARM64"}


def extract_pe_summary(file_path: Path) -> Optional[dict]:
    """Minimal PE header parse for triage: machine type, EXE vs DLL vs
    driver, section count, and the linker-set compile timestamp (useful
    for timeline correlation, though it's attacker-controllable and
    should be flagged as such, not trusted outright)."""
    try:
        with open(file_path, "rb") as f:
            dos_header = f.read(64)
            if dos_header[:2] != b"MZ" or len(dos_header) < 64:
                return None
            e_lfanew = int.from_bytes(dos_header[0x3C:0x40], "little")
            f.seek(e_lfanew)
            pe_header = f.read(24)
    except (OSError, ValueError):
        return None

    if len(pe_header) < 24 or pe_header[:4] != b"PE\x00\x00":
        return {"is_valid_pe": False}

    machine = int.from_bytes(pe_header[4:6], "little")
    num_sections = int.from_bytes(pe_header[6:8], "little")
    timestamp = int.from_bytes(pe_header[8:12], "little")
    characteristics = int.from_bytes(pe_header[22:24], "little")

    try:
        compile_time = (
            datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            if 0 < timestamp < 2_147_483_647 else None
        )
    except (OSError, OverflowError, ValueError):
        compile_time = None

    return {
        "is_valid_pe": True,
        "machine": _PE_MACHINE_TYPES.get(machine, hex(machine)),
        "is_dll": bool(characteristics & 0x2000),
        "is_system_file": bool(characteristics & 0x1000),
        "num_sections": num_sections,
        "compile_timestamp_utc": compile_time,
        "compile_timestamp_note": "PE-header timestamp; commonly forged by malware, treat as low confidence",
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


# 8. FINDING CLASSIFICATION (Normal / Suspicious / Critical)

_SEVERITY_ORDER = {"Normal": 0, "Suspicious": 1, "Critical": 2}


def classify_finding(identification: dict, pe_summary: Optional[dict],
                      processing_errors: list[str]) -> dict:
    """Rule-based triage over what the pipeline already extracted — no
    new scanning, just reasoning about the signals already in hand.
    Each rule records its own reason, so an investigator sees exactly
    why a verdict was assigned rather than trusting a black-box label.
    Verdict only ever escalates (Normal -> Suspicious -> Critical),
    never downgrades, so the worst finding always wins."""
    level = "Normal"
    reasons: list[str] = []

    def escalate(new_level: str, reason: str) -> None:
        nonlocal level
        if _SEVERITY_ORDER[new_level] > _SEVERITY_ORDER[level]:
            level = new_level
        reasons.append(reason)

    # Extension/content mismatch is a classic disguise technique
    if identification.get("is_mismatch"):
        escalate(
            "Suspicious",
            f"Declared extension '.{identification.get('declared_extension')}' does not match "
            f"detected type '.{identification.get('detected_extension')}'.",
        )

    # Executable content is inherently higher-risk evidence
    if identification.get("category") == "executable":
        escalate("Suspicious", f"File is an executable ({identification.get('detected_extension')}).")

    if pe_summary:
        if pe_summary.get("is_valid_pe"):
            if identification.get("is_mismatch"):
                escalate("Critical", "Executable content disguised behind a non-executable extension.")
            if pe_summary.get("compile_timestamp_utc") is None:
                escalate("Suspicious", "PE compile timestamp missing/invalid — often indicates a forged header.")
        else:
            escalate("Suspicious", "File has an MZ header but is not a well-formed PE — possibly corrupted or crafted.")

    # Legacy OLE container whose real subtype (doc/xls/ppt) couldn't be confirmed
    if identification.get("ole_subtype_confidence") == "low":
        escalate("Suspicious", "Legacy Office container type could not be confirmed from internal stream names.")

    # Any extraction step failing is itself worth a human look
    if processing_errors:
        escalate("Suspicious", f"{len(processing_errors)} extraction step(s) failed during processing.")

    if not reasons:
        reasons.append("No indicators found in extracted metadata; file is consistent with its declared type.")

    return {"classification": level, "reasons": reasons}


# 9. STRUCTURED FORENSIC FINDINGS RECORD

def build_forensic_finding(evidence_id: Optional[str], case_id: Optional[str], file_hash: dict,
                            identification: dict, fs_metadata: dict, exif_data: Optional[dict],
                            doc_metadata: Optional[dict], pe_summary: Optional[dict],
                            timeline_events: list[dict], classification: dict) -> dict:
    """Packages the extraction results into the compact Forensic Findings
    record that goes to the backend for the dashboard — a summary meant
    for the Findings table/list, not the full raw extraction payload."""
    return {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "file_name": fs_metadata.get("file_name"),
        "file_size_bytes": fs_metadata.get("size_bytes"),
        "declared_extension": identification.get("declared_extension"),
        "detected_extension": identification.get("detected_extension"),
        "mime_type": identification.get("mime_type"),
        "category": identification.get("category"),
        "extension_mismatch": identification.get("is_mismatch", False),
        "sha256": file_hash.get("sha256"),
        "md5": file_hash.get("md5"),
        "created_time": fs_metadata.get("created_time"),
        "modified_time": fs_metadata.get("modified_time"),
        "has_exif": bool(exif_data and exif_data.get("has_exif")),
        "has_document_metadata": doc_metadata is not None,
        "is_executable": identification.get("category") == "executable",
        "pe_summary": pe_summary,
        "timeline_event_count": len(timeline_events),
        "classification": classification["classification"],
        "classification_reasons": classification["reasons"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# 10. BACKEND INTEGRATION — send findings to Intern 1's API

try:
    import requests
except ImportError:
    requests = None

# Override with the real deployed URL via env var once Intern 1's API is live,
# e.g. JAGSPIRE_BACKEND_URL=https://api.jagspire.internal
BACKEND_BASE_URL = os.environ.get("JAGSPIRE_BACKEND_URL", "http://localhost:8000")


def send_finding_to_backend(case_id: str, finding: dict, base_url: Optional[str] = None,
                             timeout: int = 10) -> dict:
    """POSTs one structured finding to POST /cases/{case_id}/findings so
    it shows up on the investigator dashboard. Never raises — network,
    HTTP, or missing-dependency failures come back as a status dict so
    the caller can log/retry instead of losing the rest of the pipeline
    run over a backend that isn't reachable yet."""
    if requests is None:
        return {"sent": False, "error": "The 'requests' package is not installed."}
    if not case_id:
        return {"sent": False, "error": "No case_id provided; cannot post finding."}

    url = f"{(base_url or BACKEND_BASE_URL).rstrip('/')}/cases/{case_id}/findings"
    try:
        resp = requests.post(url, json=finding, timeout=timeout)
        resp.raise_for_status()
        try:
            body = resp.json()
        except ValueError:
            body = None
        return {"sent": True, "status_code": resp.status_code, "response": body}
    except requests.exceptions.RequestException as e:
        return {"sent": False, "error": str(e)}


# ONE ENGINE, ONE CALL: process_evidence()

def process_evidence(file_path: str | Path, case_id: str = None, evidence_id: str = None,
                      send_to_backend: bool = False, backend_url: Optional[str] = None) -> dict:
    """
    THE single entry point. Pass a file in, get the full forensic result
    back — hashes, file identification, filesystem metadata, EXIF, document
    metadata, parsed log entries, a unified timeline, a Normal/Suspicious/
    Critical classification, and the structured Forensic Findings record
    built from all of it — all in one call.

    This is what Intern 1 should call from the Evidence Upload API right
    after a file is saved to disk, and what Intern 1's persistence layer
    should store as-is (the keys line up with the Evidence /
    EvidenceHashes / TimelineEvents tables; "forensic_finding" is the
    record meant for the Findings table).

    Pass send_to_backend=True (with case_id set) to also POST
    "forensic_finding" to /cases/{case_id}/findings so it lands on the
    dashboard immediately; the result of that call is returned under
    "backend_send_result" and a failed/skipped send never raises — it's
    reported in the result so the caller can retry.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evidence file not found: {path}")

    errors = []

    # Hash first, always — the chain-of-custody anchor
    file_hash = compute_hashes(path)

    # Identify actual file type (don't trust the extension)
    identification = identify_file(path)

    # Filesystem-level metadata
    fs_metadata = extract_filesystem_metadata(path)

    exif_data = None
    doc_metadata = None
    log_entries = []
    pe_summary = None

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

    try:
        if identification["category"] == "executable" and identification["detected_extension"] == "exe":
            pe_summary = extract_pe_summary(path)
    except Exception as e:
        errors.append(f"PE summary extraction failed: {e}")

    timeline_events = build_timeline(fs_metadata, exif_data, doc_metadata, log_entries)

    # Classify, then build the compact record the dashboard actually wants
    classification = classify_finding(identification, pe_summary, errors)
    finding = build_forensic_finding(
        evidence_id, case_id, file_hash, identification, fs_metadata,
        exif_data, doc_metadata, pe_summary, timeline_events, classification,
    )

    backend_send_result = None
    if send_to_backend:
        backend_send_result = send_finding_to_backend(case_id, finding, base_url=backend_url)

    return {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "hash": file_hash,
        "file_identification": identification,
        "filesystem_metadata": fs_metadata,
        "exif": exif_data,
        "document_metadata": doc_metadata,
        "pe_summary": pe_summary,
        "log_entries": log_entries,
        "timeline_events": timeline_events,
        "classification": classification,
        "forensic_finding": finding,
        "backend_send_result": backend_send_result,
        "processing_errors": errors,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

# CLI entry point — run this file directly on any evidence file

if __name__ == "__main__":
    args = sys.argv[1:]
    send_flag = "--send" in args
    if send_flag:
        args.remove("--send")

    if not args:
        print("Usage: python forensic_engine.py <path-to-evidence-file-or-folder> [case_id] [--send]")
        print("  --send  POST each finding to the backend (needs case_id and JAGSPIRE_BACKEND_URL)")
        sys.exit(1)

    target = Path(args[0])
    case_id = args[1] if len(args) > 1 else None

    if send_flag and not case_id:
        print("--send requires a case_id: python forensic_engine.py <path> <case_id> --send")
        sys.exit(1)

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
                results.append(process_evidence(f, case_id=case_id, send_to_backend=send_flag))
            except Exception as e:
                results.append({"file_name": f.name, "error": str(e)})

        print(json.dumps(results, indent=2, default=str))
    else:
        result = process_evidence(target, case_id=case_id, send_to_backend=send_flag)
        print(json.dumps(result, indent=2, default=str))
