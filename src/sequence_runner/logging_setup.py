import logging
from pathlib import Path

def setup_logging(level=logging.INFO, log_file: str | Path | None = None):
    """
    Thiết lập logging ra console, và (nếu chỉ định) ghi thêm ra file.
    Trả về logger để các module khác dùng chung.
    """
    fmt = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    logger = logging.getLogger()
    logger.setLevel(level)

    # Xóa handler cũ nếu có (tránh nhân đôi log khi gọi lại setup)
    if logger.hasHandlers():
        logger.handlers.clear()

    # ---- Console output ----
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(console_handler)

    # ---- Optional file output ----
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(file_handler)

        logger.info(f"Log file created at: {log_path.resolve()}")

    return logger
