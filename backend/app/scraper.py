from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from app.config import CRAWL_DELAY, KNOWLEDGE_BASE_DIR, SCRAPE_MAX_PAGES, SCRAPE_START_URL
from app.utils import logger, print_info, print_warning


class ScrapingError(RuntimeError):
    """Raised when a remote page cannot be fetched or parsed."""


CATEGORY_OVERRIDES = {
    "programs": "Programs",
}

PROGRAM_SLUG_OVERRIDES = {
    "bca": "online_bca",
    "bba": "online_bba",
    "mba": "online_mba",
    "mca": "online_mca",
}

# CSS class / id tokens that indicate non-content regions
SKIP_CLASS_TOKENS = frozenset([
    "nav", "menu", "breadcrumb", "sidebar", "advert", "banner", "cookie",
    "social", "footer", "header", "popup", "modal", "promo", "subscribe",
    "banner-form", "brochure", "site-mobile-menu", "npf", "loader",
    "cookie-consent", "whatsapp", "enquire",
])


def sanitize_filename(value: str, fallback: str = "page") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _normalize_url(url: str, base_url: str) -> Optional[str]:
    """Resolve *url* relative to *base_url*; return ``None`` for external or
    non-HTTP URLs.  Strips fragments, query strings, and deduplicates
    ``index.html`` → ``/``."""
    candidate = urljoin(base_url, url)
    parsed = urlparse(candidate)

    if parsed.scheme not in {"http", "https"}:
        return None

    base_netloc = urlparse(base_url).netloc.lower()
    if parsed.netloc.lower() != base_netloc:
        return None

    # Strip fragments and query strings
    normalized = parsed._replace(fragment="", query="").geturl()

    # Deduplicate index.html → base
    if normalized.endswith("/index.html"):
        normalized = normalized[: -len("index.html")]

    # Ensure trailing slash for directory-like URLs (no extension)
    path = urlparse(normalized).path
    if not path.split("/")[-1].count("."):
        if not normalized.endswith("/"):
            normalized += "/"

    return normalized


def extract_internal_links(html: str, base_url: str) -> List[str]:
    """Extract all unique internal links from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links: Set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        candidate = _normalize_url(href, base_url)
        if candidate:
            links.add(candidate)
    return sorted(links)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _heading_level(tag: Tag) -> int:
    return int(tag.name[1]) if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"} else 0


def _should_skip_tag(tag: Tag) -> bool:
    """Return True if this tag is structural chrome (nav, footer, etc.)."""
    # Always skip these element types
    if tag.name in {
        "script", "style", "noscript", "svg", "iframe", "form",
        "button", "input", "select", "textarea", "link", "meta",
    }:
        return True

    # Semantic tags for non-content regions
    if tag.name in {"header", "nav", "footer", "aside"}:
        return True

    # Inspect class and id attributes for skip tokens
    classes = tag.get("class", [])
    if isinstance(classes, list):
        attrs_str = " ".join(classes).lower()
    else:
        attrs_str = str(classes).lower()
    attrs_str += " " + str(tag.get("id", "")).lower()

    if any(token in attrs_str for token in SKIP_CLASS_TOKENS):
        return True

    return False


def _render_markdown(node: object) -> str:
    """Recursively render a BeautifulSoup node to Markdown."""
    if isinstance(node, NavigableString):
        text = _clean_text(str(node))
        return text if text else ""

    if not isinstance(node, Tag):
        return ""

    if _should_skip_tag(node):
        return ""

    # Headings
    if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = _heading_level(node)
        text = _clean_text(node.get_text(" ", strip=True))
        return f"{'#' * level} {text}" if text else ""

    # Paragraphs and blockquotes
    if node.name in {"p", "blockquote"}:
        text = _clean_text(node.get_text(" ", strip=True))
        prefix = "> " if node.name == "blockquote" else ""
        return f"{prefix}{text}" if text else ""

    # Lists
    if node.name in {"ul", "ol"}:
        items: List[str] = []
        for child in node.find_all("li", recursive=False):
            item_text = _clean_text(child.get_text(" ", strip=True))
            if item_text:
                items.append(f"- {item_text}")
        return "\n".join(items)

    # Tables
    if node.name == "table":
        rows = []
        for row in node.find_all("tr"):
            cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        markdown_rows = ["| " + " | ".join(row) + " |" for row in rows]
        separator = "| " + " | ".join(["-" * max(3, len(cell)) for cell in rows[0]]) + " |"
        markdown_rows.insert(1, separator)
        return "\n".join(markdown_rows)

    # Preformatted code
    if node.name == "pre":
        code = _clean_text(node.get_text("\n", strip=True))
        return f"```\n{code}\n```" if code else ""

    # Generic container — recurse into children
    pieces: List[str] = []
    for child in node.children:
        child_rendered = _render_markdown(child)
        if child_rendered:
            pieces.append(child_rendered)
    return "\n\n".join(piece for piece in pieces if piece)


def _page_category(path: str) -> str:
    """Derive a category from the URL path."""
    path = path.strip("/")
    if not path:
        return "Home"
    parts = [segment for segment in path.split("/") if segment]
    category = parts[0].lower()
    return CATEGORY_OVERRIDES.get(category, category.replace("-", " ").title())


def _build_output_path(url: str, output_dir: Path) -> Path:
    """Map a URL to a filesystem path inside output_dir."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path or path == "index.html":
        return output_dir / "home.md"

    parts = [segment for segment in path.split("/") if segment]
    last_part = parts[-1]
    if last_part.endswith(".html"):
        last_part = last_part[: -len(".html")]

    # Program pages → programs/ subdirectory with override names
    if len(parts) >= 2 and parts[0] == "programs":
        filename = PROGRAM_SLUG_OVERRIDES.get(last_part, sanitize_filename(last_part, fallback="program"))
        output_subdir = output_dir / "programs"
    else:
        filename = sanitize_filename(last_part, fallback="page")
        output_subdir = output_dir / Path(*parts[:-1]) if len(parts) > 1 else output_dir

    output_subdir.mkdir(parents=True, exist_ok=True)
    return output_subdir / f"{filename}.md"


