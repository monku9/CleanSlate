#!/usr/bin/env python3
"""
CleanSlate
==========
A dead-simple app that backs up your files to a USB flash drive before a
clean Windows install (or a ChromeOS Powerwash), then hands you a
plain-English checklist for the rest.

Works on Windows, ChromeOS (via the Linux/Crostini container), macOS, and
general Linux.

No accounts. No internet required. No external libraries -
just Python's standard library, start to finish.

Author: Monkx Games
License: MIT
"""

import os
import sys
import string
import shutil
import queue
import threading
import time
import datetime
import platform as platform_module
import subprocess
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox

if os.name == "nt":
    import ctypes

APP_NAME = "CleanSlate"
APP_VERSION = "2.1"


def detect_platform():
    """Figure out which OS we're really running on.

    ChromeOS doesn't run Python natively - it runs inside the Linux
    (Crostini) container, which looks like plain Debian. We check for a
    couple of ChromeOS-specific fingerprints to tell the difference:
      - /dev/.cros_milestone only exists inside a ChromeOS Linux container
      - /mnt/chromeos is the special folder ChromeOS shares into that
        container (Downloads, removable drives, etc.)
      - "penguin" is the default hostname Crostini gives its container
    """
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    try:
        if (os.path.exists("/dev/.cros_milestone")
                or os.path.isdir("/mnt/chromeos")
                or platform_module.node() == "penguin"):
            return "chromeos"
    except Exception:
        pass
    return "linux"


PLATFORM = detect_platform()

# ----------------------------------------------------------------------
# Theme - dark, purple, with a hint of blue. Change these and the whole
# app follows.
# ----------------------------------------------------------------------
COLOR_BG            = "#131020"
COLOR_CARD          = "#1C1830"
COLOR_CARD_BORDER   = "#2E2850"
COLOR_PRIMARY       = "#8B5CF6"
COLOR_PRIMARY_HOVER = "#7C4DEF"
COLOR_BLUE_HINT     = "#5B8DEF"
COLOR_TEXT          = "#F2EFFB"
COLOR_MUTED         = "#8D87A8"
COLOR_SUCCESS       = "#34D399"
COLOR_SUCCESS_HOVER = "#22B989"
COLOR_DANGER        = "#F87171"
COLOR_DANGER_HOVER  = "#E15C5C"
COLOR_GHOST_HOVER   = "#272042"
COLOR_DISABLED      = "#332F45"
COLOR_DISABLED_TEXT = "#6B6580"

FONT_H1 = ("Segoe UI", 26, "bold")
FONT_H2 = ("Segoe UI", 16, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_BODY_BOLD = ("Segoe UI", 12, "bold")
FONT_SMALL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 12, "bold")


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def human_size(num_bytes):
    num_bytes = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024 or unit == "TB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"


def _drive_entry(path, label):
    try:
        usage = shutil.disk_usage(path)
        return {"path": path, "label": label, "free": usage.free, "total": usage.total}
    except Exception:
        return None


def _get_removable_drives_windows():
    drives = []
    DRIVE_REMOVABLE = 2
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if not (bitmask & (1 << i)):
            continue
        root = f"{letter}:\\"
        try:
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(root)
        except Exception:
            continue
        if drive_type != DRIVE_REMOVABLE:
            continue
        free_bytes = ctypes.c_ulonglong(0)
        total_bytes = ctypes.c_ulonglong(0)
        try:
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(root), None,
                ctypes.pointer(total_bytes), ctypes.pointer(free_bytes)
            )
        except Exception:
            pass
        label_buf = ctypes.create_unicode_buffer(261)
        try:
            ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(root), label_buf, ctypes.sizeof(label_buf),
                None, None, None, None, 0
            )
        except Exception:
            pass
        drives.append({
            "path": root,
            "label": label_buf.value.strip() or "USB Drive",
            "free": free_bytes.value,
            "total": total_bytes.value,
        })
    return drives


def _get_removable_drives_chromeos():
    """On ChromeOS, a USB drive only shows up here after the user shares it
    with Linux from the Files app (right-click the drive -> Share with
    Linux). ChromeOS then mounts it under /mnt/chromeos/removable/."""
    drives = []
    base = "/mnt/chromeos/removable"
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            entry = _drive_entry(os.path.join(base, name), name)
            if entry:
                drives.append(entry)
    return drives


def _get_removable_drives_linux():
    drives = []
    seen_paths = set()
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    candidate_bases = [f"/media/{user}", f"/run/media/{user}", "/media"]
    for base in candidate_bases:
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if path in seen_paths or not os.path.isdir(path):
                continue
            seen_paths.add(path)
            entry = _drive_entry(path, name)
            if entry:
                drives.append(entry)
    return drives


