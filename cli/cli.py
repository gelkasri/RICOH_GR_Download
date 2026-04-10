#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Launch the program from the command line
"""
from log_config import logger
from src.downloader import Downloader
from argparse import Namespace


class CLI:
    """
    Class for launching the download in command line mode, with the arguments passed during the call

    Arguments:

    Attributes:
        args: Arguments passed to the CLI
        downloader: Downloader object

    """
    def __init__(self, args: Namespace, downloader: Downloader):
        """Constructor for the CLI class
        Args:
            args: Command-line arguments (from argparse.Namespace).
            downloader: Downloader instance for photo transfers.
        """
        self.args: Namespace = args
        self.downloader: Downloader = downloader
        logger.debug(f"Launching the CLI with arguments {self.args}")