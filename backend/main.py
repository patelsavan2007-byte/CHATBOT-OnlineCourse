from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.chatbot import ChatbotApp


if __name__ == "__main__":
    app = ChatbotApp()
    app.run()
