import logging
from rich.logging import RichHandler


def get_logger(name: str = "routewise") -> logging.Logger:
    """Create a configured logger with Rich output."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_level = logging.getLevelName(__import__('os').environ.get('LOG_LEVEL', 'INFO'))

    logger.setLevel(log_level)
    handler = RichHandler(rich_tracebacks=True, show_time=True, show_level=True, show_path=False)
    fmt = logging.Formatter("%(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.propagate = False
    return logger