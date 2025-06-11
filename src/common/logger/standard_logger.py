import logging
import sys
from typing import Any, Optional, Dict
from datetime import datetime
import json

from .logger_interface import LoggerInterface, LogLevel


class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
        "BOLD": "\033[1m",  # Bold
        "DIM": "\033[2m",  # Dim
    }

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        use_colors: bool = True,
    ):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            # Add colors to log level
            level_color = self.COLORS.get(record.levelname, "")
            reset = self.COLORS["RESET"]
            bold = self.COLORS["BOLD"]
            dim = self.COLORS["DIM"]

            # Format timestamp
            timestamp = datetime.fromtimestamp(record.created).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )[:-3]

            # Format message with colors
            formatted_msg = (
                f"{dim}{timestamp}{reset} "
                f"{level_color}{bold}[{record.levelname:8}]{reset} "
                f"{bold}{record.name}{reset}: "
                f"{record.getMessage()}"
            )

            # Add context if available
            if hasattr(record, "context") and record.context:
                context_str = json.dumps(
                    record.context, indent=None, separators=(",", ":")
                )
                formatted_msg += f" {dim}| Context: {context_str}{reset}"

            return formatted_msg
        else:
            return super().format(record)


class StandardLogger(LoggerInterface):
    """Standard logger implementation using Python's logging library"""

    def __init__(
        self,
        name: str = "restful-api-testing",
        level: LogLevel = LogLevel.INFO,
        use_colors: bool = True,
        log_file: Optional[str] = None,
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}
        self.use_colors = use_colors

        # Clear any existing handlers
        self.logger.handlers.clear()
        self.logger.propagate = False

        # Set initial level
        self.set_level(level)

        # Setup console handler
        self._setup_console_handler()

        # Setup file handler if specified
        if log_file:
            self._setup_file_handler(log_file)

    def _setup_console_handler(self) -> None:
        """Setup colored console handler"""
        console_handler = logging.StreamHandler(sys.stdout)

        # Use colored formatter for console
        console_formatter = ColorFormatter(use_colors=self.use_colors)
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(console_handler)

    def _setup_file_handler(self, log_file: str) -> None:
        """Setup file handler without colors"""
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")

        # Use plain formatter for file
        file_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(file_handler)

    def _log_with_context(self, level: int, message: str, *args, **kwargs) -> None:
        """Internal method to log with context"""
        extra = kwargs.get("extra", {})
        if self.context:
            extra["context"] = self.context
        kwargs["extra"] = extra

        self.logger.log(level, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message"""
        self._log_with_context(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message"""
        self._log_with_context(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message"""
        self._log_with_context(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message"""
        self._log_with_context(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message"""
        self._log_with_context(logging.CRITICAL, message, *args, **kwargs)

    def log(self, level: LogLevel, message: str, *args, **kwargs) -> None:
        """Log message with specified level"""
        level_mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }

        self._log_with_context(level_mapping[level], message, *args, **kwargs)

    def set_level(self, level: LogLevel) -> None:
        """Set minimum log level"""
        level_mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }

        self.logger.setLevel(level_mapping[level])

    def add_context(self, **context: Any) -> None:
        """Add contextual information to logs"""
        self.context.update(context)

    def clear_context(self) -> None:
        """Clear contextual information"""
        self.context.clear()

    def add_handler(self, handler: logging.Handler) -> None:
        """Add custom handler"""
        self.logger.addHandler(handler)

    def remove_handler(self, handler: logging.Handler) -> None:
        """Remove handler"""
        self.logger.removeHandler(handler)
