#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Window to select photos to transfer
"""

import tkinter as tk
import tkinter.ttk as ttk

from log_config import logger
from src.downloader import Downloader


class SelectPhotos:
    """Class to select photos to transfer"""
    def __init__(self, down: Downloader) -> None:
        self.root = tk.Tk()
        self.root.title("Sélectionner les photos à transférer")
        self.root.geometry("400x600")
        self.root.resizable(width=True, height=True)
        if down.camera is not None:
            self.photos = down.camera.photos
        self.tv_frame = ttk.Frame(self.root)
        self.tv_frame.pack(fill='both', expand=True)
        self.tv_photo_list = ttk.Treeview(self.tv_frame, columns=("Directory", "Filename"))
        self.selected_photo = []
        self._configure_treeview()
        self.f_button = ttk.Frame(self.root)
        self.f_button.pack(side='bottom', pady=10, fill='x')
        ttk.Button(self.f_button, text="Valider la sélection",
                   command=lambda: self._update_selection(down)).pack(pady=10, anchor='center')
        ttk.Button(self.f_button, text="Annuler",
                   command=lambda: self._cancel_selection(down)).pack(pady=10, anchor='center')
        try:
            self._fill_treeview()
        except AttributeError:
            logger.debug(f"No photos to display")
            pass
        self.root.mainloop()


    def _configure_treeview(self):
        self.tv_photo_list.pack(side='left' ,fill='both', expand=True)
        self.tv_photo_list.heading('Directory', text='Directory')
        self.tv_photo_list.heading('Filename', text='File name')
        self.tv_photo_list.column('#0', width=50, anchor='w')
        self.tv_photo_list.column('Directory', width=150, anchor='center')
        self.tv_photo_list.column('Filename', width=180, anchor='center')
        v_scrollbar = ttk.Scrollbar(self.tv_frame, command=self.tv_photo_list.yview)
        self.tv_photo_list.configure(yscrollcommand=v_scrollbar.set)
        v_scrollbar.pack(side='right', fill='y')


    def _fill_treeview(self):
        n = 0
        for photo in self.photos:
            n += 1
            self.tv_photo_list.insert("", 'end',
                                      text= str(n),
                                      values=[photo.get('dir'), photo.get('filename')],
                                      tags=photo.get('path')
                                      )


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