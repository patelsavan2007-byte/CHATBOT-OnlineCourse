"""Dynamic contact routing parsed from knowledge base.

Parses contact_directory.md at startup to map user inquiry topics
and programmes to the appropriate university department contact lines.
Contains zero hard-coded phone numbers or names.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app import config
from app.utils import logger


@dataclass
class ContactEntry:
    person: str
    phone: str
    prog_tag: Optional[str] = None  # e.g. "BCA/MCA" or "BBA/MBA"


class ContactDirectory:
    """Dynamically parses and provides official contact details."""

    def __init__(self, contact_path: Optional[Path] = None) -> None:
        if contact_path is None:
            # contact_directory.md is the consolidated contact file; the old
            # programs/contact.md is kept as a fallback for older checkouts.
            primary = config.KNOWLEDGE_BASE_DIR / "contact_directory.md"
            legacy = config.KNOWLEDGE_BASE_DIR / "programs" / "contact.md"
            contact_path = primary if primary.exists() else legacy
        self.contact_path = contact_path
        self._services: Dict[str, List[ContactEntry]] = {}
        self._load()

    def _load(self) -> None:
        if not self.contact_path.exists():
            logger.warning("Contact file not found at %s", self.contact_path)
            return

        try:
            content = self.contact_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to read contact file %s: %s", self.contact_path, exc)
            return

        lines = content.splitlines()
        current_service = ""

        service_aliases = {
            "admissions": "Admissions",
            "student services": "Student Services",
            "learning management system": "Learning Management System",
            "learning management system (lms)": "Learning Management System",
            "lms": "Learning Management System",
            "course mentor": "Course Mentor",
            "examinations": "Examinations",
            "exam": "Examinations",
            "accounts & payments": "Accounts & Payments",
            "accounts and payments": "Accounts & Payments",
            "general contact": "General Contact",
            "general": "General Contact",
        }

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check for Markdown heading: e.g. "## 1. Admissions" or "## General Contact"
            if line_str.startswith("## "):
                raw_sec = re.sub(r"^##\s*(?:\d+\.?\s*)?", "", line_str).strip()
                sec_lower = raw_sec.lower()
                matched_sec = service_aliases.get(sec_lower)
                if not matched_sec:
                    for alias, canonical in service_aliases.items():
                        if alias in sec_lower:
                            matched_sec = canonical
                            break
                current_service = matched_sec or raw_sec
                continue

            # Check for bullet format: "- **Mr. Darshit Patel** – Email: ... | Mobile: 7434055553"
            if line_str.startswith("- ") and current_service:
                # Extract person name (between ** ** if present)
                person_m = re.search(r"\*\*(.*?)\*\*", line_str)
                person = person_m.group(1).strip() if person_m else ""
                # Check for programme tag like (BCA/MCA)
                tag_m = re.search(r"\((BCA/MCA|BBA/MBA)\)", line_str)
                if tag_m and person and tag_m.group(0) not in person:
                    person = f"{person} {tag_m.group(0)}"
                # Extract phone/mobile
                phone_m = re.search(r"(?:Mobile|Phone|Helpline)[^:]*:\s*([+\d\s\-()]+)", line_str, re.I)
                phone_raw = phone_m.group(1) if phone_m else ""
                phone_digits = re.sub(r"\D", "", phone_raw)
                if phone_digits:
                    if not person:
                        person = current_service
                    self._add_entry(current_service, person, phone_digits)
                continue

            # Check for Pipe Table format: "| 1 | Service | Person | Email | Mobile |"
            if line_str.startswith("|"):
                cells = [c.strip() for c in line_str.split("|")[1:-1]]
                if not cells or cells[0] == "#" or "---" in cells[0]:
                    continue

                if len(cells) >= 5 and cells[0].isdigit():
                    raw_svc = cells[1].strip()
                    current_service = service_aliases.get(raw_svc.lower(), raw_svc)
                    person = cells[2].strip()
                    phone_digits = re.sub(r"\D", "", cells[4].strip())
                    self._add_entry(current_service, person, phone_digits)
                elif len(cells) >= 3 and current_service:
                    person = cells[0].strip()
                    phone_digits = re.sub(r"\D", "", cells[2].strip())
                    self._add_entry(current_service, person, phone_digits)

        logger.info(
            "Parsed contact directory with %d services from %s",
            len(self._services),
            self.contact_path.name,
        )

    def _add_entry(self, service: str, person: str, phone: str) -> None:
        if not phone:
            return
        prog_tag = None
        # Detect programme tag BEFORE stripping it from the display name
        if "BCA/MCA" in person or "(BCA/MCA)" in person:
            prog_tag = "BCA/MCA"
        elif "BBA/MBA" in person or "(BBA/MBA)" in person:
            prog_tag = "BBA/MBA"

        entry = ContactEntry(person=person, phone=phone, prog_tag=prog_tag)
        self._services.setdefault(service, []).append(entry)

    # ------------------------------------------------------------------
    # Step 5 fix: map topics to services using new vocabulary;
    #             keep programme tags in the output.
    # ------------------------------------------------------------------
    def get_contact_line(self, topic: str = "", programme: str = "") -> str:
        """Return a formatted contact line based on topic and programme.

        The (BCA/MCA) / (BBA/MBA) tags are preserved in the output so the user
        knows which person serves which programme.  If the programme is unknown
        every row is shown with its tag.
        """
        t_lower = (topic or "").lower()
        prog_lower = (programme or "").lower()

        # Map topic -> service dynamically via topic lexicon (R1 compliant)
        try:
            from app.lexicon import get_topic_contact_service
            service_name = get_topic_contact_service(t_lower) or "Admissions"
        except Exception:
            service_name = "Admissions"

        entries = self._services.get(service_name, [])
        if not entries:
            # Fall back to Admissions
            entries = self._services.get("Admissions", [])
            service_name = "Admissions"

        if not entries:
            return "For assistance, please visit https://charusat.online."

        # Filter by programme tag when programme is known AND service has tags
        has_tags = any(e.prog_tag for e in entries)
        if has_tags and prog_lower:
            if any(p in prog_lower for p in ("bca", "mca")):
                filtered = [e for e in entries if e.prog_tag == "BCA/MCA"]
                if filtered:
                    entries = filtered
            elif any(p in prog_lower for p in ("bba", "mba")):
                filtered = [e for e in entries if e.prog_tag == "BBA/MBA"]
                if filtered:
                    entries = filtered
            # else: show all with their tags

        # Step 5 fix: keep the programme tag in the display name
        formatted_contacts = []
        for e in entries:
            # Build display: "Name (BCA/MCA) (phone)" if tag exists, else "Name (phone)"
            if e.prog_tag and e.prog_tag not in e.person:
                formatted_contacts.append(f"{e.person} ({e.prog_tag}) ({e.phone})")
            else:
                # Tag may already be embedded in person string - show as-is plus phone
                formatted_contacts.append(f"{e.person} ({e.phone})")

        contacts_str = ", ".join(formatted_contacts)
        return f"For further assistance, please contact {service_name}: {contacts_str}."


# Singleton instance
_directory: Optional[ContactDirectory] = None


def get_contact_directory() -> ContactDirectory:
    global _directory
    if _directory is None:
        _directory = ContactDirectory()
    return _directory


def get_contact_line(topic: str = "", programme: str = "") -> str:
    """Convenience helper to retrieve formatted contact line."""
    return get_contact_directory().get_contact_line(topic=topic, programme=programme)
