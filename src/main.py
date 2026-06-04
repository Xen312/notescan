import sys
import argparse
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.utils import setup_logger, purge_directory
from src.input_loader import InputLoader
from src.pdf_converter import PDFConverter
from src.groq_backend import GroqBackend
from src.markdown_cleaner import MarkdownCleaner
from src.pdf_renderer import PDFRenderer

logger = logging.getLogger("Note2PDF.Main")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Local Handwritten Notes to Typed PDF Converter"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to file target (single image, PDF, or directory of images)"
    )
    parser.add_argument(
        "-o", "--output-name",
        type=str,
        default=None,
        help="Optional base name for output files"
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Do not clean up the temporary workspace directory after processing"
    )
    return parser.parse_args()

def execute_pipeline(input_path_str: str, custom_name: str = None, keep_temp: bool = False):
    try:
        Config.validate()
    except Exception as err:
        print(f"Configuration Error: {err}")
        sys.exit(1)

    global logger
    logger = setup_logger(Config.LOGS_DIR)
    logger.info("Initializing Note2PDF Converter pipeline...")
    logger.info(f"Target Vision Backend: GROQ ONLY ({Config.GROQ_VISION_MODEL})")

    input_path = Path(input_path_str)
    
    try:
        job, input_type = InputLoader.load(input_path)
    except Exception as e:
        logger.critical(f"Failed to load input targets: {e}")
        sys.exit(1)

    if custom_name:
        job.output_name = custom_name

    job_temp_dir = Config.TEMP_DIR / job.output_name
    job_temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Convert PDF pages to images (if input is a PDF)
    if input_type == "pdf":
        try:
            PDFConverter.extract_pages(job, job_temp_dir)
        except Exception as e:
            logger.critical(f"Failed to split input PDF document: {e}")
            sys.exit(1)

    # 2. Initialize the Groq backend
    try:
        groq_engine = GroqBackend()
    except Exception as e:
        logger.critical(f"Failed to load Groq Vision backend: {e}")
        sys.exit(1)

    compiled_markdown_pages = []

    # 3. Process each page sequentially
    for idx, page in enumerate(job.pages):
        logger.info(f"Processing page {page.page_number}/{len(job.pages)}: {page.original_path.name}")
        
        try:
            # Send image directly to the Groq vision backend
            logger.info("Executing Groq Vision transcription pass...")
            extracted_text = groq_engine.extract_markdown(page.original_path)
            page.extracted_markdown = extracted_text
            
            if not extracted_text.strip():
                logger.warning(f"No text detected on page {page.page_number}.")
                page.status = "success"
                continue

            # Step D: Markdown Sanitization and Cleaning
            final_markdown = MarkdownCleaner.run(extracted_text)
            page.cleaned_markdown = final_markdown
            page.status = "success"

            compiled_markdown_pages.append(
                f"<!-- START PAGE {page.page_number} -->\n{final_markdown}\n<!-- END PAGE {page.page_number} -->"
            )
            logger.info(f"Successfully processed page {page.page_number}.")

        except Exception as page_err:
            page.status = "failed"
            page.error_message = str(page_err)
            logger.error(f"Error processing page {page.page_number}: {page_err}")
            compiled_markdown_pages.append(
                f"\n\n## [Page {page.page_number} Processing Error]\n"
                f"*Could not process this page: {page_err}*\n\n"
            )
            continue

    if not compiled_markdown_pages:
        logger.critical("No content could be processed from the input target.")
        sys.exit(1)

    page_separator = "\n\n<div class=\"page-break\"></div>\n\n"
    full_markdown_document = page_separator.join(compiled_markdown_pages)

    # 4. Save Output Files
    output_markdown_path = Config.OUTPUT_DIR / f"{job.output_name}.md"
    output_pdf_path = Config.OUTPUT_DIR / f"{job.output_name}.pdf"

    try:
        output_markdown_path.write_text(full_markdown_document, encoding="utf-8")
        job.final_markdown_path = output_markdown_path
        logger.info(f"Saved compiled Markdown file to: {output_markdown_path}")
    except Exception as e:
        logger.error(f"Failed to save output Markdown file: {e}")

    # Render Markdown and LaTeX equations to PDF
    try:
        PDFRenderer.build(full_markdown_document, output_pdf_path, job_temp_dir)
        job.final_pdf_path = output_pdf_path
        logger.info(f"Saved compiled PDF document to: {output_pdf_path}")
    except Exception as e:
        logger.error(f"Failed to render output PDF file: {e}")
        sys.exit(1)

    if not keep_temp:
        logger.info("Cleaning up temporary workspace directory...")
        purge_directory(job_temp_dir)
        try:
            job_temp_dir.rmdir()
        except OSError:
            pass

    logger.info("Pipeline execution completed.")

if __name__ == "__main__":
    args = parse_arguments()
    execute_pipeline(
        input_path_str=args.input,
        custom_name=args.output_name,
        keep_temp=args.keep_temp
    )