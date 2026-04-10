#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom logging handler for Tkinter GUI
"""
import logging
from queue import Queue


class TkinterHandler(logging.Handler):
    """Logging handler that sends log messages to a Tkinter queue for display
    """
    def __init__(self, log_queue: Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord):
        """Sends the formatted log message to the queue for GUI display
        """
        msg = self.format(record)
        self.log_queue.put(msg)
