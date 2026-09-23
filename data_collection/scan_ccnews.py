#!/usr/bin/env python3
"""Minimal CC-NEWS scanner: list WARC files, scan them for registry domains.

Setup:
    pip install boto3 fastwarc

Usage:
    # 1. See what a month of CC-NEWS looks like
    python scan_ccnews.py list 2025/08

    # 2. Scan a single WARC file for matching domains (laptop-friendly test)
    python scan_ccnews.py scan crawl-data/CC-NEWS/2025/08/CC-NEWS-20250801022804-00284.warc.gz \
        --domains domains.txt --out matched/

`domains.txt`: one registered domain per line (e.g. `nzz.ch`, `20min.ch`,
`letemps.ch`). Subdomains match automatically (`epaper.nzz.ch` -> `nzz.ch`).

Output per scanned file:
    matched/<input-stem>.warc.gz   -- raw matched WARC records (immutable layer)
    matched/<input-stem>.csv       -- manifest: url, domain, warc date, offset
"""

import argparse
import csv
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from fastwarc.stream_io import GzipWriter
from fastwarc.warc import ArchiveIterator, WarcRecordType

BUCKET = "commoncrawl"
HTTPS_BASE = "https://data.commoncrawl.org/"  # CloudFront gateway, rate-limited


def s3_client():
    # Common Crawl is public: anonymous (unsigned) access, bucket lives in us-east-1
    return boto3.client(
        "s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED)
    )


def http_get(key: str):
    req = urllib.request.Request(
        HTTPS_BASE + key, headers={"User-Agent": "ccnews-scanner/0.1 (academic research)"}
    )
    return urllib.request.urlopen(req)


def open_stream(key: str):
    """Best-available byte stream for a CC key.

    Common Crawl S3 requires an authenticated AWS request (any account works);
    without credentials we fall back to the public HTTPS gateway (rate-limited,
    fine for tests — use AWS in us-east-1 for the real scan).
    """
    try:
        s3 = boto3.client("s3", region_name="us-east-1")
        return s3.get_object(Bucket=BUCKET, Key=key)["Body"]
    except (NoCredentialsError, ClientError):
        print("no usable AWS credentials, streaming via HTTPS gateway", file=sys.stderr)
        return http_get(key)


def cmd_list(month: str):
    """month = 'YYYY/MM' -> print WARC keys for that month (via warc.paths.gz)."""
    import gzip

    with gzip.open(http_get(f"crawl-data/CC-NEWS/{month}/warc.paths.gz"), "rt") as fh:
        keys = [line.strip() for line in fh if line.strip()]
    print("\n".join(keys))
    print(f"\n{len(keys)} files (~{len(keys):.0f} GiB compressed)", file=sys.stderr)


def load_domains(path: str) -> set[str]:
    domains = set()
    for line in Path(path).read_text().splitlines():
        d = line.strip().lower()
        if d and not d.startswith("#"):
            domains.add(d.removeprefix("www."))
    return domains


def match_domain(host: str, domains: set[str]) -> str | None:
    """Return the registry domain that `host` belongs to, else None.

    Walks up the host: 'epaper.nzz.ch' -> 'nzz.ch'. Suffix-walking is safe here
    because the registry contains registered domains, not public suffixes.
    """
    host = host.lower().removeprefix("www.")
    while host:
        if host in domains:
            return host
        if "." not in host:
            return None
        host = host.split(".", 1)[1]
    return None


def cmd_scan(key: str, domains_path: str, out_dir: str):
    domains = load_domains(domains_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(key).name.removesuffix(".warc.gz")

    body = open_stream(key)  # streaming, no full download

    n_records = 0
    n_matched = 0
    with open(out / f"{stem}.warc.gz", "wb") as warc_out, \
         open(out / f"{stem}.csv", "w", newline="") as csv_file:
        manifest = csv.writer(csv_file)
        manifest.writerow(["url", "domain", "warc_date", "source_file"])
        gz_out = GzipWriter(warc_out)

        # response records only (skips warcinfo/request); fastwarc decompresses
        # each gzip member just enough to read headers, so non-matches are cheap
        for record in ArchiveIterator(body, record_types=WarcRecordType.response):
            n_records += 1
            url = record.headers.get("WARC-Target-URI", "")
            host = urlsplit(url).hostname or ""
            dom = match_domain(host, domains)
            if dom is None:
                continue
            n_matched += 1
            record.write(gz_out)  # verbatim raw record -> our immutable raw layer
            manifest.writerow([url, dom, record.record_date, key])

    print(f"{key}: {n_matched}/{n_records} response records matched", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list WARC files for a month (YYYY/MM)")
    p_list.add_argument("month")

    p_scan = sub.add_parser("scan", help="scan one WARC file (S3 key)")
    p_scan.add_argument("key")
    p_scan.add_argument("--domains", required=True)
    p_scan.add_argument("--out", default="matched")

    args = p.parse_args()
    if args.cmd == "list":
        cmd_list(args.month)
    else:
        cmd_scan(args.key, args.domains, args.out)


if __name__ == "__main__":
    main()
