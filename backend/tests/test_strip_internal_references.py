import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.llm import strip_internal_references


def test_plain_words_survival():
    """Verify that plain words like contact, home, feedback, ciqa, and policy names survive."""
    s1 = "Please contact the academic coordinator for course queries."
    cleaned1 = strip_internal_references(s1)
    assert "contact" in cleaned1, f"Expected 'contact' in '{cleaned1}'"
    assert cleaned1 == s1

    s2 = "Online students can complete all coursework from home without commuting."
    cleaned2 = strip_internal_references(s2)
    assert "home" in cleaned2, f"Expected 'home' in '{cleaned2}'"
    assert cleaned2 == s2

    s3 = "Submit your feedback to the instructor after each lecture."
    cleaned3 = strip_internal_references(s3)
    assert "feedback" in cleaned3, f"Expected 'feedback' in '{cleaned3}'"
    assert cleaned3 == s3

    s4 = "According to the Fees Refund Policy, full tuition minus administrative charges is refundable."
    cleaned4 = strip_internal_references(s4)
    assert "Fees Refund Policy" in cleaned4, f"Expected 'Fees Refund Policy' in '{cleaned4}'"

    s5 = "The university CIQA committee monitors online program quality."
    cleaned5 = strip_internal_references(s5)
    assert "CIQA" in cleaned5, f"Expected 'CIQA' in '{cleaned5}'"


def test_real_file_name_removal():
    """Verify that real file paths and file names with extensions are cleanly removed."""
    s1 = "For more details check online_bba.md on page 3."
    cleaned1 = strip_internal_references(s1)
    assert "online_bba.md" not in cleaned1
    assert "page 3" not in cleaned1

    s2 = "The structure is detailed in PPR_Online MCA.pdf on page 12."
    cleaned2 = strip_internal_references(s2)
    assert "PPR_Online MCA.pdf" not in cleaned2
    assert "page 12" not in cleaned2

    s3 = "Source: programs/contact.md\nChunk ID: 12345\nScore: 0.95\nPlease reach out to student helpdesk."
    cleaned3 = strip_internal_references(s3)
    assert "Source:" not in cleaned3
    assert "programs/contact.md" not in cleaned3
    assert "Chunk ID:" not in cleaned3
    assert "Score:" not in cleaned3
    assert "Please reach out to student helpdesk." in cleaned3


def test_markdown_and_indentation_preservation():
    """Verify that markdown tables, nested lists, and lowercase lines are not broken."""
    nested_list = (
        "- Course Overview\n"
        "    - Core Modules\n"
        "        - Data Structures\n"
        "    - Elective Modules"
    )
    cleaned_list = strip_internal_references(nested_list)
    assert "    - Core Modules" in cleaned_list
    assert "        - Data Structures" in cleaned_list

    table = (
        "| Semester | Credits |\n"
        "|---|---|\n"
        "| Sem 1 | 24 |\n"
        "| Sem 2 | 26 |"
    )
    cleaned_table = strip_internal_references(table)
    assert "| Semester | Credits |" in cleaned_table
    assert "| Sem 1 | 24 |" in cleaned_table

    lowercase_line = "variableName is used in the module."
    cleaned_lower = strip_internal_references(lowercase_line)
    assert cleaned_lower.startswith("variableName"), "Lowercase line must NOT be force-capitalized"


if __name__ == "__main__":
    test_plain_words_survival()
    test_real_file_name_removal()
    test_markdown_and_indentation_preservation()
    print("ALL STRIP_INTERNAL_REFERENCES TESTS PASSED SUCCESSFULLY!")
