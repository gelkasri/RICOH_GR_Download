#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera connection management
TODO: factoriser les appels à l'api avec une seule fonction
"""
import datetime
import json
import logging
import os
import urllib
from urllib import request, error
from typing import Optional

from log_config import logger
from src.config import (SUPPORTED_DEVICES, REQUEST_TIMEOUT,
                        API_HOST, API_PROPS, API_PHOTO_LIST, API_INFO, API_PING, API_TRANSFER, API_SHUTDOWN)


class RicohCamera:
    """
    Class for interacting with a Ricoh GR device
    Attributes:
        timeout (int): Request timeout in seconds.
        _connected (bool): Whether the camera is connected.
        model (str): Camera model (e.g., "RICOH GR III").
        name (str): Camera device name.
        battery (int): Battery level percentage.
        photos (List[Dict]): List of photos on the device.

    """

    def __init__(self):
        self.timeout = REQUEST_TIMEOUT
        self._connected = False
        self.model = None
        self.name = None
        self.battery = -1
        self.photos = []
        self._test_connection()
        self._set_device_info()
        self.set_photo_list()

    def _test_connection(self) -> bool:
        """Test connection to the Ricoh GR device via api ping.
        Modify self._connected attribute

        Returns:
            True on success, False on failure

        """
        self._connected = False
        req = urllib.request.Request(API_HOST + API_PING)
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            data = json.loads(resp.read())
            if data['errCode'] != 200:
                logger.error(f"API error code: {data['errCode']}, message: {data['errMsg']}")
                return False
            else:
                dt = datetime.datetime.strptime(data['datetime'], "%Y-%m-%dT%H:%M:%S")
                logger.debug(f"Connection ok: {dt}")
                self._connected = True
                return True
        except urllib.error.URLError as e:
            if logger.getEffectiveLevel() == logging.DEBUG:
                logger.warning(f"Unable to connect to device: {e}")
            else:
                logger.warning(f"Unable to connect to device, check the device's Wi-Fi network connection")
            raise e
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response when connecting to device : {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error connecting to device : {e}")
            raise e

    def _set_device_info(self) -> bool:
        """Retrieves the device model (private method) via API.
        Modify the attributes:
            - self.model (str): Device model.
            - self.battery (int): Battery level.
            - self.name (str): Device name.
            - self._connected (bool): True if connection ok, False otherwise

        Returns:
            True on success, False on failure
        Raises:
            ValueError if the device is not supported
        """
        self._connected = False
        req = urllib.request.Request(API_HOST + API_PROPS)
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            props = json.loads(resp.read())
            if props['errCode'] != 200:
                logger.error(f"API error code: {props['errCode']}, message: {props['errMsg']}")
                return False
            else:
                self.model = props['model']
                if self.model not in SUPPORTED_DEVICES:
                    logger.error(f"Device {self.model} is not supported or unknown")
                    raise ValueError(f"Unsupported device: {self.model}")
                self.battery = props['battery']
                self.name = props['bdName']
                self._connected = True
                logger.info(f"Model : {self.get_model()}, Battery : {self.get_battery()}%, "
                            f"Device name : {self.get_name()}")
                if self.battery < 50:
                    logger.warning(f"Battery is low: {self.battery}%")
                return True

        except urllib.error.URLError as e:
            logger.error(f"Connection error : {e.reason}")
            return False
        except json.JSONDecodeError:
            logger.error("Invalid JSON response.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error : {e}")
            return False

    def set_photo_list(self) -> bool:
        """Retrieves the list of photos present on the device
        Modify attributes:
            - self.photos with the list of photos
            - self.connected True if connection OK, False otherwise
        Returns:
            True on success, False on failure
        """
        self._connected = False
        self.photos.clear()
        resp = urllib.request.Request(API_HOST + API_PHOTO_LIST)
        try:
            resp = urllib.request.urlopen(resp, timeout=self.timeout)
            data = json.loads(resp.read())
            if data['errCode'] != 200:
                logger.error(f"API error code: {data['errCode']}, message: {data['errMsg']}")
                return False
            else:
                for directory in data['dirs']:
                    for filename in directory['files']:
                        name, ext = os.path.splitext(filename)
                        ext = ext[1:].upper()  # Remove the '.' and capitalize
                        self.photos.append({
                            "dir": directory['name'],
                            "filename": filename,
                            "name": name,
                            "ext": ext,
                            "path": f"{directory['name']}/{filename}",
                            "to_transfer": False,
                        })
                logger.info(f"{len(self.photos)} photos found on the device.")
                self._set_photo_transfer_status()
                self._connected = True
                return True
        except urllib.error.URLError as e:
            logger.error(f"Connection error while recovering photos: {e.reason}")
            return False
        except json.JSONDecodeError:
            logger.error("Invalid JSON response when retrieving photos.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while recovering photos: {e}")
            return False


    def _set_photo_transfer_status(self) -> bool:
        """Updates the photo list to know if an image should be transferred
        Returns:
             True on success, False on failure.
        """
        resp = urllib.request.Request(API_HOST + API_TRANSFER)
        try:
            resp = urllib.request.urlopen(resp, timeout=self.timeout)
            data = json.loads(resp.read())
            if data['errCode'] != 200:
                logger.error(f"API error code: {data['errCode']}, message: {data['errMsg']}")
                return False
            else:
                to_transfer = []
                for f in data.get('transfers'):
                    to_transfer.append(f.get('filepath'))
                for f in self.photos:
                    if f.get('path') in to_transfer:
                        f['to_transfer'] = True
                return True
        except urllib.error.URLError as e:
            logger.error(f"Connection error while recovering photos: {e.reason}")
            return False
        except json.JSONDecodeError:
            logger.error("Invalid JSON response when retrieving photos.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while recovering photos : {e}")
            return False

    def get_photos(self, to_transfer_only: bool = False, ext: Optional[str] = None,
                   directory: Optional[str] = None) -> list:
        """Return the list of photos
        Filters photos by extension, directory, or transfer status

        Args:
            to_transfer_only: True if you want to download only photos as marked to download to the device,
            False otherwise
            ext: image extension
            directory: image folder

        Returns:
            Photos list

        """
        filtered_photos = self.photos
        if to_transfer_only:
            filtered_photos = [p for p in filtered_photos if p['to_transfer']]
        if ext is not None:
            filtered_photos = [p for p in filtered_photos if p['ext'].upper() == ext.upper()]
        if directory is not None:
            filtered_photos = [p for p in filtered_photos if p['dir'] == directory]
        logger.debug(f"{len(filtered_photos)} photos match filter parameters")
        return filtered_photos

    def get_model(self) -> str:
        """
        Returns:
            model name
        """
        return self.model

    def get_name(self) -> str:
        """
        Returns:
            device name
        """
        return self.name

    def get_battery(self) -> int:
        """
        Returns:
            device battery level
        """
        return self.battery

    def is_connected(self) -> bool:
        """
        Returns:
            True if connected, False otherwise.
        """
        try:
            self._test_connection()
            return True
        except (urllib.error.URLError, json.JSONDecodeError):
            return False

    def shutdown(self) -> bool:
        """Shutdown Camera via API endpoint (POST)
        Returns:
            True on success, False on failure
        """
        url = API_HOST + API_SHUTDOWN
        req = urllib.request.Request(url)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, b"{}", timeout=self.timeout) as resp:
                if resp.getcode() != 200:
                    logger.error(f"Error when turning off the device : {resp.getcode()}")
                    return False
            logger.info(f"Shutdown Camera {self.model} {self.name}...")
            self._connected = False
            return True
        except urllib.error.URLError as e:
            logger.error(f"Exception when stopping the device : {e.reason}")
            return False