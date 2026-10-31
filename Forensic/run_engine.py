"""Run the forensic engine on one file and write a clean, readable report.

Usage:
    py run_engine.py "<file path>"            # prints report to screen
    py run_engine.py "<file path>" report.txt # also saves it to a text file
"""
import sys
from forensic_engine.service import EvidenceProcessingService

# Tags that are binary blobs or vendor-specific noise; not useful in a report.
SKIP_TAGS = {"MakerNote", "UserComment", "PrintImageMatching", "ComponentsConfiguration", "ExifOffset", "ExifInteroperabilityOffset", "GPSInfo"}

# Grouping of EXIF tags for the report.
GROUPS = [
    ("Camera", ["Make", "Model", "BodySerialNumber", "LensModel", "LensSerialNumber", "Software"]),
    ("Capture", ["DateTimeOriginal", "DateTimeDigitized", "DateTime", "ExposureTime", "FNumber",
                 "ISOSpeedRatings", "FocalLength", "Flash", "WhiteBalance", "ExposureMode"]),
    ("Image", ["ExifImageWidth", "ExifImageHeight", "Orientation", "XResolution", "YResolution",
               "ResolutionUnit", "ColorSpace"]),
]


def clean(value):
    """Turn raw EXIF values into short, readable text."""
    if isinstance(value, bytes):
        return "<binary data>"
    text = str(value).strip()
    if len(text) > 80:
        return text[:77] + "..."
    return text


def build_report(result, file_path):
    lines = []
    add = lines.append
    add("=" * 60)
    add("EVIDENCE PROCESSING REPORT")
    add("=" * 60)
    add(f"File name      : {result.filesystem_metadata.file_name}")
    add(f"File size      : {result.filesystem_metadata.size_bytes:,} bytes")
    add(f"Detected type  : {result.file_identification.category.value}")
    add(f"SHA-256        : {result.hash.hash_value}")
    add("")

    add("-" * 60)
    add("EXIF METADATA")
    add("-" * 60)
    exif = result.exif
    if exif is None or not exif.has_exif:
        add("No EXIF metadata found in this file.")
        add("(Messaging apps such as WhatsApp usually remove EXIF data.)")
    else:
        raw = {k: v for k, v in (exif.raw_tags or {}).items() if k not in SKIP_TAGS}
        used = set()
        for title, tags in GROUPS:
            present = [t for t in tags if t in raw]
            if not present:
                continue
            add(f"\n[{title}]")
            for tag in present:
                add(f"  {tag:<22}: {clean(raw[tag])}")
                used.add(tag)

        others = sorted(t for t in raw if t not in used)
        if others:
            add("\n[Other]")
            for tag in others:
                add(f"  {tag:<22}: {clean(raw[tag])}")

        add("\n[GPS]")
        if exif.gps_latitude is not None and exif.gps_longitude is not None:
            add(f"  Latitude              : {exif.gps_latitude:.6f}")
            add(f"  Longitude             : {exif.gps_longitude:.6f}")
        else:
            add("  No GPS coordinates recorded.")

    add("")
    add("-" * 60)
    add("PROCESSING ERRORS")
    add("-" * 60)
    if result.processing_errors:
        for err in result.processing_errors:
            add(f"  - {err}")
    else:
        add("  None.")
    add("")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: py run_engine.py <file> [output.txt]")
        sys.exit(1)

    file_path = sys.argv[1]
    result = EvidenceProcessingService().process(file_path)
    report = build_report(result, file_path)
    print(report)

    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to: {sys.argv[2]}")


if __name__ == "__main__":
    main()
