import logging
import os

logging.getLogger(__name__)


def setup_logging(level=None, log_file=None):
    """
    Set up logging configuration.

    Parameters:
    -----------
    level : str, optional
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_file : str, optional
        Path to log file

    Returns:
    --------
    logger : logging.Logger
        Root logger
    """

    # Handle None level case
    if level is None:
        level = "INFO"

    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    console = logging.StreamHandler()
    console.setLevel(numeric_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console.setFormatter(formatter)

    # Add console handler to root logger
    logger.addHandler(console)

    # Add file handler if log file specified
    if log_file:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name=None):
    """
    Get a logger instance.

    Parameters:
    -----------
    name : str, optional
        Logger name

    Returns:
    --------
    logger : logging.Logger
        Logger instance
    """
    # Set up root logger if not already configured
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        setup_logging()

    # Return named logger
    if name:
        return logging.getLogger(name)
    else:
        return root_logger
