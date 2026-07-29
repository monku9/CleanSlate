# 💜 CleanSlate

**The friendliest way to back up your files before a clean Windows install.**

Plug in a flash drive. Pick your files. Tap a button. Done.
No accounts, no cloud, no confusing options — just a simple 4-step wizard
that anyone who just got their first PC can follow without help

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
| **1. Choose your drive** | CleanSlate automatically finds USB flash drives plugged into your PC and shows how much free space each one has. Tap the one you want. |
| **2. Pick your files** | One-tap chips for Desktop, Documents, Pictures, Music, Videos, and Downloads — or add any specific files/folders yourself. |
| **3. Back it up** | A big, clear rounded progress bar shows exactly what's copying. Cancel anytime. Nothing is deleted from your PC — this only *copies* files. |
| **4. Fresh Start** | A tappable checklist for before, during, and after your clean install, plus a one-tap link to Microsoft's official Windows download page. A copy of this checklist is also saved right onto your flash drive. |

## 🎨 Design

CleanSlate uses a dark theme — deep purple with a hint of blue — and every
button and card is fully rounded. No sharp corners, no clutter, one clear
action per screen. It's meant to feel calm, not like software.

## 🚀 Getting Started



## Option A — Just run the Python script (easiest for developers)

1. Install [Python 3.8 or newer](https://www.python.org/downloads/) (tkinter comes bundled automatically on Windows).
2. Download or clone this repo:
   ```bash
   git clone https://github.com/YOUR-USERNAME/cleanslate.git
   cd cleanslate
   ```
3. Run it:
   ```bash
   python app.py
   ```

No `pip install` needed — CleanSlate only uses Python's standard library.



## Option B — Build a standalone .exe (easiest for everyone else)

If you want a double-click app with no Python required:
1. Go to the [Latest Release](https://github.com/monku9/CleanSlate/releases)
2. Make sure Python is installed (see above).
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
- `threading` / `queue` — keeping the UI smooth while big backups run

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
