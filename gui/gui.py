#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graphical User Interface for Ricoh GR photo transfer
"""
import argparse
import json
import threading
import tkinter as tk
import tkinter.ttk as ttk
import urllib
from queue import Queue, Empty
from tkinter import filedialog, messagebox, scrolledtext
from urllib import error

from .log_handler import TkinterHandler
from log_config import logger, set_log_level
from src.camera import RicohCamera
from src.config import (GUI_TITLE, GUI_GEOM, GUI_RESIZABLE_W, GUI_RESIZABLE_H,
                        ALL_EXTENSIONS, JPG_EXTENSION, RAW_EXTENSION, GUI_GEOM_X,
                        GUI_COLOR_CONNECTION_KO, GUI_COLOR_CONNECTION_OK, GUI_QUEUE_MAJ_MS)
from src.downloader import Downloader


def destroy_widgets_in_frame(frame: ttk.Frame) -> None:
    """Destroys all child widgets in a Tkinter frame
    Args:
        frame: Tkinter frame to clean
    """
    for widget in frame.winfo_children():
        widget.destroy()


class GUI:
    """
    Graphical User Interface for Ricoh GR photo transfer. Handles camera connection, photo download, and display
    """
    def __init__(self, args: argparse.Namespace, downloader: Downloader):
        self.args = args
        self.downloader = downloader
        logger.debug(f"Launching the GUI with arguments {self.args}")
        self.root = tk.Tk()
        self.root.title(GUI_TITLE)
        self.root.geometry(GUI_GEOM)
        self.root.resizable(GUI_RESIZABLE_W, GUI_RESIZABLE_H)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)  # Handle window close

        # For GUI objects
        self._connection_indic = None
        self._f_cam_info = None
        self._dest_dir = tk.StringVar(value=self.downloader.dest_dir)
        self._ext_choice = tk.StringVar()
        if self.downloader.jpg_only == self.downloader.raw_only:
            self._ext_choice.set(ALL_EXTENSIONS)
        elif self.downloader.jpg_only:
            self._ext_choice.set(JPG_EXTENSION)
        else:
            self._ext_choice.set(RAW_EXTENSION)
        self._to_transfer_only = tk.BooleanVar(value=self.downloader.to_transfer_only)
        self._v_progress = tk.IntVar(value=0)
        self._v_progress_label = f"Progression du transfert : {self._v_progress.get()}%"

        # Get the logs with a queue and a thread
        self._log_queue = Queue()
        self._tkinter_handler = TkinterHandler(self._log_queue)
        logger.addHandler(self._tkinter_handler)
        set_log_level(logger_to_set=logger, log_level=args.log_level)
        self._check_log_queue()

        self._create_widgets()
        self.root.mainloop()

    def _on_close(self) -> None:
        """Cleanup before closing the window."""
        logger.removeHandler(self._tkinter_handler)
        self.root.destroy()

    def _refresh_connection_indic(self) -> bool:
        """Updates the connection status indicator and camera info.

        Returns:
            True if device is connected, False otherwise
        """
        if self.downloader.camera is None:
            try:
                self.downloader.camera = RicohCamera()
            except (urllib.error.URLError, json.JSONDecodeError):
                self._connection_indic.create_oval(2, 2, 18, 18, fill=GUI_COLOR_CONNECTION_KO, outline="")
                destroy_widgets_in_frame(self._f_cam_info)
                ttk.Label(self._f_cam_info, text="Aucun appareil connecté",
                          foreground=GUI_COLOR_CONNECTION_KO).pack(padx=10)
                return False
        c = self.downloader.camera
        if c.is_connected():
            self._connection_indic.create_oval(2, 2, 18, 18, fill=GUI_COLOR_CONNECTION_OK, outline="")
            destroy_widgets_in_frame(self._f_cam_info)
            ttk.Label(self._f_cam_info, text=f"Modèle : {c.get_model()}").pack(padx=10, side="top", anchor="nw")
            ttk.Label(self._f_cam_info, text=f"Batterie : {c.get_battery()}%").pack(padx=10, side="top", anchor="nw")
            ttk.Label(self._f_cam_info, text=f"Nom de l'appareil : {c.get_name()}").pack(padx=10, side="top", anchor="nw")
            return True
        else:
            self._connection_indic.create_oval(2, 2, 18, 18, fill=GUI_COLOR_CONNECTION_KO, outline="")
            destroy_widgets_in_frame(self._f_cam_info)
            ttk.Label(self._f_cam_info, text="Aucun appareil connecté",
                      foreground=GUI_COLOR_CONNECTION_KO).pack(padx=10)
            return False


    def _check_log_queue(self) -> None:
        """
        Periodically checks the log queue and displays new messages in the GUI
        """
        try:
            message = self._log_queue.get_nowait()
            self._log_text.insert(tk.END, message + "\n")
            self._log_text.see(tk.END)
        except Empty:
            pass
        self.root.after(GUI_QUEUE_MAJ_MS, self._check_log_queue)


    def _choose_directory(self) -> None:
        """
        Periodically checks the log queue and displays new messages in the GUI
        """
        directory = filedialog.askdirectory(initialdir=self._dest_dir.get(),
                                            title="Choisissez le répertoire de destination")
        if directory:
            self._dest_dir.set(directory)
            self.downloader.dest_dir = directory


    def _shutdown(self):
        """
        Shuts down the camera
        Called by disconnect button
        TODO: meilleure gestion des logs : pas mal de logs en double, dans refresh_connection_indic
        """
        if self.downloader.camera:
            self.downloader.camera.shutdown()
            self.root.after(1000, self._refresh_connection_indic)


    def _start_download(self) -> None:
        """
        Start the photo transfer process
        Updates downloader settings (extension, transfer flags) and starts the download in a thread
        Called by the "Start transfer" button
        Uses a Queue to receive progress updates from the Downloader thread
        """
        progress_queue = Queue()
        def update_progress():
            """Update the progress bar
            """
            try:
                progress = progress_queue.get_nowait()
                self._v_progress.set(progress)
                self.f_progress.config(text=f"Progression du transfert : {progress}%")
            except Empty:
                pass
            self.root.after(GUI_QUEUE_MAJ_MS, func=update_progress)
        update_progress()
        self.downloader.to_transfer_only = self._to_transfer_only.get()
        ext = self._ext_choice.get()
        self.downloader.raw_only = (ext == RAW_EXTENSION)
        self.downloader.jpg_only = (ext == JPG_EXTENSION)
        if not self._refresh_connection_indic():
            tk.messagebox.showwarning(title="Aucun appareil connecté",
                                      message="Aucun appareil connecté",
                                      detail="Vérifier la connection au Wi-Fi de l'appareil")
            return
        try:
            thread = threading.Thread(target=self.downloader.download, args=(progress_queue,), daemon=True)
            thread.start()
        except Exception as e:
            tk.messagebox.showerror(message=f"Erreur lors du téléchargement des photos : {e}")


    def _create_widgets(self):
        """Creates the 'Transfer' tab with all its widgets"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self._create_transfer_tab()


    def _create_transfer_tab(self) -> None:
        """Creates the 'Transfer' tab with all its widgets"""
        transfer_tab = ttk.Frame(self.notebook)
        self.notebook.add(transfer_tab, text="Transfert des photos")
        self._create_connection_frame(transfer_tab)
        self._create_directory_frame(transfer_tab)
        self._create_options_frame(transfer_tab)
        self._create_transfer_frame(transfer_tab)
        self._create_log_frame(transfer_tab)
        self._create_disconnect_frame(transfer_tab)


    def _create_connection_frame(self, parent: ttk.Frame) -> None:
        """Create connection status frame"""
        f_connect = ttk.LabelFrame(parent, text="Connexion à l'appareil")
        f_connect.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        ttk.Label(f_connect, text="Connexion à l'appareil : ").pack(pady=10, side="left")
        # TODO: trouver un moyen pour rendre le fond du canevas transparent
        self._connection_indic = tk.Canvas(f_connect, width=20, height=20, highlightthickness=0)
        self._connection_indic.pack(fill="x", expand=False, padx=5, pady=5, side="left")
        ttk.Button(f_connect, text="Rafraichir", command=self._refresh_connection_indic).pack(pady=10, side="left")
        ttk.Frame(f_connect).pack(fill="x", expand=False, padx=50, side="left") # Margin between the two Frames
        self._f_cam_info = ttk.Frame(f_connect)
        self._f_cam_info.pack(expand=False, padx=5, pady=5, side="left")
        self._refresh_connection_indic()


    def _create_directory_frame(self, parent: ttk.Frame) -> None:
        """Creates the destination directory selection frame."""
        f_dir = ttk.LabelFrame(parent, text="Choix du répertoire de destination")
        f_dir.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        ttk.Label(f_dir, text="Répertoire de destination : ").pack(pady=10, side="left")
        # TODO: ne fonctionne pas quand on écrit le chemin à la main
        ttk.Entry(f_dir, textvariable=self._dest_dir).pack(pady=10, side="left", fill="x", expand=True)
        ttk.Button(f_dir, text="Parcourir", command=self._choose_directory).pack(pady=10, padx=5, side="left")


    def _create_options_frame(self, parent: ttk.Frame) -> None:
        """Creates the transfer options frame."""
        f_opt = ttk.LabelFrame(parent, text="Options de transfert")
        f_opt.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        f_opt_ext = ttk.Frame(f_opt)
        f_opt_ext.pack(fill="y", expand=False, padx=5, pady=5, side="left")
        ttk.Radiobutton(f_opt_ext, text="Toutes les images", value=ALL_EXTENSIONS,
                        variable=self._ext_choice).pack(side="top", anchor="w")
        ttk.Radiobutton(f_opt_ext, text="RAW uniquement", value=RAW_EXTENSION,
                        variable=self._ext_choice).pack(side="top", anchor="w")
        ttk.Radiobutton(f_opt_ext, text="JPG uniquement", value=JPG_EXTENSION,
                        variable=self._ext_choice).pack(side="top", anchor="w")
        ttk.Frame(f_opt).pack(fill="y", expand=False, padx=100, side="left") # Marge entre les deux Frames
        f_opt_flag = ttk.Frame(f_opt)
        f_opt_flag.pack(fill="y", expand=False, padx=5, pady=5, side="left")
        ttk.Checkbutton(f_opt_flag, text="Uniquement photos avec flag de transfert",
                        variable=self._to_transfer_only).pack(anchor="nw")
        ttk.Frame(f_opt_flag).pack(fill="x", expand=True)
        ttk.Button(f_opt_flag, text="Sélectionner les photos à transférer").pack(anchor="sw")


    def _create_transfer_frame(self, parent: ttk.Frame) -> None:
        """Create file transfer frame and progress bar."""
        f_transfer = ttk.Frame(parent)
        f_transfer.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        ttk.Button(f_transfer, text="Démarrer le transfert", command=self._start_download).pack(pady=10, side="left")

        self.f_progress = ttk.LabelFrame(parent,
                                         text=self._v_progress_label)
        self.f_progress.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        ttk.Progressbar(self.f_progress, orient="horizontal", mode="determinate",
                        length=GUI_GEOM_X-100, variable=self._v_progress).pack(pady=5, side="left")


    def _create_log_frame(self, parent: ttk.Frame) -> None:
        """Create log display frame"""
        f_log = ttk.LabelFrame(parent, text="Logs")
        f_log.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        self._log_text = scrolledtext.ScrolledText(f_log, height=10, width=200)
        self._log_text.pack(pady=10, side="left")


    def _create_disconnect_frame(self, parent: ttk.Frame) -> None:
        """Create the disconnection button frame"""
        f_disconnect = ttk.LabelFrame(parent)
        f_disconnect.pack(fill="x", expand=False, padx=5, pady=5, side="top")
        ttk.Button(f_disconnect, text="Déconnecter l'appareil", command=self._shutdown).pack(pady=10, side="left")