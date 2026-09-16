"""Safe export helpers: CSV-injection-safe + XSS escaping."""

from __future__ import annotations

import csv
import html
import io

# Cells starting with these trigger formula evaluation in Excel/Sheets.
_DANGEROUS_FIRST = ("=", "+", "-", "@", "|", "%")


def safe_csv_cell(value: object) -> str:
    """Neutralize CSV formula injection.

    Prefixes a single quote when the (stripped) cell starts with
    ``= + - @ | %`` (incl. tab/CR-prefixed tricks, since we lstrip).
    Guarantees the returned cell never starts with ``=+-@``.
    """
    if value is None:
        return ""
    s = str(value)
    if s.lstrip(" \t\r\n").startswith(_DANGEROUS_FIRST):
        return "'" + s
    return s


def export_csv(rows: list[dict], columns: list[str]) -> str:
    """Export rows to CSV with every cell passed through :func:`safe_csv_cell`."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([safe_csv_cell(c) for c in columns])
    for r in rows:
        w.writerow([safe_csv_cell(r.get(c, "")) for c in columns])
    return buf.getvalue()


def html_escape(value: object) -> str:
    """Escape HTML special chars to prevent reflected-XSS in UI rendering."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)