def _get_removable_drives_mac():
    drives = []
    base = "/Volumes"
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            if name == "Macintosh HD":
                continue
            path = os.path.join(base, name)
            if os.path.isdir(path):
                entry = _drive_entry(path, name)
                if entry:
                    drives.append(entry)
    return drives


def get_removable_drives():
    if PLATFORM == "windows":
        return _get_removable_drives_windows()
    if PLATFORM == "chromeos":
        return _get_removable_drives_chromeos()
    if PLATFORM == "mac":
        return _get_removable_drives_mac()
    return _get_removable_drives_linux()


def get_common_folders():
    home = os.path.expanduser("~")
    candidates = [
        ("Desktop", os.path.join(home, "Desktop")),
        ("Documents", os.path.join(home, "Documents")),
        ("Pictures", os.path.join(home, "Pictures")),
        ("Music", os.path.join(home, "Music")),
        ("Videos", os.path.join(home, "Videos")),
        ("Downloads", os.path.join(home, "Downloads")),
    ]
    return [(name, path) for name, path in candidates if os.path.isdir(path)]


def collect_files(selected_paths):
    plan = []
    total_size = 0
    for p in selected_paths:
        if os.path.isfile(p):
            rel = os.path.basename(p)
            try:
                size = os.path.getsize(p)
            except OSError:
                size = 0
            plan.append((p, rel))
            total_size += size
        elif os.path.isdir(p):
            parent = os.path.dirname(os.path.normpath(p))
            for root, _dirs, filenames in os.walk(p):
                for fn in filenames:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, parent)
                    try:
                        size = os.path.getsize(full)
                    except OSError:
                        size = 0
                    plan.append((full, rel))
                    total_size += size
    return plan, total_size


CHECKLIST_CONTENT_WINDOWS = """FRESH START CHECKLIST (Windows)
================================
Made for you by CleanSlate on {date}

Before you wipe your PC:
  [ ] Confirm this backup finished with no errors
  [ ] Note your Wi-Fi password (Settings > Network > Wi-Fi > Manage known networks)
  [ ] Write down any software license/product keys you'll need again
  [ ] Sign out of apps that only allow a few active devices (Steam, Adobe, etc.)
  [ ] Make sure important files are synced (OneDrive, Google Drive, Dropbox)
  [ ] Charge your laptop or make sure your desktop won't lose power mid-install

To do the clean install:
  [ ] Go to microsoft.com/software-download and get the official Media Creation Tool
  [ ] Create installation media on a SECOND USB drive (not this backup drive!)
  [ ] Restart your PC and boot from that USB drive
  [ ] Choose "Custom install" and pick "Delete" on old partitions for a truly clean install
  [ ] Follow the on-screen setup steps

After Windows is reinstalled:
  [ ] Reconnected to Wi-Fi using the password you saved
  [ ] Installed graphics/chipset drivers
  [ ] Plugged this drive back in and copied your files back over
  [ ] Reinstalled your favorite apps
  [ ] Breathe. You did it. Enjoy the clean, fast PC!

-- CleanSlate v{version}
"""

CHECKLIST_CONTENT_CHROMEOS = """FRESH START CHECKLIST (ChromeOS)
=================================
Made for you by CleanSlate on {date}

Before you Powerwash:
  [ ] Confirm this backup finished with no errors
  [ ] Make sure you know your Google Account password (you'll sign back in after)
  [ ] Note your Wi-Fi password if it isn't saved anywhere else
  [ ] Double-check important files are synced to Google Drive
  [ ] Make sure your Chromebook is charged or plugged in

To Powerwash your Chromebook:
  [ ] Open Settings > About ChromeOS > Powerwash this device
      (or hold Ctrl+Alt+Shift+R at the sign-in screen)
  [ ] Follow the on-screen confirmation steps
  [ ] Sign back in with your Google Account when it restarts

After the Powerwash:
  [ ] Reconnect to Wi-Fi
  [ ] Sign back into your Google Account
  [ ] Re-share this drive with Linux (Files app > right-click > Share with Linux)
  [ ] Copy your files back and reinstall your favorite apps
  [ ] Breathe. You did it. Enjoy the clean, fast Chromebook!

-- CleanSlate v{version}
"""


def get_checklist_content():
    return CHECKLIST_CONTENT_CHROMEOS if PLATFORM == "chromeos" else CHECKLIST_CONTENT_WINDOWS


