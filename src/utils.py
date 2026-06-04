import sys
import shutil
import logging
from pathlib import Path

def setup_logger(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Configures a double-output logger to output to both the console and a file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("Note2PDF")
    logger.setLevel(level)
    
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_dir / "processing.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def purge_directory(target_dir: Path) -> None:
    """Safely cleans up intermediate and temporary files inside the target directory."""
    if not target_dir.exists():
        return
    for item in target_dir.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception:
            pass