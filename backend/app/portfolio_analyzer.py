"""Portfolio / GitHub analyzer for SkillForge AI.

Supports:
1. GitHub user profiles — via GitHub public REST API
2. GitHub repository URLs — single repo info
3. Static portfolio websites — via requests + BeautifulSoup
4. Modern SPA portfolios — returns low-content result (never invents)

Never invents skills. If insufficient evidence, returns empty skills
with a low-confidence message.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.gemini_client import get_gemini_client
from app.schemas import (
    ProfileSource,
    ProjectDetail,
    StudentProfile,
)
from app.utils import logger, print_info, print_warning

try:
    import requests as req_lib
    HAS_REQUESTS = True
except ImportError:
    req_lib = None
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    HAS_BS4 = False


GITHUB_API_BASE = "https://api.github.com"
REQUEST_TIMEOUT = 15
MAX_REPOS = 30


def _is_github_url(url: str) -> bool:
    """Check if URL is a GitHub URL."""
    parsed = urlparse(url)
    return parsed.hostname in ("github.com", "www.github.com")


def _parse_github_url(url: str) -> Dict[str, Optional[str]]:
    """Parse a GitHub URL into user/repo components."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    if len(path_parts) >= 2:
        return {"user": path_parts[0], "repo": path_parts[1]}
    elif len(path_parts) == 1:
        return {"user": path_parts[0], "repo": None}
    return {"user": None, "repo": None}


def _fetch_github_user_repos(username: str) -> List[Dict]:
    """Fetch public repositories for a GitHub user via API."""
    if not HAS_REQUESTS:
        return []

    url = f"{GITHUB_API_BASE}/users/{username}/repos"
    params = {
        "type": "owner",
        "sort": "updated",
        "per_page": MAX_REPOS,
    }

    try:
        resp = req_lib.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            logger.warning("GitHub user not found: %s", username)
        elif resp.status_code == 403:
            logger.warning("GitHub API rate limited")
        else:
            logger.warning("GitHub API returned %d for %s", resp.status_code, username)
    except Exception as exc:
        logger.error("GitHub API request failed: %s", exc)

    return []


def _fetch_github_repo(username: str, repo_name: str) -> Optional[Dict]:
    """Fetch a single GitHub repository."""
    if not HAS_REQUESTS:
        return None

    url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}"
    try:
        resp = req_lib.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.error("GitHub repo fetch failed: %s", exc)
    return None


def _fetch_repo_languages(username: str, repo_name: str) -> Dict[str, int]:
    """Fetch language breakdown for a repository."""
    if not HAS_REQUESTS:
        return {}

    url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/languages"
    try:
        resp = req_lib.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch languages for %s/%s: %s", username, repo_name, exc)
    return {}


def _fetch_readme(username: str, repo_name: str) -> str:
    """Fetch README content for a repository."""
    if not HAS_REQUESTS:
        return ""

    url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/readme"
    headers = {"Accept": "application/vnd.github.raw+json"}
    try:
        resp = req_lib.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            text = resp.text
            # Limit README to first 2000 chars
            return text[:2000] if text else ""
    except Exception as exc:
        logger.warning("Failed to fetch README for %s/%s: %s", username, repo_name, exc)
    return ""


