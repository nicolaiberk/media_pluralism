"""Host-restricted GET helper for this project's data sources.

Exists so the permission allowlist can grant ONE auditable program instead of `curl -s *`,
which would permit requests to any host with any method. Enforcement lives here, in code
that is reviewable and version-controlled, rather than in a shell-pattern glob that later
flags can override.

Only GET. Only the hosts below. No request body, no custom method, no file writes.

Usage (from data_collection/outlet_urls/):
    python scripts/dnr_fetch.py "http://web.archive.org/cdx/search/cdx?url=20min.ch&limit=1"
    python scripts/dnr_fetch.py --head "https://bluenews.ch/"
    python scripts/dnr_fetch.py --timeout 60 "<url>"
"""
import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_HOSTS = {
    "web.archive.org",
    "archive.org",
    "index.commoncrawl.org",
    "data.commoncrawl.org",
    "www.wikidata.org",
    "wikidata.org",
    "reutersinstitute.politics.ox.ac.uk",
}


def check(url):
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https"):
        sys.exit(f"refused: scheme {p.scheme!r} not allowed")
    host = (p.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        sys.exit(f"refused: host {host!r} not in the allowlist.\n"
                 f"Allowed: {', '.join(sorted(ALLOWED_HOSTS))}\n"
                 f"If this project genuinely needs another host, add it to ALLOWED_HOSTS "
                 f"in this file so the change is reviewable in git.")
    return url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--head", action="store_true", help="HEAD request; print status and headers")
    ap.add_argument("--timeout", type=int, default=45)
    a = ap.parse_args()

    url = check(a.url)
    req = urllib.request.Request(url, method="HEAD" if a.head else "GET")
    req.add_header("User-Agent", "ETH-media-pluralism-registry/1.0 (academic research)")
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            if a.head:
                print(r.status)
                for k, v in r.headers.items():
                    print(f"{k}: {v}")
            else:
                sys.stdout.write(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}", file=sys.stderr)
        if a.head:
            print(e.code)
            for k, v in e.headers.items():
                print(f"{k}: {v}")
        sys.exit(1)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
