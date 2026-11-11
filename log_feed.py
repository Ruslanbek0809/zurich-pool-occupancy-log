#!/usr/bin/env python3
"""Fetch the Stadt Zürich "current pool guests" CSV feed once and append it to data/YYYY-MM.csv.

Standard library only. Usage:
    python3 log_feed.py [FEED_URL]
The feed URL can also be set with the environment variable FEED_URL (the argument wins).
Failures are recorded in data/failures.log; the script then exits 0 without writing rows.
"""

import csv
import io
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_URL = "https://data.stadt-zuerich.ch/dataset/ssd_spo_badi_aktuell/download/crowd-monitor.csv"
DATA_DIR = Path(__file__).resolve().parent / "data"
TIMEOUT_S = 30
ATTEMPTS = 3
PAUSE_S = 10
MAX_BYTES = 5_000_000


class FeedError(Exception):
    pass


def utc_stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url):
    """Return the response body, retrying on any error. Raises FeedError after the last attempt."""
    last = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pool-occupancy-logger/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                body = resp.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise FeedError(f"response larger than {MAX_BYTES} bytes")
            return body
        except Exception as exc:  # network errors, HTTP errors, timeouts
            last = f"{type(exc).__name__}: {exc}"
            if attempt < ATTEMPTS:
                time.sleep(PAUSE_S)
    raise FeedError(f"fetch failed after {ATTEMPTS} attempts: {last}")


def parse(body):
    """Return (header, rows). Raises FeedError on an empty or malformed CSV."""
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FeedError(f"not valid UTF-8: {exc}")
    if not text.strip():
        raise FeedError("empty response")
    if text.lstrip().startswith("<"):
        raise FeedError("response looks like HTML, not CSV")
    try:
        records = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise FeedError(f"CSV parse error: {exc}")
    records = [r for r in records if r]  # blank lines
    if not records:
        raise FeedError("empty response")
    header, rows = records[0], records[1:]
    if len(header) < 2 or any(not h.strip() for h in header) or len(set(header)) != len(header):
        raise FeedError(f"unusable header: {header!r}")
    if not rows:
        raise FeedError("header but no data rows")
    bad = [i for i, r in enumerate(rows, start=2) if len(r) != len(header)]
    if bad:
        raise FeedError(f"{len(bad)} rows with a field count different from the header (first at line {bad[0]})")
    return header, rows


def read_header(path):
    with path.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f), None)


def target_file(month, header):
    """First month file whose header matches; otherwise the first unused name (YYYY-MM.csv, YYYY-MM_schema2.csv, ...)."""
    n = 1
    while True:
        path = DATA_DIR / (f"{month}.csv" if n == 1 else f"{month}_schema{n}.csv")
        if not path.exists() or path.stat().st_size == 0:
            return path
        if read_header(path) == ["logged_at_utc"] + header:
            return path
        n += 1


def log_failure(reason):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{utc_stamp(datetime.now(timezone.utc))}\t{' '.join(reason.split())}\n"
    with (DATA_DIR / "failures.log").open("a", encoding="utf-8") as f:
        f.write(line)
    print(f"FAILED: {reason.strip()} (recorded in data/failures.log)")


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FEED_URL") or DEFAULT_URL
    try:
        body = fetch(url)
        fetched_at = datetime.now(timezone.utc)
        header, rows = parse(body)
    except FeedError as exc:
        log_failure(str(exc))
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = target_file(fetched_at.strftime("%Y-%m"), header)
    is_new = not path.exists() or path.stat().st_size == 0
    stamp = utc_stamp(fetched_at)

    # Build everything first, then append in a single write.
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    if is_new:
        writer.writerow(["logged_at_utc"] + header)
    for row in rows:
        writer.writerow([stamp] + row)
    with path.open("a", newline="", encoding="utf-8") as f:
        f.write(buf.getvalue())

    print(f"appended {len(rows)} rows to data/{path.name} (logged_at_utc {stamp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