def get_checklist_sections():
    if PLATFORM == "chromeos":
        return [
            ("Before you Powerwash", [
                "This backup finished with no errors",
                "I know my Google Account password",
                "Wrote down my Wi-Fi password (if needed)",
                "Confirmed files are synced to Google Drive",
            ]),
            ("Doing the Powerwash", [
                "Opened Settings > About ChromeOS > Powerwash this device",
                "Followed the on-screen confirmation steps",
            ]),
            ("After the Powerwash", [
                "Reconnected to Wi-Fi and signed back in",
                "Re-shared this drive with Linux, if I use Linux apps",
                "Copied my files back and reinstalled my favorite apps",
            ]),
        ]
    return [
        ("Before you wipe your PC", [
            "This backup finished with no errors",
            "Wrote down my Wi-Fi password",
            "Noted any software license/product keys",
            "Signed out of apps with device limits",
            "Confirmed cloud-synced files are up to date",
        ]),
        ("Doing the clean install", [
            "Got the official Media Creation Tool from microsoft.com",
            "Created install media on a DIFFERENT usb drive",
            "Booted from that install USB and chose Custom install",
        ]),
        ("After Windows is reinstalled", [
            "Reconnected to Wi-Fi",
            "Installed graphics/chipset drivers",
            "Copied my files back from this drive",
            "Reinstalled my favorite apps",
        ]),
    ]


# ----------------------------------------------------------------------
# Rounded, canvas-drawn widgets (tkinter has no native rounded corners)
# ----------------------------------------------------------------------
def _round_rect_points(x1, y1, x2, y2, radius):
    r = radius
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


class PillButton(tk.Canvas):
    """A fully rounded (pill-shaped) button, drawn on a canvas."""

    PALETTES = {
        "primary": (COLOR_PRIMARY, COLOR_PRIMARY_HOVER, "white"),
        "ghost":   (COLOR_CARD, COLOR_GHOST_HOVER, COLOR_TEXT),
        "success": (COLOR_SUCCESS, COLOR_SUCCESS_HOVER, "#0B1A14"),
        "danger":  (COLOR_DANGER, COLOR_DANGER_HOVER, "#1F0E0E"),
    }

    def __init__(self, parent, text, command=None, kind="primary",
                 width=220, height=50, font=FONT_BUTTON, bg=COLOR_BG):
        super().__init__(parent, width=width, height=height, bg=bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.fill, self.hover, self.fg = self.PALETTES.get(kind, self.PALETTES["primary"])
        self.w, self.h = width, height
        radius = height / 2
        pts = _round_rect_points(1, 1, width - 1, height - 1, radius)
        self.rect = self.create_polygon(pts, smooth=True, fill=self.fill, outline="")
        self.label = self.create_text(width / 2, height / 2, text=text,
                                       fill=self.fg, font=font)
        self.enabled = True
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)

    def _enter(self, _e):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.hover)

    def _leave(self, _e):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.fill)

    def _click(self, _e):
        if self.enabled and self.command:
            self.command()

    def set_text(self, text):
        self.itemconfig(self.label, text=text)

    def disable(self):
        self.enabled = False
        self.itemconfig(self.rect, fill=COLOR_DISABLED)
        self.itemconfig(self.label, fill=COLOR_DISABLED_TEXT)
        self.config(cursor="arrow")

    def enable(self):
        self.enabled = True
        self.itemconfig(self.rect, fill=self.fill)
        self.itemconfig(self.label, fill=self.fg)
        self.config(cursor="hand2")


