from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class PageData:
    """Stores intermediate extracted Markdown and processing states for a single page."""
    page_number: int
    original_path: Path
    extracted_markdown: str = ""
    cleaned_markdown: str = ""
    status: str = "pending"  # pending, success, failed
    error_message: Optional[str] = None

@dataclass
class BatchJob:
    """Maintains the full execution context for a note conversion job."""
    input_path: Path
    output_name: str
    pages: List[PageData] = field(default_factory=list)
    final_markdown_path: Optional[Path] = None
    final_pdf_path: Optional[Path] = None