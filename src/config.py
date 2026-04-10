#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for the project.
Contains the project's global constants and parameters.
"""
import logging
from pathlib import Path


# --- Ricoh API address and endpoints ---
API_HOST = "http://192.168.0.1/v1"                  # Warning : Fixed address of the device (do not modify)
API_PHOTO_LIST = "/photos"                          # Endpoint to list photos
API_PROPS = "/props"                                # Endpoint for device properties
API_INFO = "/info"
API_PING = "/ping"
API_TRANSFER = "/transfers"
API_SHUTDOWN = "/device/finish"

# --- File extensions ---
JPG_EXTENSION = "JPG"
RAW_EXTENSION = "DNG"
ALL_EXTENSIONS = "ALL"

# --- Default Settings ---
DEFAULT_DEST_DIR = Path.home() / "Pictures" / "GR_Downloads"    # Default destination folder

# --- Supported devices ---
# Only tested on Ricoh GR III
SUPPORTED_DEVICES = [
    'RICOH GR III',
    'RICOH GR IIIx'
]

# --- Timeouts and network settings ---
REQUEST_TIMEOUT = 5                                 # Timeout for HTTP requests (in seconds)

# --- Logging level (can be DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = logging.INFO

# --- GUI Settings
GUI_TITLE = "Transfert de photos depuis appareil Ricoh GR"
GUI_GEOM_X = 800
GUI_GEOM_Y = 750
GUI_GEOM = f"{GUI_GEOM_X}x{GUI_GEOM_Y}"             # format : "800x750"
GUI_RESIZABLE_H = True
GUI_RESIZABLE_W = True
GUI_COLOR_CONNECTION_OK = "green"
GUI_COLOR_CONNECTION_KO = "red"
GUI_QUEUE_MAJ_MS = 50