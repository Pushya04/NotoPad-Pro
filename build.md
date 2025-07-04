# 🛠️ Build Instructions for NotoPad Pro

This guide helps you build `app.exe` from the source `app.py` using PyInstaller on Windows.

---

## ✅ Prerequisites

- Python 3.8+
- `pip` installed
- Required Python packages:

```bash
pip install pyinstaller reportlab pyenchant
```

---

## 🧼 Step 1: Clean Old Builds (Optional)

Open PowerShell or CMD in your project folder and run:

```powershell
Remove-Item -Recurse -Force .\build, .\dist
Remove-Item -Force .\app.spec
```

---

## ⚙️ Step 2: Build the `.exe` File

Run the command:

```powershell
pyinstaller --onefile --windowed --icon=icon.ico app.py
```

> This will create an `.exe` file at `dist/app.exe`

---

## 📦 Step 3: Package Executable

Move these into the same folder as `app.exe` if needed:

- `editor_config.ini`
- `recent_files.json`

Zip the contents of the `dist/` folder and upload it to GitHub Releases.

---

## ❌ Drag & Drop Info

We removed `tkinterdnd2` support for `.exe` because of native DLL issues. It's only supported when running the Python file directly.

---

## 📁 Folder Output

```
dist/
├── app.exe
├── editor_config.ini
└── recent_files.json
```

---

## 🧪 Test Executable

Double-click `app.exe` and test:
- Open & Save
- Theme switching
- PDF Export
- Font changes
- Auto-save & recent files

✅ You're ready to ship!