def _build_frontmatter(title: str, url: str, category: str, last_scraped: str) -> str:
    return (
        f"Title: {title}\n"
        f"URL: {url}\n"
        f"Category: {category}\n"
        f"Last Scraped: {last_scraped}\n"
    )


def extract_clean_markdown(html: str, source_url: str) -> str:
    """Convert raw HTML to clean Markdown, stripping all chrome."""
    soup = BeautifulSoup(html, "html.parser")

    # Phase 1: Decompose unwanted elements entirely
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form",
                     "button", "input", "select", "textarea", "link", "meta"]):
        tag.decompose()

    # Phase 2: Decompose semantic non-content tags
    for tag in soup.find_all(["header", "nav", "footer", "aside"]):
        tag.decompose()

    # Phase 3: Decompose by class/id patterns
    def _has_skip_class(t: Tag) -> bool:
        classes = t.get("class", [])
        if isinstance(classes, list):
            attrs_str = " ".join(classes).lower()
        else:
            attrs_str = str(classes).lower()
        attrs_str += " " + str(t.get("id", "")).lower()
        return any(token in attrs_str for token in SKIP_CLASS_TOKENS)

    for tag in soup.find_all(_has_skip_class):
        tag.decompose()

    # Phase 4: Find the best content container
    container = soup.find("main") or soup.find("article") or soup.body or soup

    # If main contains sections, use all of them
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

    # Ensure the document starts with a heading
    title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else "Page"
    if title and not markdown.lstrip().startswith("#"):
        markdown = f"# {title}\n\n{markdown}"

    # Deduplicate paragraphs (exact-match blocks)
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
        blocks.append(block.strip())

    markdown = "\n\n".join(blocks)

    # Final cleanup: strip any remaining raw HTML tags
    markdown = re.sub(r"<[^>]+>", "", markdown)
    # Remove empty lines left by tag removal
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()

    return markdown


def _fetch_url(url: str) -> str:
    """Fetch a URL and return the raw HTML as a string."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CHARUSAT-RAG/2.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.text


def crawl_internal_pages(
    start_url: str = SCRAPE_START_URL,
    max_pages: int = SCRAPE_MAX_PAGES,
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """Crawl all internal pages starting from *start_url* and save each as
    a separate Markdown file.

    Returns the list of written file paths.
    """
    output_dir = output_dir or KNOWLEDGE_BASE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    visited: Set[str] = set()
    queue: List[str] = [start_url]
    discovered: Set[str] = {start_url}
    written_files: List[Path] = []

    print_info(f"Starting crawl from: {start_url}")
    print_info(f"Max pages: {max_pages}")

    while queue and len(written_files) < max_pages:
        url = queue.pop(0)
        normalized = _normalize_url(url, start_url)
        if not normalized or normalized in visited:
            continue
        visited.add(normalized)

        # Skip non-HTML resources
        path_lower = urlparse(normalized).path.lower()
        if any(path_lower.endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png",
                                                     ".gif", ".webp", ".css", ".js",
                                                     ".svg", ".ico", ".zip", ".doc",
                                                     ".docx", ".xlsx", ".mp4", ".mp3"]):
            print_warning(f"Skipping non-HTML: {normalized}")
            continue

        try:
            html = _fetch_url(normalized)
        except requests.RequestException as exc:
            print_warning(f"Skipping {normalized}: {exc}")
            continue

        # Extract links FIRST from the raw HTML (this is the key fix)
        new_links = extract_internal_links(html, normalized)
        for link in new_links:
            if link not in visited and link not in discovered:
                discovered.add(link)
                queue.append(link)

        # Clean the HTML into Markdown
        markdown_body = extract_clean_markdown(html, normalized)
        if not markdown_body.strip():
            print_warning(f"No content extracted from: {normalized}")
            continue

        # Build metadata
        soup_title = BeautifulSoup(html, "html.parser")
        page_title = _clean_text(soup_title.title.get_text(" ", strip=True)) if soup_title.title else "Page"
        category = _page_category(urlparse(normalized).path)
        last_scraped = datetime.now(timezone.utc).isoformat()
        frontmatter = _build_frontmatter(page_title, normalized, category, last_scraped)
        markdown = f"{frontmatter}\n{markdown_body}\n"

        # Write to file
        target_path = _build_output_path(normalized, output_dir)
        target_path.write_text(markdown, encoding="utf-8")
        written_files.append(target_path)
        print_info(f"  [{len(written_files)}] Saved: {target_path.relative_to(output_dir)}")
        logger.info("Saved scraped page %s to %s", normalized, target_path)

        # Polite delay between requests
        if queue:
            time.sleep(CRAWL_DELAY)

    # Print crawl summary
    print_info(f"\n{'=' * 50}")
    print_info(f"Pages Discovered: {len(discovered)}")
    print_info(f"Pages Crawled: {len(visited)}")
    print_info(f"Markdown Files Created: {len(written_files)}")
    print_info(f"{'=' * 50}")

    return written_files


def build_document_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path).encode("utf-8"))
        digest.update(str(path.stat().st_mtime).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


# Allow running the scraper directly for testing
if __name__ == "__main__":
    import sys
    ROOT = Path(__file__).resolve().parent.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    files = crawl_internal_pages()
    print_info(f"\nTotal files created: {len(files)}")
    for f in files:
        print_info(f"  - {f}")