class SelectableCard(tk.Canvas):
    """A rounded card that highlights purple (with a blue rim) when selected."""

    def __init__(self, parent, title, subtitle, on_click, width=620, height=68, bg=COLOR_BG):
        super().__init__(parent, width=width, height=height, bg=bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.width, self.height = width, height
        radius = 20
        pts = _round_rect_points(1, 1, width - 1, height - 1, radius)
        self.rect = self.create_polygon(pts, smooth=True, fill=COLOR_CARD,
                                         outline=COLOR_CARD_BORDER, width=1.5)
        self.title_id = self.create_text(26, height / 2 - 10, text=title, anchor="w",
                                          fill=COLOR_TEXT, font=FONT_BODY_BOLD)
        self.sub_id = self.create_text(26, height / 2 + 13, text=subtitle, anchor="w",
                                        fill=COLOR_MUTED, font=FONT_SMALL)
        self.check_id = self.create_text(width - 30, height / 2, text="", fill="white",
                                          font=FONT_H2)
        self.selected = False
        self.bind("<Button-1>", lambda _e: on_click(self))

    def set_selected(self, value):
        self.selected = value
        if value:
            self.itemconfig(self.rect, fill=COLOR_PRIMARY, outline=COLOR_BLUE_HINT, width=2)
            self.itemconfig(self.title_id, fill="white")
            self.itemconfig(self.sub_id, fill="#E7E1FF")
            self.itemconfig(self.check_id, text="\u2713")
        else:
            self.itemconfig(self.rect, fill=COLOR_CARD, outline=COLOR_CARD_BORDER, width=1.5)
            self.itemconfig(self.title_id, fill=COLOR_TEXT)
            self.itemconfig(self.sub_id, fill=COLOR_MUTED)
            self.itemconfig(self.check_id, text="")


class ToggleChip(tk.Canvas):
    """A small rounded pill you tap on/off - used for the quick-add folders."""

    def __init__(self, parent, text, on_toggle, width=176, height=44, bg=COLOR_BG):
        super().__init__(parent, width=width, height=height, bg=bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.on_toggle = on_toggle
        self.active = False
        radius = height / 2
        pts = _round_rect_points(1, 1, width - 1, height - 1, radius)
        self.rect = self.create_polygon(pts, smooth=True, fill=COLOR_CARD,
                                         outline=COLOR_CARD_BORDER, width=1.5)
        self.label_id = self.create_text(width / 2, height / 2, text=text,
                                          fill=COLOR_TEXT, font=FONT_BODY_BOLD)
        self.bind("<Button-1>", lambda _e: self.on_toggle(self))

    def set_active(self, value):
        self.active = value
        if value:
            self.itemconfig(self.rect, fill=COLOR_PRIMARY, outline=COLOR_BLUE_HINT, width=2)
            self.itemconfig(self.label_id, fill="white")
        else:
            self.itemconfig(self.rect, fill=COLOR_CARD, outline=COLOR_CARD_BORDER, width=1.5)
            self.itemconfig(self.label_id, fill=COLOR_TEXT)


class RoundedProgressBar(tk.Canvas):
    def __init__(self, parent, width=620, height=28, bg=COLOR_BG):
        super().__init__(parent, width=width, height=height, bg=bg,
                          highlightthickness=0, bd=0)
        self.width, self.height = width, height
        self.radius = height / 2
        track_pts = _round_rect_points(0, 0, width, height, self.radius)
        self.create_polygon(track_pts, smooth=True, fill=COLOR_CARD_BORDER, outline="")
        self.fill_id = None
        self.set_progress(0)

    def set_progress(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        if self.fill_id:
            self.delete(self.fill_id)
            self.fill_id = None
        if fraction <= 0:
            return
        fill_width = max(self.height, fraction * self.width)
        pts = _round_rect_points(0, 0, fill_width, self.height, self.radius)
        self.fill_id = self.create_polygon(pts, smooth=True, fill=COLOR_PRIMARY, outline="")


class StepDots(tk.Frame):
    """A minimal 4-dot progress strip, no clutter, no labels."""

    def __init__(self, parent, current_index, total=4, bg=COLOR_BG):
        super().__init__(parent, bg=bg)
        for i in range(total):
            if i < current_index:
                color = COLOR_BLUE_HINT
            elif i == current_index:
                color = COLOR_PRIMARY
            else:
                color = COLOR_CARD_BORDER
            dot = tk.Canvas(self, width=30, height=10, bg=bg, highlightthickness=0, bd=0)
            dot.create_oval(1, 1, 9, 9, fill=color, outline="") if False else None
            pts = _round_rect_points(0, 2, 26, 8, 3)
            dot.create_polygon(pts, smooth=True, fill=color, outline="")
            dot.grid(row=0, column=i, padx=4)


# ----------------------------------------------------------------------
# Main application
# ----------------------------------------------------------------------
class CleanSlateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - Simple Backup & Fresh Start")
        self.geometry("760x620")
        self.minsize(700, 580)
        self.configure(bg=COLOR_BG)

        self.selected_drive = None
        self.selected_paths = []
        self.copy_plan = []
        self.total_size = 0
        self.cancel_event = threading.Event()
        self.progress_queue = queue.Queue()
        self.backup_dest_folder = None
        self.backup_started_at = None
        self.drive_cards = []
        self.folder_chips = {}

        self.container = tk.Frame(self, bg=COLOR_BG)
        self.container.pack(fill="both", expand=True)

        self.show_welcome()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ---------------- Welcome ----------------
    def show_welcome(self):
        self.clear()
        wrap = tk.Frame(self.container, bg=COLOR_BG)
        wrap.pack(fill="both", expand=True)

        center = tk.Frame(wrap, bg=COLOR_BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center, text="\U0001F4BE", font=("Segoe UI Emoji", 54), bg=COLOR_BG).pack(pady=(0, 8))
        tk.Label(center, text=APP_NAME, font=FONT_H1, bg=COLOR_BG, fg=COLOR_TEXT).pack()
        tk.Label(center, text="Back up your files. Reinstall Windows. Feel great.",
                 font=FONT_BODY, bg=COLOR_BG, fg=COLOR_MUTED).pack(pady=(6, 28))

        PillButton(center, "Get Started", command=self.go_step_drive,
                   width=240, height=54, bg=COLOR_BG).pack()

    # ---------------- Step 1: Drive ----------------
    def go_step_drive(self):
        self.clear()
        outer = tk.Frame(self.container, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=36, pady=28)

        StepDots(outer, 0).pack(anchor="w", pady=(0, 22))
        tk.Label(outer, text="Choose your drive", font=FONT_H2, bg=COLOR_BG, fg=COLOR_TEXT)\
            .pack(anchor="w")

        if PLATFORM == "chromeos":
            hint = ("Plug in a USB drive, then in the Files app right-click it and\n"
                    "choose \"Share with Linux\". Then tap Refresh below.")
        else:
            hint = "Plug in a USB drive and tap it below."

        tk.Label(outer, text=hint, font=FONT_BODY, justify="left",
                 bg=COLOR_BG, fg=COLOR_MUTED).pack(anchor="w", pady=(2, 18))

        self.drive_list_holder = tk.Frame(outer, bg=COLOR_BG)
        self.drive_list_holder.pack(fill="both", expand=True)
        self.render_drives()

        btn_row = tk.Frame(outer, bg=COLOR_BG)
        btn_row.pack(fill="x", pady=(18, 0))
        PillButton(btn_row, "Refresh", command=self.render_drives, kind="ghost",
                   width=130, height=46, bg=COLOR_BG).pack(side="left")
        PillButton(btn_row, "Choose a Folder", command=self.pick_drive_manually,
                   kind="ghost", width=180, height=46, bg=COLOR_BG).pack(side="left", padx=(10, 0))
        PillButton(btn_row, "Next", command=self.confirm_drive, width=140, height=46,
                   bg=COLOR_BG).pack(side="right")

    def render_drives(self):
        for w in self.drive_list_holder.winfo_children():
            w.destroy()
        self.drive_cards = []

        drives = get_removable_drives()

        if not drives:
            if PLATFORM == "chromeos":
                msg = ("No shared USB drive detected yet.\n"
                       "Share it with Linux from the Files app, then tap Refresh -\n"
                       "or use 'Choose a Folder' below.")
            else:
                msg = "No USB drive detected yet. Plug one in and tap Refresh."
            tk.Label(self.drive_list_holder, text=msg, font=FONT_BODY, justify="left",
                     bg=COLOR_BG, fg=COLOR_MUTED).pack(anchor="w", pady=20)
            return

        for d in drives:
            subtitle = f"{human_size(d['free'])} free of {human_size(d['total'])}  \u2022  {d['path']}"
            card = SelectableCard(self.drive_list_holder, d["label"], subtitle,
                                   on_click=lambda c, drive=d: self.select_drive(c, drive), bg=COLOR_BG)
            card.pack(anchor="w", pady=6)
            card._drive = d
            self.drive_cards.append(card)
            if self.selected_drive and self.selected_drive["path"] == d["path"]:
                card.set_selected(True)

    def select_drive(self, card, drive):
        for c in self.drive_cards:
            c.set_selected(c is card)
        self.selected_drive = drive

    def pick_drive_manually(self):
        path = filedialog.askdirectory(title="Select your USB drive's folder")
        if path:
            usage = shutil.disk_usage(path)
            self.selected_drive = {"path": path, "label": os.path.basename(path) or path,
                                    "free": usage.free, "total": usage.total}
            self.go_step_files()

    def confirm_drive(self):
        if not self.selected_drive:
            messagebox.showwarning(APP_NAME, "Please pick a flash drive first.")
            return
        self.go_step_files()

    # ---------------- Step 2: Files ----------------
    def go_step_files(self):
        self.clear()
        outer = tk.Frame(self.container, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=36, pady=28)

        StepDots(outer, 1).pack(anchor="w", pady=(0, 22))
        tk.Label(outer, text="What should we back up?", font=FONT_H2, bg=COLOR_BG, fg=COLOR_TEXT)\
            .pack(anchor="w")
        tk.Label(outer, text="Tap to add. Tap again to remove.", font=FONT_BODY,
                 bg=COLOR_BG, fg=COLOR_MUTED).pack(anchor="w", pady=(2, 18))

        chip_wrap = tk.Frame(outer, bg=COLOR_BG)
        chip_wrap.pack(fill="x")
        self.folder_chips = {}
        common = get_common_folders()
        for i, (name, path) in enumerate(common):
            chip = ToggleChip(chip_wrap, name, on_toggle=self.toggle_folder_chip, bg=COLOR_BG)
            chip.grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="w")
            chip._path = path
            chip.set_active(path in self.selected_paths)
            self.folder_chips[path] = chip

        custom_row = tk.Frame(outer, bg=COLOR_BG)
        custom_row.pack(fill="x", pady=(6, 16))
        PillButton(custom_row, "+ Add Files", kind="ghost", width=150, height=44,
                   command=self.add_files_dialog, bg=COLOR_BG).pack(side="left")
        PillButton(custom_row, "+ Add Folder", kind="ghost", width=150, height=44,
                   command=self.add_folder_dialog, bg=COLOR_BG).pack(side="left", padx=(10, 0))

        self.selected_count_label = tk.Label(outer, text="", font=FONT_SMALL,
                                              bg=COLOR_BG, fg=COLOR_MUTED)
        self.selected_count_label.pack(anchor="w")

        list_wrap = tk.Frame(outer, bg=COLOR_BG)
        list_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.selected_list_frame = tk.Frame(list_wrap, bg=COLOR_BG)
        self.selected_list_frame.pack(fill="both", expand=True)

        btn_row = tk.Frame(outer, bg=COLOR_BG)
        btn_row.pack(fill="x", pady=(16, 0))
        PillButton(btn_row, "Back", kind="ghost", command=self.go_step_drive,
                   width=120, height=46, bg=COLOR_BG).pack(side="left")
        PillButton(btn_row, "Next", command=self.confirm_files, width=140, height=46,
                   bg=COLOR_BG).pack(side="right")

        self.render_selected_list()

    def toggle_folder_chip(self, chip):
        path = chip._path
        if path in self.selected_paths:
            self.selected_paths.remove(path)
            chip.set_active(False)
        else:
            self.selected_paths.append(path)
            chip.set_active(True)
        self.render_selected_list()

    def add_files_dialog(self):
        paths = filedialog.askopenfilenames(title="Choose files to back up")
        for p in paths:
            if p not in self.selected_paths:
                self.selected_paths.append(p)
        self.render_selected_list()

    def add_folder_dialog(self):
        path = filedialog.askdirectory(title="Choose a folder to back up")
        if path and path not in self.selected_paths:
            self.selected_paths.append(path)
        self.render_selected_list()

    def remove_path(self, path):
        if path in self.selected_paths:
            self.selected_paths.remove(path)
        if path in self.folder_chips:
            self.folder_chips[path].set_active(False)
        self.render_selected_list()

    def render_selected_list(self):
        for w in self.selected_list_frame.winfo_children():
            w.destroy()

        if not self.selected_paths:
            self.selected_count_label.config(text="Nothing selected yet.")
            return

        self.selected_count_label.config(text=f"{len(self.selected_paths)} item(s) selected")

        for p in self.selected_paths:
            row = tk.Frame(self.selected_list_frame, bg=COLOR_BG)
            row.pack(fill="x", pady=3)
            kind = "\U0001F4C1" if os.path.isdir(p) else "\U0001F4C4"
            tk.Label(row, text=f"{kind}  {p}", font=FONT_SMALL, bg=COLOR_BG,
                     fg=COLOR_MUTED, anchor="w").pack(side="left", fill="x", expand=True)
            PillButton(row, "\u2715", kind="ghost", width=36, height=36, font=FONT_SMALL,
                       command=lambda path=p: self.remove_path(path), bg=COLOR_BG).pack(side="right")

    def confirm_files(self):
        if not self.selected_paths:
            messagebox.showwarning(APP_NAME, "Please add at least one file or folder.")
            return
        self.go_step_backup()

    # ---------------- Step 3: Backup ----------------
    def go_step_backup(self):
        self.clear()
        outer = tk.Frame(self.container, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=36, pady=28)

        StepDots(outer, 2).pack(anchor="w", pady=(0, 22))
        tk.Label(outer, text="Ready when you are", font=FONT_H2, bg=COLOR_BG, fg=COLOR_TEXT)\
            .pack(anchor="w")

        self.copy_plan, self.total_size = collect_files(self.selected_paths)
        file_count = len(self.copy_plan)
        tk.Label(outer, text=f"{file_count:,} files \u2022 {human_size(self.total_size)} "
                              f"\u2192 {self.selected_drive['path']}",
                 font=FONT_BODY, bg=COLOR_BG, fg=COLOR_MUTED).pack(anchor="w", pady=(2, 24))

        center = tk.Frame(outer, bg=COLOR_BG)
        center.pack(fill="x", pady=(10, 0))

        self.progress_status = tk.Label(center, text="Tap Start when you're ready.",
                                         font=FONT_BODY_BOLD, bg=COLOR_BG, fg=COLOR_TEXT)
        self.progress_status.pack(anchor="w", pady=(0, 12))

        self.progress_bar = RoundedProgressBar(center, width=620, height=28, bg=COLOR_BG)
        self.progress_bar.pack(anchor="w")

        self.progress_detail = tk.Label(center, text="", font=FONT_SMALL,
                                         bg=COLOR_BG, fg=COLOR_MUTED, anchor="w")
        self.progress_detail.pack(anchor="w", pady=(10, 0))

        self.backup_action_row = tk.Frame(outer, bg=COLOR_BG)
        self.backup_action_row.pack(anchor="w", pady=(28, 0))
        self.start_button = PillButton(self.backup_action_row, "Start Backup", kind="success",
                                        command=self.start_backup, width=200, height=54, bg=COLOR_BG)
        self.start_button.pack(side="left")
        self.cancel_button = PillButton(self.backup_action_row, "Cancel", kind="danger",
                                         command=self.cancel_backup, width=140, height=54, bg=COLOR_BG)

        btn_row = tk.Frame(outer, bg=COLOR_BG)
        btn_row.pack(fill="x", side="bottom", pady=(24, 0))
        self.back_button_step3 = PillButton(btn_row, "Back", kind="ghost", command=self.go_step_files,
                                             width=120, height=46, bg=COLOR_BG)
        self.back_button_step3.pack(side="left")
        self.next_button_step3 = PillButton(btn_row, "Next", command=self.go_step_checklist,
                                             width=140, height=46, bg=COLOR_BG)

    def start_backup(self):
        if not self.copy_plan:
            messagebox.showinfo(APP_NAME, "There's nothing to back up.")
            return

        free_space = self.selected_drive.get("free", 0)
        if free_space and self.total_size > free_space:
            proceed = messagebox.askyesno(
                APP_NAME,
                f"Your drive may not have enough space.\n\n"
                f"Files need: {human_size(self.total_size)}\n"
                f"Drive has: {human_size(free_space)} free\n\nTry anyway?"
            )
            if not proceed:
                return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.backup_dest_folder = os.path.join(self.selected_drive["path"], f"CleanSlate_Backup_{timestamp}")
        os.makedirs(self.backup_dest_folder, exist_ok=True)

        self.cancel_event.clear()
        self.progress_queue = queue.Queue()
        self.backup_started_at = time.time()

        self.start_button.pack_forget()
        self.cancel_button.pack(side="left")
        self.back_button_step3.disable()

        threading.Thread(target=self._copy_worker, daemon=True).start()
        self.after(100, self.poll_progress)

    def _copy_worker(self):
        done_bytes = 0
        done_count = 0
        total_count = len(self.copy_plan)
        try:
            for src, rel in self.copy_plan:
                if self.cancel_event.is_set():
                    self.progress_queue.put(("cancelled",))
                    return
                dest_path = os.path.join(self.backup_dest_folder, rel)
                try:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(src, dest_path)
                    size = os.path.getsize(src)
                except Exception as e:
                    self.progress_queue.put(("file_error", src, str(e)))
                    continue
                done_bytes += size
                done_count += 1
                self.progress_queue.put(("progress", done_bytes, done_count, total_count, rel))

            try:
                checklist_path = os.path.join(self.backup_dest_folder, "Fresh-Start-Checklist.txt")
                with open(checklist_path, "w", encoding="utf-8") as f:
                    f.write(get_checklist_content().format(
                        date=datetime.date.today().isoformat(), version=APP_VERSION))
            except Exception:
                pass

            self.progress_queue.put(("done", done_count, total_count))
        except Exception as e:
            self.progress_queue.put(("error", str(e)))

    def poll_progress(self):
        try:
            while True:
                item = self.progress_queue.get_nowait()
                kind = item[0]

                if kind == "progress":
                    _, done_bytes, done_count, total_count, rel = item
                    frac = (done_bytes / self.total_size) if self.total_size else 1.0
                    self.progress_bar.set_progress(frac)
                    self.progress_status.config(
                        text=f"Backing up\u2026 {frac*100:.0f}% ({done_count:,}/{total_count:,} files)")
                    short_name = rel if len(rel) < 60 else "..." + rel[-57:]
                    self.progress_detail.config(text=f"Copying: {short_name}")

                elif kind == "file_error":
                    _, src, _err = item
                    self.progress_detail.config(text=f"Skipped: {os.path.basename(src)}")

                elif kind == "done":
                    _, done_count, total_count = item
                    elapsed = time.time() - (self.backup_started_at or time.time())
                    self.progress_bar.set_progress(1.0)
                    self.progress_status.config(
                        text=f"\u2705 Done! Backed up {done_count:,} files in {elapsed:.0f}s.")
                    self.progress_detail.config(text=f"Saved to: {self.backup_dest_folder}")
                    self.cancel_button.pack_forget()
                    self.back_button_step3.enable()
                    self.next_button_step3.pack(side="right")
                    return

                elif kind == "cancelled":
                    self.progress_status.config(text="Backup cancelled.")
                    self.progress_detail.config(text="Tap Start Backup to try again.")
                    self.cancel_button.pack_forget()
                    self.start_button.pack(side="left")
                    self.back_button_step3.enable()
                    return

                elif kind == "error":
                    _, msg = item
                    messagebox.showerror(APP_NAME, f"Something went wrong:\n{msg}")
                    self.cancel_button.pack_forget()
                    self.start_button.pack(side="left")
                    self.back_button_step3.enable()
                    return
        except queue.Empty:
            pass
        self.after(100, self.poll_progress)

    def cancel_backup(self):
        self.cancel_event.set()

    # ---------------- Step 4: Checklist ----------------
    def go_step_checklist(self):
        self.clear()
        outer = tk.Frame(self.container, bg=COLOR_BG)
        outer.pack(fill="both", expand=True, padx=36, pady=28)

        StepDots(outer, 3).pack(anchor="w", pady=(0, 22))
        tk.Label(outer, text="Your Fresh Start plan", font=FONT_H2, bg=COLOR_BG, fg=COLOR_TEXT)\
            .pack(anchor="w")

        if PLATFORM == "chromeos":
            subtitle = "Work through this before and after you Powerwash."
            install_label, install_url = "Learn about Powerwash", "https://support.google.com/chromebook/answer/183084"
        else:
            subtitle = "Work through this before and after your clean install."
            install_label, install_url = "Get Install Media", "https://www.microsoft.com/software-download/windows11"

        tk.Label(outer, text=subtitle, font=FONT_BODY, bg=COLOR_BG, fg=COLOR_MUTED)\
            .pack(anchor="w", pady=(2, 16))

        canvas = tk.Canvas(outer, bg=COLOR_BG, highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        scroll_frame = tk.Frame(canvas, bg=COLOR_BG)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        for section_title, items in get_checklist_sections():
            tk.Label(scroll_frame, text=section_title, font=FONT_BODY_BOLD,
                     bg=COLOR_BG, fg=COLOR_BLUE_HINT).pack(anchor="w", pady=(10, 6))
            for item_text in items:
                self._make_checklist_row(scroll_frame, item_text)

        btn_row = tk.Frame(outer, bg=COLOR_BG)
        btn_row.pack(fill="x", side="bottom", pady=(18, 0))
        PillButton(btn_row, install_label, kind="ghost", width=190, height=46,
                   command=lambda: webbrowser.open(install_url), bg=COLOR_BG).pack(side="left")
        PillButton(btn_row, "Open Backup Folder", kind="ghost", width=190, height=46,
                   command=self.open_backup_folder, bg=COLOR_BG).pack(side="left", padx=(10, 0))
        PillButton(btn_row, "Finish", kind="success", command=self.destroy,
                   width=140, height=46, bg=COLOR_BG).pack(side="right")

    def _make_checklist_row(self, parent, text):
        row = tk.Frame(parent, bg=COLOR_BG)
        row.pack(fill="x", pady=3)
        box = tk.Canvas(row, width=26, height=26, bg=COLOR_BG, highlightthickness=0, bd=0, cursor="hand2")
        pts = _round_rect_points(1, 1, 25, 25, 7)
        rect = box.create_polygon(pts, smooth=True, fill=COLOR_CARD, outline=COLOR_CARD_BORDER, width=1.5)
        mark = box.create_text(13, 13, text="", fill="white", font=FONT_SMALL)
        state = {"checked": False}

        def toggle(_e=None):
            state["checked"] = not state["checked"]
            if state["checked"]:
                box.itemconfig(rect, fill=COLOR_PRIMARY, outline=COLOR_BLUE_HINT)
                box.itemconfig(mark, text="\u2713")
            else:
                box.itemconfig(rect, fill=COLOR_CARD, outline=COLOR_CARD_BORDER)
                box.itemconfig(mark, text="")

        box.bind("<Button-1>", toggle)
        box.pack(side="left", padx=(0, 10))
        label = tk.Label(row, text=text, font=FONT_BODY, bg=COLOR_BG, fg=COLOR_TEXT,
                          anchor="w", cursor="hand2")
        label.pack(side="left", fill="x", expand=True)
        label.bind("<Button-1>", toggle)

    def open_backup_folder(self):
        if not (self.backup_dest_folder and os.path.isdir(self.backup_dest_folder)):
            messagebox.showinfo(APP_NAME, "No backup folder yet.")
            return
        try:
            if PLATFORM == "windows":
                os.startfile(self.backup_dest_folder)
            elif PLATFORM == "mac":
                subprocess.run(["open", self.backup_dest_folder], check=False)
            else:
                # Linux and ChromeOS's Crostini both understand xdg-open;
                # on ChromeOS it hands the folder off to the Files app.
                subprocess.run(["xdg-open", self.backup_dest_folder], check=False)
        except Exception:
            try:
                webbrowser.open(f"file://{self.backup_dest_folder}")
            except Exception as e:
                messagebox.showerror(APP_NAME, f"Couldn't open that folder:\n{e}")


def main():
    app = CleanSlateApp()
    app.mainloop()


if __name__ == "__main__":
    main()
