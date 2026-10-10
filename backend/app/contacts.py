"""Dynamic contact routing parsed from knowledge base.

Parses programs/contact.md at startup to map user inquiry topics
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
        self.contact_path = contact_path or (config.KNOWLEDGE_BASE_DIR / "programs" / "contact.md")
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

        for line in lines:
            line_str = line.strip()
            if not line_str.startswith("|"):
                continue
            cells = [c.strip() for c in line_str.split("|")[1:-1]]
            if not cells or cells[0] == "#" or "---" in cells[0]:
                continue

            # Row format 1: | 1 | Service | Person | Email | Mobile |
            if len(cells) >= 5 and cells[0].isdigit():
                current_service = cells[1].strip()
                person = cells[2].strip()
                phone_digits = re.sub(r"\D", "", cells[4].strip())
                self._add_entry(current_service, person, phone_digits)
            # Row format 2: continuation row | Person | Email | Mobile |
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
        if "BCA/MCA" in person or "(BCA/MCA)" in person:
            prog_tag = "BCA/MCA"
        elif "BBA/MBA" in person or "(BBA/MBA)" in person:
            prog_tag = "BBA/MBA"

        entry = ContactEntry(person=person, phone=phone, prog_tag=prog_tag)
        self._services.setdefault(service, []).append(entry)

    def get_contact_line(self, topic: str = "", programme: str = "") -> str:
        """Return a single formatted contact line based on topic and programme."""
        t_lower = (topic or "").lower()
        prog_lower = (programme or "").lower()

        # Map topic to service
        if any(w in t_lower for w in ("fee", "fees", "payment", "receipt", "refund", "account", "tuition")):
            service_name = "Accounts & Payments"
        elif any(w in t_lower for w in ("exam", "examination", "marksheet", "result", "certificate", "grade", "grading", "evaluation", "score")):
            service_name = "Examinations"
        elif any(w in t_lower for w in ("lms", "login", "password", "technical", "portal")):
            service_name = "Learning Management System"
        elif any(w in t_lower for w in ("mentor", "counsel", "faculty", "counselling")):
            service_name = "Course Mentor"
        elif any(w in t_lower for w in ("student support", "support", "services", "id card")):
            service_name = "Student Services"
        elif any(w in t_lower for w in ("admission", "eligibility", "document", "apply", "enrol", "enrollment", "registration")):
            service_name = "Admissions"
        else:
            service_name = "Admissions"

        entries = self._services.get(service_name, [])
        if not entries:
            # Fall back to Admissions
            entries = self._services.get("Admissions", [])
            service_name = "Admissions"

        if not entries:
            return "For assistance, please visit https://charusat.online."

        # Filter LMS or Examinations entries by programme if applicable
        if service_name in ("Learning Management System", "Examinations") and prog_lower:
            if any(p in prog_lower for p in ("bca", "mca")):
                filtered = [e for e in entries if e.prog_tag == "BCA/MCA"]
                if filtered:
                    entries = filtered
            elif any(p in prog_lower for p in ("bba", "mba")):
                filtered = [e for e in entries if e.prog_tag == "BBA/MBA"]
                if filtered:
                    entries = filtered

        # Format one clean contact line with names and numbers
        formatted_contacts = []
        for e in entries:
            clean_name = re.sub(r"\s*\([^)]*\)", "", e.person).strip()
            formatted_contacts.append(f"{clean_name} ({e.phone})")

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
