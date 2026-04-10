#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main project entry point
Handling command line arguments
"""

import argparse
import json
import sys
import urllib.error

from cli.cli import CLI
from gui.gui import GUI
from log_config import logger, set_log_level
from src.camera import RicohCamera
from src.downloader import Downloader


def parse_args():
    """Parse program arguments passed on the command line"""
    parser = argparse.ArgumentParser(
        prog="ricoh_gr_download.py",
        description="Photo transfer tool for Ricoh GR cameras, via Wi-Fi",
        epilog="""""")
    parser.add_argument("-d", "--dest-dir",
                        help="Choose destination directory", type=str)
    parser.add_argument("-j", "--jpg-only", action="store_true",
                        help="Transfer only JPG files")
    parser.add_argument("-r", "--raw-only", action="store_true",
                        help="Transfer only RAW files")
    parser.add_argument("-t", "--to-transfer", action="store_true",
                        help="Transfer only photos marked as 'To Transfer' on the camera")
    parser.add_argument("-D", "--dir-to-transfer", type=str,
                        help="Camera directory to transfer")
    parser.add_argument("-n", "--no-gui", action="store_true",
                        help="Disable the GUI and run the program from the command line")
    parser.add_argument("-l", "--log-level",
                        help="Level of logs displayed by the program",
                        type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    return parser.parse_args()


def main() -> int:
    """
    Main function of the program
    :return: 0 for success or 1 for error
    """
    args = parse_args()
    set_log_level(logger_to_set=logger, log_level=args.log_level)
    logger.debug(f"Starting the main program with arguments : {args}")
    c = None
    try:
        c = RicohCamera()
    except (urllib.error.URLError, json.JSONDecodeError):
        if args.no_gui:
            logger.error(f"Unable to connect to device, "
                         f"check the device's Wi-Fi network connection")
            sys.exit(1)
        else:
            logger.warning(f"Unable to connect to device, "
                         f"check the device's Wi-Fi network connection")
    downloader = Downloader(
        dest_dir=args.dest_dir,
        jpg_only=args.jpg_only,
        raw_only=args.raw_only,
        to_transfer_only=args.to_transfer,
        dir_to_transfer=args.dir_to_transfer,
        camera=c,
    )

    if args.no_gui:
        cli = CLI(args=args, downloader=downloader)
        if cli.downloader.download(): return 0
        else: return 1
    else:
        GUI(args=args, downloader=downloader)
    return 0


if __name__ == "__main__":
    sys.exit(main())
