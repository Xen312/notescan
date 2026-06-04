import logging
from pathlib import Path
from typing import Tuple
from src.models import BatchJob, PageData

logger = logging.getLogger("Note2PDF.InputLoader")

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

class InputLoader:
    @staticmethod
    def load(input_path: Path) -> Tuple[BatchJob, str]:
        """Analyzes the input path, creates a BatchJob, and returns the detected input type."""
        if not input_path.exists():
            raise FileNotFoundError(f"Input path target does not exist: {input_path}")

        output_name = input_path.stem
        job = BatchJob(input_path=input_path, output_name=output_name)

        if input_path.is_file():
            ext = input_path.suffix.lower()
            if ext == ".pdf":
                logger.info(f"Target identified as a PDF file: {input_path.name}")
                return job, "pdf"
            elif ext in SUPPORTED_IMAGE_EXTENSIONS:
                logger.info(f"Target identified as a single image file: {input_path.name}")
                job.pages.append(PageData(page_number=1, original_path=input_path))
                return job, "image"
            else:
                raise ValueError(f"Unsupported file format extension: {ext}")

        elif input_path.is_dir():
            logger.info(f"Target identified as a directory: {input_path}")
            images = sorted(
                [f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS],
                key=lambda x: x.name
            )
            
            if not images:
                raise ValueError(f"No compatible image files found inside target directory: {input_path}")

            for index, img_path in enumerate(images, start=1):
                job.pages.append(PageData(page_number=index, original_path=img_path))
                
            logger.info(f"Successfully loaded {len(job.pages)} image files from directory.")
            return job, "directory"

        else:
            raise ValueError("Input path target configuration is invalid.")