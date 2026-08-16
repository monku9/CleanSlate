<img width="2720" height="880" alt="cleanslate_usb_logo" src="https://github.com/user-attachments/assets/df8becce-6aeb-4e8c-b9a7-653dd78428d1" />

**The friendliest way to back up your files before a clean Windows install.**

Plug in a flash drive. Pick your files. Tap a button. Done.
No accounts, no cloud, no confusing options — just a simple 4-step wizard
that anyone who just got their first PC can follow without help.

[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows)](https://www.microsoft.com/software-download/windows11)
[![Platform](https://img.shields.io/badge/platform-ChromeOS-4285F4?style=flat-square&logo=googlechrome)](https://support.google.com/chromebook/answer/183084)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square&logo=python)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-8B5CF6?style=flat-square)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen?style=flat-square)](requirements.txt)
[![Latest Release](https://img.shields.io/github/v/release/monku9/CleanSlate?style=flat-square&color=8B5CF6&label=release)](https://github.com/monku9/CleanSlate/releases/latest)

---

## ✨ Why CleanSlate?

Doing a clean install of Windows is one of the best things you can do for a
slow or cluttered PC — but it's intimidating. Most people either:

- Skip it forever because backing up files feels scary, or
- Forget something important and lose it

CleanSlate fixes that. It's built for **one job only**: get your files onto
a USB drive quickly and safely, and hand you a plain-English checklist for
everything else.

## 🧭 How it works

CleanSlate walks you through four simple steps:

| Step | What happens |
|------|--------------|
| **1. Choose your drive** | CleanSlate automatically finds USB flash drives plugged into your device and shows how much free space each one has. Tap the one you want. |
| **2. Pick your files** | One-tap chips for Desktop, Documents, Pictures, Music, Videos, and Downloads — or add any specific files/folders yourself. |
| **3. Back it up** | A big, clear rounded progress bar shows exactly what's copying. Cancel anytime. Nothing is deleted from your device — this only *copies* files. |
| **4. Fresh Start** | On Windows, choose **Reinstall Windows** or **Switch to Linux**. Either way you get a tappable checklist for before, during, and after, plus a one-tap link to the right official resource. A copy of the matching checklist is also saved right onto your flash drive. |

CleanSlate knows what kind of "fresh start" you're actually doing:

- **On Windows**, Step 4 asks you to pick one of two paths:
  - **Reinstall Windows** — the classic clean-install checklist, with a link to Microsoft's official Media Creation Tool.
  - **Switch to Linux** — for anyone ready to leave Windows behind entirely. This checklist covers checking hardware/driver support, handling BitLocker, exporting browser data, picking a beginner-friendly distro (Mint, Ubuntu, Zorin OS), making a bootable USB, and choosing a full switch vs. dual-boot.
- **On ChromeOS**, Step 4 shows a Powerwash checklist instead (Chromebooks don't reinstall an OS — they factory-reset), and links to Google's official Powerwash support page.

Whichever path you pick, a matching copy of the checklist is saved right onto your flash drive, so it's there for you after the wipe.

## 💻 Platform support

| Platform | Drive detection | Notes |
|----------|-----------------|-------|
| **Windows** | Automatic | Uses the Windows API directly to find removable drives. |
| **ChromeOS** | Automatic (after one extra step) | Runs inside the Linux (Crostini) container. Plug in your USB drive, then in the **Files app**, right-click it and choose **"Share with Linux"** — it'll then show up automatically in CleanSlate. |
| **macOS** | Automatic | Scans `/Volumes` for mounted drives. |
| **Other Linux** | Automatic | Scans common mount points (`/media/$USER`, `/run/media/$USER`). |

On any platform, "Choose a Folder" is always available as a manual fallback if auto-detection doesn't find your drive.

### A note for ChromeOS / Linux users on tkinter

CleanSlate's UI is built with `tkinter`, which ships with Python by default
on Windows and macOS, but Debian-based systems (including ChromeOS's Linux
container) sometimes leave it out. If `python app.py` complains about a
missing `_tkinter` module, install it with:

```bash
sudo apt update && sudo apt install python3-tk
```

## 🎨 Design

CleanSlate uses a dark theme — deep purple with a hint of blue — and every
button and card is fully rounded. No sharp corners, no clutter, one clear
action per screen. It's meant to feel calm, not like software.

## 🚀 Getting Started

### Option A — Just run the Python script (easiest for developers)

1. Install [Python 3.8 or newer](https://www.python.org/downloads/) (tkinter comes bundled automatically on Windows).
2. Download or clone this repo:
   ```bash
   git clone https://github.com/monku9/CleanSlate.git
   cd CleanSlate
   ```
3. Run it:
   ```bash
   python app.py
   ```

No `pip install` needed — CleanSlate only uses Python's standard library.

### Option B — Build a standalone .exe (easiest for everyone else)

If you want a double-click app with no Python required:

1. Make sure Python is installed (see above).
2. Go download the [Latest Release](https://github.com/monku9/CleanSlate/releases/latest) and extract the Source Code ZIP file.
3. Double-click `build.bat` (or run it from a terminal).
4. Grab `CleanSlate.exe` from the new `dist` folder.
5. Share that `.exe` with anyone — it runs on its own.

> **Having trouble with `build.bat`?** Some Python installs (especially the
> newer per-user "Python Install Manager" installs) don't add PyInstaller's
> command to your PATH. `build.bat` is already written to work around this
> by calling `python -m PyInstaller` instead of `pyinstaller` directly — if
> you edited the script and it's failing, make sure it still uses the
> `python -m` form.

## 🔒 Safety & Privacy, by design

- **100% offline.** CleanSlate never connects to the internet, except when
  *you* tap the button to open Microsoft's official download page.
- **Copy-only.** It only ever copies files to your flash drive. It never
  deletes or modifies anything on your PC.
- **No telemetry, no accounts, no ads.**
- **Open source.** Every line of code that touches your files is right here
  in `app.py` — read it, audit it, fork it.

## 🛠️ Built with

CleanSlate is a single Python file using only the standard library:

- `tkinter` — the entire UI, including hand-drawn rounded buttons and cards
- `shutil` / `os` — file copying and folder walking
- `ctypes` — detecting removable USB drives on Windows
- Filesystem fingerprinting (`/mnt/chromeos`, `/dev/.cros_milestone`, hostname) — detecting ChromeOS's Linux container so the UI and checklist can adapt
- `threading` / `queue` — keeping the UI smooth while big backups run
- `subprocess` — opening the backup folder with the right tool per OS (`xdg-open` on Linux/ChromeOS, `open` on macOS, `os.startfile` on Windows)

No pip packages required to run it. No build system. Nothing to break in
six months.

## 🤝 Contributing

Found a bug? Have an idea that would make this friendlier for beginners?
Pull requests and issues are very welcome. A few ideas if you want to help:

- [ ] Add a light theme toggle
- [ ] Add file de-duplication (skip files already backed up)
- [ ] Add drag-and-drop file selection
- [ ] Localize the UI into other languages
- [ ] Add automated tests for `collect_files()` and drive detection

## 📄 License

MIT — do whatever you'd like with it. See [LICENSE](LICENSE).

---

<p align="center">Made with 💜 to help more people feel confident taking care of their own PC.</p>