def analyze_github_profile(username: str, repo_name: Optional[str] = None) -> StudentProfile:
    """Analyze a GitHub profile or single repository.

    Parameters
    ----------
    username : str
        GitHub username.
    repo_name : str, optional
        Specific repository name. If None, analyzes all user repos.

    Returns
    -------
    StudentProfile
        Extracted profile from GitHub data.
    """
    all_technologies: set = set()
    projects: List[ProjectDetail] = []
    all_languages: set = set()

    if repo_name:
        # Single repo analysis
        repo = _fetch_github_repo(username, repo_name)
        if repo:
            langs = _fetch_repo_languages(username, repo_name)
            readme = _fetch_readme(username, repo_name)
            all_languages.update(langs.keys())

            tech_list = list(langs.keys())
            topics = repo.get("topics", [])
            all_technologies.update(tech_list)
            all_technologies.update(topics)

            projects.append(ProjectDetail(
                name=repo.get("name", ""),
                description=repo.get("description", "") or "",
                technologies=tech_list + topics,
                url=repo.get("html_url", ""),
                source="github",
            ))

            print_info(f"[GitHub] Analyzed repo: {username}/{repo_name}")
        else:
            return StudentProfile(
                source=ProfileSource.PORTFOLIO,
                confidence="low",
                extraction_notes=f"Could not access GitHub repository: {username}/{repo_name}",
            )
    else:
        # Full user profile analysis
        repos = _fetch_github_user_repos(username)
        if not repos:
            return StudentProfile(
                source=ProfileSource.PORTFOLIO,
                confidence="low",
                extraction_notes=f"No public repositories found for GitHub user: {username}",
            )

        for repo in repos:
            if repo.get("fork", False):
                continue  # Skip forks

            name = repo.get("name", "")
            description = repo.get("description", "") or ""
            language = repo.get("language", "")
            topics = repo.get("topics", [])
            html_url = repo.get("html_url", "")

            tech = []
            if language:
                tech.append(language)
                all_languages.add(language)
            tech.extend(topics)
            all_technologies.update(tech)

            projects.append(ProjectDetail(
                name=name,
                description=description,
                technologies=tech,
                url=html_url,
                source="github",
            ))

        # Fetch languages for top repos (limit API calls)
        for project in projects[:10]:
            if project.url:
                repo_parts = project.url.rstrip("/").split("/")
                if len(repo_parts) >= 2:
                    langs = _fetch_repo_languages(repo_parts[-2], repo_parts[-1])
                    all_languages.update(langs.keys())
                    all_technologies.update(langs.keys())

        print_info(f"[GitHub] Analyzed {len(projects)} repos for {username}")

    # Use Gemini to enhance the profile analysis if available
    profile = _enhance_with_gemini(
        projects=projects,
        technologies=list(all_technologies),
        languages=list(all_languages),
        source_url=f"https://github.com/{username}",
    )

    if profile:
        return profile

    # Fallback: return raw extracted data
    return StudentProfile(
        skills=sorted(all_technologies),
        technologies=sorted(all_languages),
        projects=projects,
        links=[f"https://github.com/{username}"],
        source=ProfileSource.PORTFOLIO,
        confidence="medium",
        summary=f"GitHub profile with {len(projects)} public repositories. "
                f"Primary technologies: {', '.join(sorted(all_languages)[:8])}.",
    )


