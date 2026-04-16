#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image download management
"""
import os
import shutil
import urllib
import time
from urllib import request
from queue import Queue
from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from log_config import logger
from src.camera import RicohCamera
from src.config import (REQUEST_TIMEOUT, DEFAULT_DEST_DIR,
                        API_HOST, API_PHOTO_LIST,
                        RAW_EXTENSION, JPG_EXTENSION, MAX_WORKERS, USE_MULTI_THREADING)


class Downloader:
    """Handles downloading photos from a Ricoh GR camera

    Attributes:
        timeout (int): Request timeout in seconds.
        camera (RicohCamera): Camera instance for fetching photos.
        jpg_only (bool): If True, only download JPG files.
        raw_only (bool): If True, only download RAW files.
        to_transfer_only (bool): If True, only download photos marked for transfer.
        dir_to_transfer (Optional[str]): Specific directory to download from.
        dest_dir (str): Local destination directory for downloaded photos.
        _local_files_list (List[str]): List of files already present in dest_dir.
        _remote_file_list (List[str]): List of files to download from the camera.
    """
    def __init__(self,
                 dest_dir: str = DEFAULT_DEST_DIR,
                 jpg_only: bool = False,
                 raw_only: bool = False,
                 to_transfer_only: bool = False,
                 dir_to_transfer: str = None,
                 camera: RicohCamera = None,
                 ):
        """
        Args:
            dest_dir: Destination directory name
            jpg_only: True if you only want jpg files, False otherwise
            raw_only: True if you only want raw files, False otherwise
            to_transfer_only: True if you only want the photos marked as 'to transfer', False otherwise
            dir_to_transfer: Directory of the device to transfer, None if you want all directories
            camera: RicohCamera object used for device connection
        """
        self.timeout = REQUEST_TIMEOUT
        self.camera = camera
        self.jpg_only = jpg_only
        self.raw_only = raw_only
        self.to_transfer_only = to_transfer_only
        self.dir_to_transfer = dir_to_transfer
        if dest_dir is None:
            self.dest_dir = DEFAULT_DEST_DIR
        else:
            self.dest_dir = dest_dir
        self.dest_dir = os.path.normpath(os.path.expanduser(self.dest_dir))
        self._local_files_list = []
        self._remote_file_list = []


    def _get_dest_dir_files(self) -> list:
        """
        List files present in the destination directory, used to avoid overwriting an existing photo
        Returns:
            List of relative paths of all files present in the directory
        """
        file_list = []
        max_depth = 1
        # Create the folder if it does not exist
        logger.debug(f"Destination directory is : {self.dest_dir}")
        try:
            os.makedirs(self.dest_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Unable to create/access directory {self.dest_dir}: {e}")
        if not os.access(self.dest_dir, os.W_OK):
            logger.error(f"Unable to write to folder {self.dest_dir} - No permission")
            raise PermissionError
        for (root, directory, files) in os.walk(self.dest_dir, followlinks=False):
            depth = root[len(self.dest_dir):].count(os.sep)
            if depth > max_depth:
                directory[:] = []
                continue
            for f in files:
                file_list.append(os.path.join(str(root), str(f)).replace(self.dest_dir, ""))
        return file_list


    def download(self, queue: Optional[Queue] = None) -> bool:
        """
        Downloading all photos, applying filters (JPG/RAW/transfer status)
        Args:
            queue: Queue object used in GUI mode for send transfer progression and logs
        Returns:
            True if success, False on failure
        """
        if self.camera is None:
            logger.critical("Warning: download() call without camera")
            return False

        if not self.camera.set_photo_list(): return False
        if self.raw_only:
            photos_filtered = self.camera.get_photos(ext=RAW_EXTENSION, to_transfer_only=self.to_transfer_only,
                                              directory=self.dir_to_transfer)
        elif self.jpg_only:
            photos_filtered = self.camera.get_photos(ext=JPG_EXTENSION, to_transfer_only=self.to_transfer_only,
                                              directory=self.dir_to_transfer)
        else:
            photos_filtered = self.camera.get_photos(to_transfer_only=self.to_transfer_only,
                                              directory=self.dir_to_transfer)
        total_files = len(photos_filtered)
        if total_files == 0:
            logger.info("No photos to download.")
            return True
        self._remote_file_list.clear()
        for photo in photos_filtered:
            remote_path = str(Path(photo["dir"]) / photo["filename"]).replace("\\", "/")
            self._remote_file_list.append(f"/{remote_path}")
        try:
            self._local_files_list = self._get_dest_dir_files()
        except OSError:
            return False
        photos_to_download = [
            file for file in self._remote_file_list
            if Path(file).as_posix() not in self._local_files_list
        ]
        skipped_files = total_files - len(photos_to_download)
        logger.info(f"{skipped_files} files already exist. Downloading {len(photos_to_download)} new files.")
        start_time = time.time()
        if USE_MULTI_THREADING:
            logger.debug(f"Multi-threading activated, max workers = {MAX_WORKERS}")
            self.multi_thread_download(photos_to_download, queue)
        else:
           self.single_thread_download(photos_to_download, queue)
        end_time = time.time()
        logger.debug(f"Download time : {end_time - start_time} seconds")
        return True

    def single_thread_download(self,photos_to_download: list, queue: Optional[Queue] = None) -> bool:
        """Downloading all photos, applying filters (JPG/RAW/transfer status)
        Args:
            photos_to_download: Photos to download (after filtering)
            queue: Queue object used in GUI mode for send transfer progression and logs

        Returns:
        """
        count = 0
        transferred = 0
        total_file = len(photos_to_download)
        if queue is not None: queue.put(0)
        for file in photos_to_download:
            count += 1
            logger.info(f"{count}/{total_file} - Downloading {file}" )
            if self._download_photo(file, self.dest_dir):
                transferred += 1
            progress = int(count/total_file*100) if total_file > 0 else 0
            if queue is not None: queue.put(progress) # To send progress to the interface
        logger.info(f"Download finished : {transferred} pictures transferred, {total_file - transferred} failed")
        return True


    def multi_thread_download(self, photos_to_download:list ,queue: Optional[Queue] = None) -> bool:
        """Downloading all photos, applying filters (JPG/RAW/transfer status), using threads
        Args:
            photos_to_download: Photos to download (after filtering)
            queue: Queue object used in GUI mode for send transfer progression and logs

        Returns: True on success, False on failure
        """
        count = 0
        transferred = 0
        total_file = len(photos_to_download)
        if queue is not None: queue.put(0)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all download tasks
            future_to_file = {
                executor.submit(self._download_photo, file, self.dest_dir): file
                for file in photos_to_download
            }
            # Process completed futures as they finish
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    if future.result():
                        transferred += 1
                    progress = int((transferred / len(photos_to_download)) * 100) if photos_to_download else 0
                    if queue is not None: queue.put(progress) # To send progress to the interface
                    logger.info(f"Downloaded {file} ({transferred}/{len(photos_to_download)})")
                except Exception as e:
                    logger.error(f"Failed to download {file}: {e}")
        logger.info(f"Download finished : {transferred} pictures transferred, {total_file - transferred} failed")
        return True


    def _download_photo(self, photo: str, destination: str) -> bool:
        """
        Download a photo to the destination directory
        Args:
            photo: path of the photo to download
            destination: local directory to save the photo

        Returns:
            True on success, False on failure
        """
        try:
            resp = urllib.request.urlopen(API_HOST + API_PHOTO_LIST + photo, timeout=self.timeout)
            os.makedirs(os.path.dirname(destination+photo), exist_ok=True)
            dest_path = Path(destination) / photo.lstrip("/")
            with open(dest_path, "wb") as newfile:
                shutil.copyfileobj(resp, newfile)
            return True
        except Exception as e:
            logger.error(f"Unable to download photo {photo}, error: {e}")
            return False