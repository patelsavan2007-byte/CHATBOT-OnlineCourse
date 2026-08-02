# Rebuild RAG Knowledge Base: Full-Site Crawler + Per-Page Markdown + Metadata-Filtered Retrieval

## Problem Statement

The current scraper only produces a single `home.md` because:
1. **`crawl4ai` returns pre-rendered markdown** — when the `_fetch_with_crawl4ai` path succeeds, it returns markdown text instead of raw HTML. The `extract_internal_links()` function then finds **zero `<a>` tags** in that markdown string, so the crawl queue stays empty after the first page.
2. **Nav/footer content is not stripped** — `crawl4ai`'s markdown output includes navigation links, footers, and duplicate sections, resulting in a noisy 40KB `home.md`.
3. The chatbot therefore only answers from homepage content and cannot differentiate between programs.

## Proposed Changes

### Scraper — [scraper.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/scraper.py)

#### [MODIFY] [scraper.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/scraper.py)

**Root cause fix**: Always fetch raw HTML with `requests` for link extraction, then optionally use crawl4ai for enhanced content. Key changes:

1. **Always use `requests` to get raw HTML first** — this guarantees `extract_internal_links()` works correctly on every page. Remove `crawl4ai` dependency entirely (it complicates things and its markdown output bypasses our cleaning).
2. **Fix URL normalization** — ensure `https://charusat.online` (no trailing slash) is handled correctly. Normalize start URL to always include trailing slash. Also handle `index.html` → `/` deduplication.
3. **Improve content cleaning** — the current `extract_clean_markdown` gets confused by crawl4ai markdown. Since we'll always have raw HTML, the BeautifulSoup cleaning pipeline will work correctly:
   - Decompose `<header>`, `<nav>`, `<footer>`, `<aside>`, `<script>`, `<style>`, etc.
   - Also decompose elements by class/id containing: `nav`, `menu`, `footer`, `header`, `sidebar`, `cookie`, `social`, `modal`, `popup`, `banner-form`, `brochure`, `subscribe`
   - Find content in `<main>` → `<article>` → `<section>` → `<body>`
4. **Robust link discovery** — extract links from both `<a href>` tags and detect common patterns like `programs/*.html` pages.
5. **Add polite crawl delay** (0.5s between requests) to avoid overwhelming the server.
6. **Better filename generation** — use the `PROGRAM_SLUG_OVERRIDES` map already present, and generate clean filenames from URL paths for other pages.

---

### Ingestion — [ingestion.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/ingestion.py)

#### [MODIFY] [ingestion.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/ingestion.py)

1. **Exclude unwanted files** — add explicit skip list for `deep-research-report.md` and `CHARUSAT_Online_Programs_Knowledge_Base.txt`. Also skip any `.txt` files from indexing.
2. **Each markdown file → separate LangChain Document** — already implemented correctly, no change needed.
3. **Chunk parameters** — already set to `chunk_size=600`, `chunk_overlap=100` (correct).
4. **Chunk metadata** — already includes `source_filename`, `page_title`, `url`, `category`, `chunk_id`, and `program_name`. No change needed.

---

### Config — [config.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/config.py)

#### [MODIFY] [config.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/config.py)

1. Fix `SCRAPE_START_URL` to use trailing slash: `https://charusat.online/`
2. Add `CRAWL_DELAY = 0.5` constant.

---

### Retriever — [retriever.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/retriever.py)

#### [MODIFY] [retriever.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/retriever.py)

No major changes needed. The existing metadata-filtered retrieval using `program_name` is already well-designed. The real fix is that the program pages will now actually exist as separate documents in the vector store.

---

### Chatbot — [chatbot.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/chatbot.py)

#### [MODIFY] [chatbot.py](file:///c:/AProjects/CHATB/CHATBOT-OnlineCourse/backend/app/chatbot.py)

1. Add `Pages Discovered` count to the rebuild summary output.
2. Ensure the summary matches the exact format requested.

---

## Summary of Root Cause & Fix

| Issue | Cause | Fix |
|-------|-------|-----|
| Only `home.md` generated | `crawl4ai` returns markdown, not HTML → `extract_internal_links()` finds zero `<a>` tags → queue stays empty | Always use `requests.get()` for raw HTML; remove `crawl4ai` dependency |
| Nav/footer in output | `crawl4ai` markdown bypasses BeautifulSoup cleaning | Raw HTML goes through full BS4 cleaning pipeline |
| Programs not indexed | Crawl stops after page 1 | Queue populates correctly from raw HTML links |
| Mixed program results | Only one document exists | Separate docs per page + existing metadata filter works |

## Files NOT to Index

These files will be explicitly excluded from the knowledge base and vector store:
- `deep-research-report.md`
- `CHARUSAT_Online_Programs_Knowledge_Base.txt`

## Verification Plan

### Automated Verification
After modifying the code, run the full pipeline:
```bash
cd c:\AProjects\CHATB\CHATBOT-OnlineCourse\backend
python -m app.scraper
```

Verify output:
- **Multiple markdown files** exist in `knowledge_base/` (not just `home.md`)
- `knowledge_base/programs/` directory contains `online_bca.md`, `online_bba.md`, `online_mba.md`, `online_mca.md`
- Each file begins with the correct metadata header (Title, URL, Category, Last Scraped)
- Nav/footer content is NOT present in the markdown files

### Pipeline Summary Output
The script will print:
```
Pages Discovered: <count>
Pages Crawled: <count>
Markdown Files Created: <count>
Chunks Generated: <count>
Embeddings Generated: <count>
ChromaDB Rebuilt Successfully
```

### Manual Spot-Check
- Inspect `online_bca.md` to confirm it contains BCA-specific content (eligibility, curriculum, fee structure)
- Inspect `online_mba.md` to confirm it contains MBA-specific content and NOT BCA content