def analyze_portfolio_website(url: str) -> StudentProfile:
    """Analyze a portfolio website via HTTP scraping.

    Uses requests + BeautifulSoup for static content extraction.
    If the site is a modern SPA with minimal static HTML, returns
    a low-content result instead of inventing information.
    """
    if not HAS_REQUESTS or not HAS_BS4:
        return StudentProfile(
            source=ProfileSource.PORTFOLIO,
            confidence="low",
            extraction_notes="Missing dependencies (requests/beautifulsoup4) for portfolio analysis.",
        )

    try:
        resp = req_lib.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "SkillForge-AI-Analyzer/1.0"},
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Failed to fetch portfolio: %s", exc)
        return StudentProfile(
            source=ProfileSource.PORTFOLIO,
            confidence="low",
            extraction_notes=f"Could not access portfolio URL: {exc}",
        )

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    if len(text) < 100:
        return StudentProfile(
            source=ProfileSource.PORTFOLIO,
            confidence="low",
            extraction_notes="Portfolio returned minimal static content. "
                           "It may be a JavaScript-rendered SPA. "
                           "Consider providing a GitHub URL instead.",
        )

    # Extract links
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("http") and "github.com" in href:
            links.append(href)
        elif href.startswith("http") and any(
            kw in href.lower() for kw in ["linkedin", "portfolio", "project"]
        ):
            links.append(href)

    # Use Gemini for intelligent extraction
    client = get_gemini_client()
    if client.is_available:
        prompt = f"""Analyze this portfolio website content and extract structured information.

CRITICAL: ONLY extract what is EXPLICITLY stated. DO NOT invent or assume anything.
If very little information is available, return empty lists.

Portfolio URL: {url}
Portfolio Content:
---
{text[:6000]}
---

Return JSON:
{{
  "skills": ["only skills explicitly mentioned"],
  "technologies": ["only technologies explicitly mentioned"],
  "projects": [
    {{
      "name": "project name",
      "description": "description",
      "technologies": ["tech used"],
      "url": "project URL if available",
      "source": "portfolio"
    }}
  ],
  "achievements": ["achievements mentioned"],
  "strengths": ["strengths demonstrated"],
  "summary": "brief summary of what the portfolio shows",
  "confidence": "high/medium/low based on content quality"
}}"""

        result = client.generate_json(prompt, temperature=0.1)
        if result:
            try:
                profile = StudentProfile.model_validate(result)
                profile.source = ProfileSource.PORTFOLIO
                profile.links = links[:10]
                print_info(f"[Portfolio] Extracted {len(profile.skills)} skills from {url}")
                return profile
            except Exception as exc:
                logger.warning("Portfolio Gemini validation failed: %s", exc)

    # Fallback: basic extraction
    return StudentProfile(
        links=links[:10],
        source=ProfileSource.PORTFOLIO,
        confidence="low",
        extraction_notes="Portfolio content was extracted but could not be analyzed in detail.",
        summary=text[:300],
    )


def _enhance_with_gemini(
    projects: List[ProjectDetail],
    technologies: List[str],
    languages: List[str],
    source_url: str,
) -> Optional[StudentProfile]:
    """Use Gemini to enhance raw GitHub data into a richer profile."""
    client = get_gemini_client()
    if not client.is_available:
        return None

    projects_text = "\n".join(
        f"- {p.name}: {p.description} (Tech: {', '.join(p.technologies)})"
        for p in projects[:15]
    )

    prompt = f"""Analyze this GitHub profile data and create a structured student profile.

CRITICAL: ONLY derive skills and strengths from the ACTUAL projects and technologies listed below.
DO NOT invent skills or technologies not evident from the data.

GitHub URL: {source_url}
Technologies detected: {', '.join(technologies[:30])}
Languages: {', '.join(languages[:15])}
Projects:
{projects_text}

Return JSON:
{{
  "skills": ["skills evident from the projects and technologies"],
  "technologies": ["all technologies used across projects"],
  "strengths": ["demonstrated strengths based on project patterns"],
  "summary": "2-3 sentence summary of this developer's profile",
  "confidence": "high/medium/low"
}}"""

    result = client.generate_json(prompt, temperature=0.1)
    if result:
        try:
            # Merge Gemini analysis with raw project data
            profile = StudentProfile(
                skills=result.get("skills", []),
                technologies=result.get("technologies", technologies),
                projects=projects,
                strengths=result.get("strengths", []),
                links=[source_url],
                source=ProfileSource.PORTFOLIO,
                confidence=result.get("confidence", "medium"),
                summary=result.get("summary", ""),
            )
            return profile
        except Exception as exc:
            logger.warning("Gemini GitHub enhancement failed: %s", exc)
    return None


def analyze_portfolio(url: str) -> StudentProfile:
    """Main entry point: analyze a portfolio or GitHub URL.

    Automatically detects whether the URL is a GitHub profile,
    GitHub repo, or general portfolio website.
    """
    if not url or not url.strip():
        return StudentProfile(
            source=ProfileSource.PORTFOLIO,
            confidence="low",
            extraction_notes="No portfolio URL provided.",
        )

    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    if _is_github_url(url):
        parts = _parse_github_url(url)
        if parts["user"]:
            return analyze_github_profile(parts["user"], parts.get("repo"))
        return StudentProfile(
            source=ProfileSource.PORTFOLIO,
            confidence="low",
            extraction_notes="Could not parse GitHub URL.",
        )

    return analyze_portfolio_website(url)
