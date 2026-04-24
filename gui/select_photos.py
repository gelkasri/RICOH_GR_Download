#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Window to select photos to transfer
"""

import tkinter as tk
import tkinter.ttk as ttk
import urllib
from urllib import request, error

from PIL.ImageTk import PhotoImage, Image

from log_config import logger
from src.config import API_HOST, API_PHOTO_LIST, SIZE_THUMB_QUERY, SIZE_VIEW_QUERY, REQUEST_TIMEOUT, THUMB_SIZE_X, \
    THUMB_SIZE_Y, MAX_ROW_THUMB, THUMB_PADY, SELECT_PHOTO_GUI_SIZE, THUMB_PADX, THUMB_BATCH_SIZE
from src.downloader import Downloader


class SelectPhotos:
    """Class to select photos to transfer"""
    def __init__(self, down: Downloader) -> None:
        self.root = tk.Toplevel()
        self.root.title("Sélectionner les photos à transférer")
        self.root.geometry(SELECT_PHOTO_GUI_SIZE)
        self.root.resizable(width=True, height=True)
        self.root.grab_set()
        if down.camera is not None:
            self.photos = down.camera.photos
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.tv_frame = ttk.Frame(self.main_frame)
        self.tv_frame.pack(fill='x', expand=False, side='top')
        self.selected_photo = []
        self.thumb = []
        self._configure_treeview()
        self.f_button = ttk.Frame(self.main_frame)
        ttk.Button(self.f_button, text="Valider la sélection",
                   command=lambda: self._update_selection(down)).pack(pady=10, anchor='center', side='left')
        ttk.Button(self.f_button, text="Annuler",
                   command=lambda: self._cancel_selection(down)).pack(pady=10, anchor='center', side='left')
        self.f_button.pack(side='bottom', anchor='center')
        try:
            self._fill_treeview_without_previews()
            self.current_photo_index = 0
            self._load_next_batch()
        except AttributeError:
            logger.error(f"Unable to load photos: device not connected")
        self.root.wait_window()


    def _configure_treeview(self):
        self.tv_photo_list = ttk.Treeview(self.tv_frame, columns=("Extension", "Directory", "Filename"),
                                          height=MAX_ROW_THUMB, selectmode='extended')
        self.tv_photo_list.pack(fill='x', side='left', expand=True)
        self.tv_photo_list.heading('Directory', text='Directory')
        self.tv_photo_list.heading('Filename', text='File name')
        self.tv_photo_list.heading('Extension', text='Format')
        self.tv_photo_list.column('#0', width=THUMB_SIZE_X + THUMB_PADX, anchor='center')
        self.tv_photo_list.column('Extension', width=50, anchor='center')
        self.tv_photo_list.column('Directory', width=100, anchor='center')
        self.tv_photo_list.column('Filename', anchor='center')
        s = ttk.Style()
        s.configure('Treeview', rowheight=THUMB_SIZE_Y + THUMB_PADY)
        v_scrollbar = ttk.Scrollbar(self.tv_frame, command=self.tv_photo_list.yview, orient='vertical')
        self.tv_photo_list.configure(yscrollcommand=v_scrollbar.set)
        v_scrollbar.pack(side='right', fill='y')


    def _fill_treeview(self) -> None:
        """Unused"""
        for photo in self.photos:
            size = SIZE_THUMB_QUERY if '.DNG' in photo else SIZE_VIEW_QUERY
            url = API_HOST + API_PHOTO_LIST + '/' + photo.get('path') + size
            try:
                resp = urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT)
                img = Image.open(resp)
                image = PhotoImage(img.resize((THUMB_SIZE_X, THUMB_SIZE_Y)))
                self.thumb.append(image)
            except urllib.error.URLError:
                logger.error(f"Unable to load preview: URL error {url}")
            self.tv_photo_list.insert("", 'end',
                                      values=[photo.get('ext'), photo.get('dir'), photo.get('filename')],
                                      tags=photo.get('path'),
                                      image=self.thumb[-1]
                                      )

    def _fill_treeview_without_previews(self) -> None:
        """Remplit le Treeview avec les métadonnées (sans les previews)."""
        for photo in self.photos:
            self.tv_photo_list.insert(
                "",'end',
                values=[photo.get('ext'), photo.get('dir'), photo.get('filename')],
                tags=photo.get('path'),
            )

    def _load_next_preview(self) -> None:
        """Unused
        Load and display the next preview asynchronously."""
        if self.current_photo_index < len(self.photos):
            photo = self.photos[self.current_photo_index]
            size = SIZE_THUMB_QUERY if '.DNG' in photo else SIZE_VIEW_QUERY
            url = API_HOST + API_PHOTO_LIST + '/' + photo.get('path') + size

            try:
                resp = urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT)
                img = Image.open(resp)
                image = PhotoImage(img.resize((THUMB_SIZE_X, THUMB_SIZE_Y)))
                self.thumb.append(image)

                # Updates the corresponding row in the Treeview
                item_id = self.tv_photo_list.get_children()[self.current_photo_index]
                self.tv_photo_list.item(item_id, image=image)

                self.current_photo_index += 1
                # Schedules the next image to load after a short delay
                self.root.after(50, self._load_next_preview)

            except urllib.error.URLError:
                logger.error(f"Unable to load preview: URL error {url}")
                self.current_photo_index += 1
                self.root.after(30, self._load_next_preview)

    def _load_next_batch(self) -> None:
        """Load a batch of previews asynchronously."""
        batch_end = min(self.current_photo_index + THUMB_BATCH_SIZE, len(self.photos))

        # Load all images from current batch
        for i in range(self.current_photo_index, batch_end):
            photo = self.photos[i]
            size = SIZE_THUMB_QUERY if '.DNG' in photo else SIZE_VIEW_QUERY
            url = API_HOST + API_PHOTO_LIST + '/' + photo.get('path') + size

            try:
                resp = urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT)
                img = Image.open(resp)
                image = PhotoImage(img.resize((THUMB_SIZE_X, THUMB_SIZE_Y)))
                self.thumb.append(image)

                # Updates the corresponding row in the Treeview
                item_id = self.tv_photo_list.get_children()[i]
                self.tv_photo_list.item(item_id, image=image)

            except urllib.error.URLError:
                logger.error(f"Unable to load preview: URL error {url}")
                self.thumb.append(None)

        # Updates index and schedules next batch
        self.current_photo_index = batch_end
        if self.current_photo_index < len(self.photos):
            self.root.after(30, self._load_next_batch)


    def _update_selection(self, down:Downloader) -> None:
        sel = self.tv_photo_list.selection()
        self.selected_photo = []
        for index in sel:
            self.selected_photo.append(self.tv_photo_list.item(index).get('tags')[0])
        down.gui_selected_photos = self.selected_photo if len(self.selected_photo) > 0 else None
        logger.debug(f"{len(self.selected_photo)} photos selected")
        self.root.destroy()


    def _cancel_selection(self, down:Downloader):
        self.selected_photo.clear()
        down.gui_selected_photos = None
        self.root.destroy()