import logging
from pathlib import Path
import fitz  # PyMuPDF
from src.models import BatchJob, PageData

logger = logging.getLogger("Note2PDF.PDFConverter")

class PDFConverter:
    @staticmethod
    def extract_pages(job: BatchJob, temp_dir: Path, dpi: int = 200) -> None:
        """Splits a PDF file into high-DPI page images and outputs them to the temporary workspace directory."""
        pdf_path = job.input_path
        logger.info(f"Opening document: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"PyMuPDF failed to load target PDF: {e}")
            raise RuntimeError(f"Could not open PDF document: {e}")

        try:
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                page = doc.load_page(page_idx)
                
                zoom = dpi / 72.0
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                
                output_image_path = temp_dir / f"page_{page_num:03d}.png"
                pix.save(str(output_image_path))
                
                job.pages.append(PageData(
                    page_number=page_num,
                    original_path=output_image_path
                ))
                logger.debug(f"Rendered page {page_num} to: {output_image_path.name}")
                
            logger.info(f"Extracted {len(job.pages)} pages from PDF.")
        finally:
            doc.close()