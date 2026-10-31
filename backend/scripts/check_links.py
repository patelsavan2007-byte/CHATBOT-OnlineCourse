"""Check official and knowledge-base URLs and fail on non-200 responses.

Default scope:
  * every value in ``config.OFFICIAL_LINKS``
  * every ``URL:`` metadata line in knowledge_base/**/*.md
  * every URL on charusat.online, admission.charusat.ac.in, or
    charusat.lmexamsuite.com found in knowledge_base/**/*.md

Use ``--all`` to also check third-party bibliography/reference URLs.
"""

from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import config  # noqa: E402

KB_DIR = config.KNOWLEDGE_BASE_DIR
OFFICIAL_HOSTS = {
    "charusat.online",
    "admission.charusat.ac.in",
    "charusat.lmexamsuite.com",
}
URL_RE = re.compile(r'https?://[^\s<>"\'\]]+')
META_RE = re.compile(r"^\s*(?:URL|Source URL|Link):\s*(https?://\S+)", re.IGNORECASE)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def _clean(url: str) -> str:
    return url.rstrip(").,;:")


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def collect_urls(include_all: bool) -> list[tuple[str, str]]:
    found: dict[str, set[str]] = {}

    for key, url in config.OFFICIAL_LINKS.items():
        found.setdefault(url, set()).add(f"config.OFFICIAL_LINKS[{key!r}]")

    for path in sorted(KB_DIR.rglob("*.md")):
        rel = path.relative_to(BACKEND_DIR).as_posix()
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            meta = META_RE.match(line)
            if meta:
                url = _clean(meta.group(1))
                found.setdefault(url, set()).add(f"{rel}:{line_no} (metadata)")
            for match in URL_RE.findall(line):
                url = _clean(match)
                if include_all or _host(url) in OFFICIAL_HOSTS:
                    found.setdefault(url, set()).add(f"{rel}:{line_no}")

    return sorted(
        ((url, ", ".join(sorted(origins))) for url, origins in found.items()),
        key=lambda item: item[0],
    )


def check(url: str) -> tuple[str, int | str, str, str]:
    try:
        try:
            import certifi

            try:
                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=30,
                    allow_redirects=True,
                    verify=certifi.where(),
                )
            except Exception:
                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=30,
                    allow_redirects=True,
                    verify=True,
                )
        except Exception as exc:  # noqa: BLE001 - report the concrete request failure
            return url, "ERR", "", f"{type(exc).__name__}: {exc}"
        return url, response.status_code, response.url, response.headers.get("content-type", "")
    except Exception as exc:  # noqa: BLE001 - report the concrete request failure
        return url, "ERR", "", f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--all",
        action="store_true",
        help="also check third-party bibliography/reference URLs",
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    urls = collect_urls(include_all=args.all)
    scope = "ALL knowledge-base URLs" if args.all else "official URLs + metadata URLs"
    print(f"SCOPE: {scope}")
    print(f"URLS: {len(urls)}")
    print()

    failures: list[tuple[str, int | str, str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        jobs = {pool.submit(check, url): (url, origins) for url, origins in urls}
        results: dict[str, tuple[int | str, str, str]] = {}
        for future in as_completed(jobs):
            url, _origins = jobs[future]
            _url, status, final_url, detail = future.result()
            results[url] = (status, final_url, detail)

    for url, origins in urls:
        status, final_url, detail = results[url]
        if status != 200:
            failures.append((url, status, final_url, detail))
        print(f"{str(status):>4}  {url}")
        if final_url and final_url != url:
            print(f"      -> {final_url}")
        if status != 200:
            print(f"      {detail}")
        print(f"      refs: {origins}")

    print()
    print(f"RESULT: {'PASS' if not failures else 'FAIL'} ({len(urls) - len(failures)}/{len(urls)} HTTP 200)")
    if failures:
        print("FAILURES:")
        for url, status, _final, detail in failures:
            print(f"  {status}  {url}  {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
