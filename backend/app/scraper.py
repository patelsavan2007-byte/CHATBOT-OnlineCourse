from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from app.config import SCRAPE_MAX_PAGES, SCRAPE_START_URL
from app.utils import logger, print_info, print_warning


class ScrapingError(RuntimeError):
    """Raised when a remote page cannot be fetched or parsed."""


def sanitize_filename(value: str, fallback: str = "page") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def normalize_url(url: str, base_url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc and parsed.netloc.lower() != urlparse(base_url).netloc.lower():
        return None
    return urljoin(base_url, url)


def extract_internal_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: Set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        candidate = normalize_url(href, base_url)
        if candidate:
            links.add(candidate)
    return sorted(links)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _heading_level(tag: Tag) -> int:
    return int(tag.name[1]) if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"} else 0


def _should_skip_tag(tag: Tag) -> bool:
    if tag.name in {"script", "style", "noscript", "svg", "iframe", "form", "button", "input", "select", "textarea", "link"}:
        return True

    attrs = " ".join([str(tag.get("class", "")), str(tag.get("id", ""))]).lower()
    if any(token in attrs for token in ["nav", "menu", "breadcrumb", "sidebar", "advert", "banner", "cookie", "social", "footer", "header", "popup"]):
        return True

    if tag.name in {"header", "nav", "footer", "aside"}:
        return True

    return False


def _render_markdown(node: object) -> str:
    if isinstance(node, NavigableString):
        return _clean_text(str(node))

    if not isinstance(node, Tag):
        return ""

    if _should_skip_tag(node):
        return ""

    if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = _heading_level(node)
        text = _clean_text(node.get_text(" ", strip=True))
        return f"{'#' * level} {text}" if text else ""

    if node.name in {"p", "blockquote"}:
        text = _clean_text(node.get_text(" ", strip=True))
        prefix = "> " if node.name == "blockquote" else ""
        return f"{prefix}{text}" if text else ""

    if node.name in {"ul", "ol"}:
        items: List[str] = []
        for child in node.find_all("li", recursive=False):
            item_text = _clean_text(child.get_text(" ", strip=True))
            if item_text:
                items.append(f"- {item_text}")
        return "\n".join(items)

    if node.name == "table":
        rows = []
        for row in node.find_all("tr"):
            cells = [ _clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"]) ]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        markdown_rows = ["| " + " | ".join(row) + " |" for row in rows]
        separator = "| " + " | ".join(["-" * max(3, len(cell)) for cell in rows[0]]) + " |"
        markdown_rows.insert(1, separator)
        return "\n".join(markdown_rows)

    if node.name == "pre":
        code = _clean_text(node.get_text("\n", strip=True))
        return f"```\n{code}\n```" if code else ""

    pieces: List[str] = []
    for child in node.children:
        child_rendered = _render_markdown(child)
        if child_rendered:
            pieces.append(child_rendered)
    return "\n\n".join(piece for piece in pieces if piece)


def extract_clean_markdown(html: str, source_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form", "button", "input", "select", "textarea", "link"]):
        tag.decompose()

    for tag in soup.find_all(["header", "nav", "footer", "aside"]):
        tag.decompose()

    container = soup.find(["main", "article", "section"]) or soup.body or soup
    segments: List[str] = []
    for child in container.children:
        rendered = _render_markdown(child)
        if rendered:
            segments.append(rendered)

    markdown = "\n\n".join(segment for segment in segments if segment.strip())
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()

    if not markdown:
        title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else "Page"
        return f"# {title}\n\nNo meaningful content could be extracted."

    title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else "Page"
    if title and not markdown.lstrip().startswith("#"):
        markdown = f"# {title}\n\n{markdown}"

    blocks: List[str] = []
    seen: Set[str] = set()
    for block in re.split(r"\n{2,}", markdown):
        normalized = re.sub(r"\s+", " ", block.strip())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        blocks.append(normalized)

    result = "\n\n".join(blocks)
    if source_url:
        return f"<!-- Source: {source_url} -->\n\n{result}" if result else f"<!-- Source: {source_url} -->"
    return result


def _fetch_url(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CHARUSAT-RAG/1.0)"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.text


async def _fetch_with_crawl4ai(url: str) -> Optional[str]:
    try:
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency missing is expected in some environments
        logger.warning("Crawl4AI is not available; falling back to requests")
        return None

    try:
        async def _run() -> Optional[str]:
            crawler = AsyncWebCrawler()
            async with crawler:
                result = await crawler.arun(url=url)
                if hasattr(result, "markdown") and result.markdown:
                    return result.markdown
                if hasattr(result, "html") and result.html:
                    return result.html
                if hasattr(result, "content") and result.content:
                    return result.content
                return None

        return await _run()
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Crawl4AI request failed: %s", exc)
        return None


def crawl_internal_pages(start_url: str = SCRAPE_START_URL, max_pages: int = SCRAPE_MAX_PAGES, output_dir: Optional[Path] = None) -> List[Path]:
    output_dir = output_dir or Path(__file__).resolve().parent.parent / "knowledge_base" / "scraped"
    output_dir.mkdir(parents=True, exist_ok=True)

    visited: Set[str] = set()
    queue: List[str] = [start_url]
    written_files: List[Path] = []

    while queue and len(written_files) < max_pages:
        url = queue.pop(0)
        normalized = normalize_url(url, start_url)
        if not normalized or normalized in visited:
            continue
        visited.add(normalized)

        try:
            html = asyncio.run(_fetch_with_crawl4ai(normalized)) or _fetch_url(normalized)
        except requests.RequestException as exc:
            print_warning(f"Skipping {normalized}: {exc}")
            continue
        except ScrapingError as exc:
            print_warning(str(exc))
            continue

        markdown = extract_clean_markdown(html, normalized)
        if not markdown.strip():
            continue

        filename = _build_filename(normalized)
        target_path = output_dir / f"{filename}.md"
        target_path.write_text(markdown, encoding="utf-8")
        written_files.append(target_path)
        print_info(f"Scraped and saved: {target_path.name}")
        logger.info("Saved scraped page %s to %s", normalized, target_path)

        for link in extract_internal_links(html, normalized):
            if link not in visited and link not in queue:
                queue.append(link)

    return written_files


def _build_filename(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return sanitize_filename(parsed.netloc or "home", fallback="home")
    slug = sanitize_filename(path.replace("/", "-"), fallback="page")
    return f"{sanitize_filename(parsed.netloc or 'charusat', fallback='charusat')}-{slug}"


def build_document_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path).encode("utf-8"))
        digest.update(str(path.stat().st_mtime).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()
