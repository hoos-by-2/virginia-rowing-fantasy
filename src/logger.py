import logging
from typing import Optional

def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger instance.
    
    :param name: Name of the logger. If None, the root logger is used.
    :param level: Logging level. Default is logging.INFO.
    :return: Configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():  # Avoid adding multiple handlers if already configured
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
    