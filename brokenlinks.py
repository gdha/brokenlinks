#!/usr/bin/env python3
"""
brokenlinks.py - Detect broken links in a given URL.

Usage:
    python brokenlinks.py <url> [--depth <n>] [--timeout <seconds>]

Options:
    --depth     Maximum crawl depth (default: 2, use 0 for single page only)
    --timeout   Request timeout in seconds (default: 10)
    --same-domain  Only follow links within the same domain (default: True)
"""

import argparse
import sys
import urllib.parse
from collections import deque

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit(
        "Required packages are missing. Install them with:\n"
        "  pip install requests beautifulsoup4"
    )


def is_same_domain(base_url: str, url: str) -> bool:
    base_netloc = urllib.parse.urlparse(base_url).netloc
    url_netloc = urllib.parse.urlparse(url).netloc
    return base_netloc == url_netloc


def normalize_url(base: str, href: str) -> str | None:
    """Resolve a (possibly relative) href against base and return an absolute http/https URL."""
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
        return None
    parsed = urllib.parse.urlparse(href)
    if parsed.scheme in ("", "http", "https"):
        full = urllib.parse.urljoin(base, href)
        # Drop fragment
        full = urllib.parse.urldefrag(full)[0]
        if urllib.parse.urlparse(full).scheme in ("http", "https"):
            return full
    return None


def is_broken(status: int | None) -> bool:
    """Return True if the URL should be considered broken."""
    return status is None or status >= 400


def check_url(url: str, session: requests.Session, timeout: int) -> tuple[int | None, str]:
    """Return (status_code, error_message). status_code is None on connection error."""
    try:
        response = session.head(url, timeout=timeout, allow_redirects=True)
        # Some servers don't support HEAD; fall back to GET with stream
        if response.status_code in (405, 501):
            with session.get(url, timeout=timeout, allow_redirects=True, stream=True) as response:
                return response.status_code, ""
        return response.status_code, ""
    except requests.exceptions.ConnectionError as exc:
        return None, f"Connection error: {exc}"
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except requests.exceptions.TooManyRedirects:
        return None, "Too many redirects"
    except requests.exceptions.RequestException as exc:
        return None, str(exc)


def get_links(url: str, session: requests.Session, timeout: int) -> list[str]:
    """Fetch page at *url* and extract all href links."""
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        if "text/html" not in response.headers.get("Content-Type", ""):
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for tag in soup.find_all("a", href=True):
            normalized = normalize_url(url, tag["href"])
            if normalized:
                links.append(normalized)
        return links
    except requests.exceptions.RequestException:
        return []


def crawl(start_url: str, max_depth: int, timeout: int, same_domain: bool) -> dict:
    """
    BFS crawl starting from *start_url*.

    Returns a dict mapping each discovered URL to its check result:
        {url: {"status": int|None, "error": str, "referrer": str}}
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "brokenlinks-checker/1.0"})

    visited: set[str] = set()
    results: dict[str, dict] = {}
    # Queue items: (url, depth, referrer)
    queue: deque[tuple[str, int, str]] = deque([(start_url, 0, "")])

    while queue:
        url, depth, referrer = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        status, error = check_url(url, session, timeout)
        results[url] = {"status": status, "error": error, "referrer": referrer}

        broken = is_broken(status)
        print(
            f"{'BROKEN' if broken else 'OK':6s}  [{status if status is not None else 'ERR'}]  {url}"
            + (f"  ({error})" if error else "")
        )

        # Only crawl deeper into same-domain HTML pages that are OK
        if depth < max_depth and not broken:
            if not same_domain or is_same_domain(start_url, url):
                for link in get_links(url, session, timeout):
                    if link not in visited:
                        if not same_domain or is_same_domain(start_url, link):
                            queue.append((link, depth + 1, url))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect broken links in a given URL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="Starting URL to check")
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        metavar="N",
        help="Maximum crawl depth (default: 2; 0 = single page only)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        metavar="SEC",
        help="Request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--no-same-domain",
        action="store_true",
        help="Also follow links to external domains",
    )
    args = parser.parse_args()

    if not args.url.startswith(("http://", "https://")):
        args.url = "https://" + args.url

    print(f"Checking links starting at: {args.url}")
    print(f"Max depth: {args.depth}  |  Timeout: {args.timeout}s\n")

    results = crawl(
        start_url=args.url,
        max_depth=args.depth,
        timeout=args.timeout,
        same_domain=not args.no_same_domain,
    )

    broken = {url: info for url, info in results.items() if is_broken(info["status"])}

    print(f"\n{'='*60}")
    print(f"Total links checked : {len(results)}")
    print(f"Broken links found  : {len(broken)}")

    if broken:
        print("\nBroken links summary:")
        for url, info in broken.items():
            status_str = str(info["status"]) if info["status"] is not None else "ERR"
            ref_str = f"  (found on: {info['referrer']})" if info["referrer"] else ""
            print(f"  [{status_str}] {url}{ref_str}")
        sys.exit(1)


if __name__ == "__main__":
    main()
