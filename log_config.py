#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging configuration for the project
"""
import logging
import os
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from typing import Optional, List

from src.config import LOG_LEVEL


def setup_logger(
    name: str = __name__,
    log_file: Optional[str] = None,
    level: int = LOG_LEVEL,
    custom_handlers: Optional[List[logging.Handler]] = None
) -> logging.Logger:
    """
    Configures and returns a global logger for the project.

    Args:
        name: Name of logger (usually __name__).
        log_file: Path to a log file (optional). If None, logs to the console.
        level: Log level (ex: logging.DEBUG, logging.INFO).
        custom_handlers : Handlers for the GUI log area, or others if necessary

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger_to_setup = logging.getLogger(name)
    logger_to_setup.setLevel(level)
    formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s -- in <%(module)s>:%(funcName)s', datefmt='%H:%M:%S')

    # Handler for console (always active)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger_to_setup.addHandler(console_handler)

    # Handler for a file (if log_file is specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger_to_setup.addHandler(file_handler)

    if custom_handlers:
        for handler in custom_handlers:
            handler.setLevel(level)
            handler.setFormatter(formatter)
            logger_to_setup.addHandler(handler)

    return logger_to_setup

def set_log_level(logger_to_set: logging.Logger, log_level: str) -> None:
    """Modify the level of a logger, if log_level is not defined, we set the default value LOG_LEVEL

    Args:
        logger_to_set: logger whose level we want to modify
        log_level: log level as a string (e.g., "DEBUG", "INFO"). If None, uses LOG_LEVEL
    """
    option = {"DEBUG":DEBUG, "INFO":INFO, "WARNING":WARNING, "ERROR":ERROR, "CRITICAL":CRITICAL}
    if log_level is not None:
        logger_to_set.setLevel(option[log_level])
    else:
        logger_to_set.setLevel(LOG_LEVEL)
    set_log_formatter(logger_to_set)


def set_log_formatter(logger_to_set: logging.Logger) -> None:
    """Update the formatter for all handlers of a logger_to_set based on its level.
    In DEBUG mode, includes module and function name for more details.

    Args:
        logger_to_set: Logger whose level to modify
    """
    if logger_to_set.getEffectiveLevel() == logging.DEBUG:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s -- in <%(module)s>:%(funcName)s', datefmt='%H:%M:%S')
    else:
        formatter = logging.Formatter(
                 '%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    for handler in logger_to_set.handlers:
        handler.setFormatter(formatter)


# Global logger for the project (to import into other files)
logger = setup_logger(__name__)