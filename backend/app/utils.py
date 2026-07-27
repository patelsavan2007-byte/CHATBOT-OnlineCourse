from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("charusat_rag")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RichHandler(console=console, rich_tracebacks=True)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()


def print_section(title: str) -> None:
    console.print(f"[bold cyan]{title}[/bold cyan]")


def print_info(message: str) -> None:
    console.print(f"[green]{message}[/green]")


def print_warning(message: str) -> None:
    console.print(f"[yellow]{message}[/yellow]")


def print_error(message: str) -> None:
    console.print(f"[red]{message}[/red]")


class Timer:
    def __enter__(self) -> "Timer":
        self.started_at = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.elapsed_seconds = time.perf_counter() - self.started_at


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Could not decode file: {path.name}") from exc
