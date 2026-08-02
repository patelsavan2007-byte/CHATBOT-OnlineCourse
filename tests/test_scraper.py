from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.scraper import extract_clean_markdown


def test_extract_clean_markdown_removes_noise_and_preserves_structure() -> None:
    html = """
    <html>
      <body>
        <header>Header content</header>
        <nav>Navigation</nav>
        <main>
          <h1>Program Overview</h1>
          <p>Welcome to CHARUSAT.</p>
          <ul>
            <li>Flexible learning</li>
            <li>Industry-oriented labs</li>
          </ul>
          <table>
            <tr><th>Course</th><th>Duration</th></tr>
            <tr><td>B.Tech</td><td>4 years</td></tr>
          </table>
          <script>var x = 1;</script>
        </main>
        <footer>Footer content</footer>
      </body>
    </html>
    """

    markdown = extract_clean_markdown(html, source_url="https://charusat.online/programs")

    assert "# Program Overview" in markdown
    assert "Welcome to CHARUSAT." in markdown
    assert "- Flexible learning" in markdown
    assert "| Course | Duration |" in markdown
    assert "Header content" not in markdown
    assert "Navigation" not in markdown
    assert "Footer content" not in markdown
    assert "var x = 1;" not in markdown
